from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import CurrentUser
from app.core.config import get_settings
from app.schemas.media_studio import VeoOptionsResponse, VeoTaskResponse
from app.services.grsai_veo import (
    GrsaiVeoError,
    create_public_input_url,
    create_task_record,
    create_veo_options,
    get_task_record,
    iter_minio_object,
    list_task_records,
    mark_task_failed,
    open_public_input,
    public_task_record,
    refresh_task,
    save_input_image,
    submit_task,
)


# 路径中的 veo 为兼容已有前端地址和部署规则而保留，实际供应商已经迁移为百炼 Wan 2.7。
router = APIRouter(prefix="/api/media-studio/veo", tags=["媒体工作台 - Wan 图生视频"])
public_router = APIRouter(prefix="/api/public/media-studio/veo-inputs", tags=["媒体工作台 - 视频临时素材"])


@router.get(
    "/options",
    response_model=VeoOptionsResponse,
    summary="查询 Wan 图生视频能力与配置状态",
    description=(
        "返回当前开放的 Wan 模型、分辨率、时长、图片限制以及服务端是否已配置百炼。"
        "接口只返回布尔配置状态，不会泄露 API Key 或对象存储凭据。"
    ),
)
def get_veo_options() -> VeoOptionsResponse:
    return VeoOptionsResponse.model_validate(create_veo_options())


@router.post(
    "/tasks",
    response_model=VeoTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建 Wan 图生视频任务",
    description=(
        "上传首帧图片或填写公网图片 URL，创建阿里云百炼 Wan 2.7 异步任务。"
        "可额外提供尾帧；接口只保存任务 ID，视频生成不会阻塞本请求。"
    ),
)
def create_veo_task(
    current_user: CurrentUser,
    prompt: Annotated[str, Form(min_length=1, max_length=2000, description="视频动作、镜头与氛围提示词")],
    model: Annotated[str, Form(description="百炼模型：wan2.7-i2v-2026-04-25")] = "wan2.7-i2v-2026-04-25",
    aspect_ratio: Annotated[
        str,
        Form(description="兼容旧前端的画幅字段；Wan 2.7 实际输出比例始终跟随首帧"),
    ] = "auto",
    resolution: Annotated[str, Form(description="输出分辨率：720P 或 1080P")] = "720P",
    duration_seconds: Annotated[
        int,
        Form(ge=2, le=15, description="输出时长，单位秒，范围 2 到 15"),
    ] = 5,
    first_frame: Annotated[
        UploadFile | None,
        File(description="首帧图片；与 first_frame_url 二选一，支持 JPG、PNG、WEBP，大小上限由服务端配置"),
    ] = None,
    first_frame_url: Annotated[
        str,
        Form(max_length=2048, description="公开可访问的首帧 HTTP(S) 地址；与 first_frame 二选一"),
    ] = "",
    last_frame: Annotated[
        UploadFile | None,
        File(description="可选尾帧图片；与 last_frame_url 二选一"),
    ] = None,
    last_frame_url: Annotated[str, Form(max_length=2048, description="可选公开尾帧 HTTP(S) 地址")] = "",
) -> VeoTaskResponse:
    settings = get_settings()
    if not settings.video_mock_mode and not settings.dashscope_api_key:
        raise HTTPException(status_code=503, detail="服务端尚未配置 DASHSCOPE_API_KEY，暂不能创建视频任务。")

    first_frame_url = first_frame_url.strip()
    last_frame_url = last_frame_url.strip()
    if bool(first_frame) == bool(first_frame_url):
        raise HTTPException(status_code=400, detail="请上传一张首帧图片，或填写一个首帧公网 URL，二者只能选一个。")
    if last_frame and last_frame_url:
        raise HTTPException(status_code=400, detail="尾帧图片与尾帧 URL 只能选一个。")
    if aspect_ratio not in {"auto", "16:9", "9:16"}:
        raise HTTPException(status_code=400, detail="视频画幅参数无效。")
    if (first_frame or last_frame) and not settings.video_mock_mode and not settings.video_public_base_url:
        raise HTTPException(
            status_code=503,
            detail="本地图片回源地址未配置，请设置 VIDEO_PUBLIC_BASE_URL，或改用公网图片 URL。",
        )

    source_mode = "upload" if first_frame else "url"
    # 浏览器通常只会提交基础文件名，但仍在服务端移除客户端目录并限制长度，避免污染任务元数据。
    source_file_name = (
        (first_frame.filename or "").replace("\\", "/").rsplit("/", 1)[-1][:255]
        if first_frame
        else first_frame_url
    )
    record: dict | None = None
    stored_object_keys: list[str] = []
    try:
        record = create_task_record(
            owner_id=current_user.id,
            prompt=prompt,
            model=model,
            # Wan 2.7 不接受独立画幅参数；保留 auto 可避免页面误导用户。
            aspect_ratio="auto",
            resolution=resolution,
            duration_seconds=duration_seconds,
            source_mode=source_mode,
            source_file_name=source_file_name or "",
            has_last_frame=bool(last_frame or last_frame_url),
            settings=settings,
        )

        if first_frame:
            stored_first_frame = save_input_image(first_frame, settings)
            stored_object_keys.append(stored_first_frame.object_key)
            resolved_first_url = (
                "https://example.invalid/mock-first-frame.png"
                if settings.video_mock_mode
                else create_public_input_url(stored_first_frame, settings)
            )
        else:
            resolved_first_url = first_frame_url

        if last_frame:
            stored_last_frame = save_input_image(last_frame, settings)
            stored_object_keys.append(stored_last_frame.object_key)
            resolved_last_url = (
                "https://example.invalid/mock-last-frame.png"
                if settings.video_mock_mode
                else create_public_input_url(stored_last_frame, settings)
            )
        else:
            resolved_last_url = last_frame_url

        record = submit_task(
            record,
            resolved_first_url,
            resolved_last_url,
            input_object_keys=stored_object_keys,
            settings=settings,
        )
    except GrsaiVeoError as exc:
        if record is not None:
            mark_task_failed(record, exc, settings)
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return VeoTaskResponse.model_validate(public_task_record(record))


@router.get(
    "/tasks",
    response_model=list[VeoTaskResponse],
    summary="查询当前账号最近的视频任务",
    description="返回当前登录账号最近 12 条任务；供应商任务 ID、MinIO 对象键与密钥不会返回。",
)
def get_recent_veo_tasks(current_user: CurrentUser) -> list[VeoTaskResponse]:
    try:
        rows = list_task_records(current_user.id)
    except GrsaiVeoError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return [VeoTaskResponse.model_validate(public_task_record(row)) for row in rows]


@router.get(
    "/tasks/{task_id}",
    response_model=VeoTaskResponse,
    summary="刷新 Wan 图生视频任务状态",
    description="校验任务归属后向阿里云百炼查询一次结果，并返回平台统一状态。建议前端每 10-15 秒调用一次。",
)
def get_veo_task(task_id: str, current_user: CurrentUser) -> VeoTaskResponse:
    try:
        record = get_task_record(task_id, current_user.id)
        record = refresh_task(record)
    except GrsaiVeoError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return VeoTaskResponse.model_validate(public_task_record(record))


@public_router.get(
    "/{token}",
    include_in_schema=False,
    summary="供应商限时读取视频首尾帧",
)
def read_veo_input_image(token: str) -> StreamingResponse:
    """仅供视频供应商回源：令牌签名、对象目录和过期时间全部通过后才返回图片。"""

    try:
        response, content_type = open_public_input(token)
    except GrsaiVeoError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return StreamingResponse(
        iter_minio_object(response),
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=300", "X-Content-Type-Options": "nosniff"},
    )
