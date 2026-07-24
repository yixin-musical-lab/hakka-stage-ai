from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import RedirectResponse, StreamingResponse

from app.api.dependencies import CurrentUser
from app.core.config import get_settings
from app.schemas.media_studio import MotionTransferOptionsResponse, MotionTransferTaskResponse
from app.services.wan_animate import (
    MotionTransferError,
    create_motion_public_input_url,
    create_motion_task_record,
    create_motion_transfer_options,
    get_motion_task_record,
    iter_motion_object,
    list_motion_task_records,
    mark_motion_task_failed,
    open_motion_public_input,
    open_motion_result,
    parse_motion_video_range,
    public_motion_task_record,
    refresh_motion_task,
    remove_motion_inputs,
    save_motion_input,
    submit_motion_task,
)


router = APIRouter(
    prefix="/api/media-studio/motion-transfer",
    tags=["媒体工作台 - Wan 动作模仿"],
)
public_router = APIRouter(
    prefix="/api/public/media-studio/motion-inputs",
    tags=["媒体工作台 - 动作模仿临时素材"],
)


@router.get(
    "/options",
    response_model=MotionTransferOptionsResponse,
    summary="查询 Wan 动作模仿能力与配置状态",
    description=(
        "返回 wan2.2-animate-move 的素材限制、标准/专业模式和服务端配置状态。"
        "响应不会包含百炼 API Key、MinIO 凭据或供应商内部任务 ID。"
    ),
)
def get_motion_transfer_options() -> MotionTransferOptionsResponse:
    return MotionTransferOptionsResponse.model_validate(create_motion_transfer_options())


@router.post(
    "/tasks",
    response_model=MotionTransferTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建图片人物动作模仿任务",
    description=(
        "上传一张已获授权的单人人物图片和一段参考动作视频，创建百炼 "
        "wan2.2-animate-move 异步任务。输出保留人物图片背景，并迁移参考视频中的动作与表情。"
    ),
)
def create_motion_transfer_task(
    current_user: CurrentUser,
    person_image: Annotated[
        UploadFile,
        File(description="单人人物图片，支持 JPG/JPEG/PNG/BMP/WEBP，最大 5MB"),
    ],
    motion_video: Annotated[
        UploadFile,
        File(description="参考动作视频，支持 MP4/AVI/MOV，时长 2～30 秒，最大 200MB"),
    ],
    mode: Annotated[
        str,
        Form(description="质量模式：wan-std 标准模式或 wan-pro 专业模式"),
    ] = "wan-std",
    watermark: Annotated[
        bool,
        Form(description="是否在右下角添加千问 AI 生成标识"),
    ] = True,
    motion_duration_seconds: Annotated[
        float,
        Form(ge=2, le=30, description="浏览器读取到的参考视频时长，用于提交前校验和任务展示"),
    ] = 2,
    rights_confirmed: Annotated[
        bool,
        Form(description="确认人物肖像与参考动作视频已经取得使用授权"),
    ] = False,
) -> MotionTransferTaskResponse:
    settings = get_settings()
    if not rights_confirmed:
        raise HTTPException(status_code=400, detail="请先确认人物肖像和参考视频已经取得使用授权。")

    options = create_motion_transfer_options(settings)
    if not options["configured"]:
        if not settings.dashscope_api_key and not settings.video_mock_mode:
            detail = "服务端尚未配置 DASHSCOPE_API_KEY，暂不能创建动作模仿任务。"
        else:
            detail = "本地素材回源地址未配置，请设置外网可访问的 VIDEO_PUBLIC_BASE_URL。"
        raise HTTPException(status_code=503, detail=detail)

    record: dict | None = None
    stored_object_keys: list[str] = []
    try:
        record = create_motion_task_record(
            owner_id=current_user.id,
            mode=mode,
            watermark=watermark,
            person_file_name=person_image.filename or "",
            motion_file_name=motion_video.filename or "",
            motion_duration_seconds=motion_duration_seconds,
            settings=settings,
        )
        stored_image = save_motion_input(person_image, "image", settings)
        stored_object_keys.append(stored_image.object_key)
        stored_video = save_motion_input(motion_video, "video", settings)
        stored_object_keys.append(stored_video.object_key)

        if settings.video_mock_mode:
            image_url = "https://example.invalid/mock-person.png"
            video_url = "https://example.invalid/mock-motion.mp4"
        else:
            image_url = create_motion_public_input_url(stored_image, settings)
            video_url = create_motion_public_input_url(stored_video, settings)

        record = submit_motion_task(
            record,
            image_url,
            video_url,
            stored_object_keys,
            settings,
        )
    except MotionTransferError as exc:
        remove_motion_inputs(stored_object_keys, settings)
        if record is not None:
            mark_motion_task_failed(record, exc, settings)
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return MotionTransferTaskResponse.model_validate(public_motion_task_record(record))


@router.get(
    "/tasks",
    response_model=list[MotionTransferTaskResponse],
    summary="查询当前账号最近的动作模仿任务",
    description="最多返回当前账号最近 12 条记录，任务归属、对象键和供应商任务 ID 不会返回浏览器。",
)
def get_recent_motion_transfer_tasks(
    current_user: CurrentUser,
) -> list[MotionTransferTaskResponse]:
    try:
        rows = list_motion_task_records(current_user.id)
    except MotionTransferError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return [MotionTransferTaskResponse.model_validate(public_motion_task_record(row)) for row in rows]


@router.get(
    "/tasks/{task_id}",
    response_model=MotionTransferTaskResponse,
    summary="刷新单个动作模仿任务",
    description=(
        "校验任务归属后查询一次百炼状态；生成成功时尝试把供应商临时结果转存到 MinIO。"
        "建议前端每 12～15 秒调用一次。"
    ),
)
def get_motion_transfer_task(
    task_id: str,
    current_user: CurrentUser,
) -> MotionTransferTaskResponse:
    try:
        record = get_motion_task_record(task_id, current_user.id)
        record = refresh_motion_task(record)
    except MotionTransferError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return MotionTransferTaskResponse.model_validate(public_motion_task_record(record))


@router.get(
    "/tasks/{task_id}/result",
    summary="播放或下载当前账号的动作模仿结果",
    description="优先代理 MinIO 中已转存的视频，并支持浏览器单段 Range 播放；转存失败时跳转百炼临时地址。",
)
def read_motion_transfer_result(
    task_id: str,
    request: Request,
    current_user: CurrentUser,
    download: Annotated[bool, Query(description="true 时使用附件下载响应头")] = False,
):
    settings = get_settings()
    try:
        record = get_motion_task_record(task_id, current_user.id, settings)
    except MotionTransferError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if record.get("status") != "succeeded" or not record.get("result_available"):
        raise HTTPException(status_code=409, detail="动作模仿结果尚未生成完成。")

    if not record.get("result_persisted"):
        temporary_url = str(record.get("video_url") or "")
        if temporary_url:
            return RedirectResponse(temporary_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        raise HTTPException(status_code=404, detail="动作模仿结果地址不可用。")

    total_size = int(record.get("result_size_bytes") or 0)
    try:
        byte_range = parse_motion_video_range(request.headers.get("range"), total_size)
        response = open_motion_result(
            record,
            offset=byte_range.start if byte_range else 0,
            length=byte_range.length if byte_range else None,
            settings=settings,
        )
    except MotionTransferError as exc:
        headers = {"Content-Range": f"bytes */{total_size}"} if exc.status_code == 416 else None
        raise HTTPException(status_code=exc.status_code, detail=str(exc), headers=headers) from exc

    content_length = byte_range.length if byte_range else total_size
    file_name = f"motion-transfer-{task_id}.mp4"
    disposition = "attachment" if download else "inline"
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(file_name, safe='')}",
    }
    if byte_range:
        headers["Content-Range"] = f"bytes {byte_range.start}-{byte_range.end}/{total_size}"
    return StreamingResponse(
        iter_motion_object(response),
        status_code=status.HTTP_206_PARTIAL_CONTENT if byte_range else status.HTTP_200_OK,
        media_type=str(record.get("result_content_type") or "video/mp4"),
        headers=headers,
    )


@public_router.get(
    "/{token}",
    include_in_schema=False,
    summary="供百炼限时读取动作模仿输入素材",
)
def read_motion_transfer_input(token: str) -> StreamingResponse:
    """仅供百炼回源；令牌签名、目录和过期时间全部通过后才流式返回素材。"""

    try:
        response, content_type, size_bytes = open_motion_public_input(token)
    except MotionTransferError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return StreamingResponse(
        iter_motion_object(response),
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=300",
            "Content-Length": str(size_bytes),
            "X-Content-Type-Options": "nosniff",
        },
    )
