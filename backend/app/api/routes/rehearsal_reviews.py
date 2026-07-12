from datetime import datetime
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.llm_options import REASONING_LEVELS, is_supported_model
from app.models import (
    AiTask,
    MusicalFusionPlan,
    MusicalProject,
    MusicalScript,
    RehearsalReview,
    RoleTrainingPlan,
)
from app.schemas import (
    RehearsalReviewGenerateRequest,
    RehearsalReviewGenerateResponse,
    RehearsalReviewResponse,
    RehearsalReviewSummaryResponse,
    RehearsalReviewUpdateRequest,
    RehearsalVideoUploadResponse,
)
from app.services.rehearsal_review_queue import QueueUnavailableError, enqueue_rehearsal_review_task
from app.services.rehearsal_review_service import (
    delete_rehearsal_review_with_related_data,
    rehearsal_review_summary,
    render_rehearsal_review_markdown,
)
from app.services.rehearsal_storage import (
    RehearsalStorageError,
    iter_minio_response,
    open_rehearsal_video,
    parse_video_range,
    save_rehearsal_video_upload,
    stat_rehearsal_video,
)


router = APIRouter(prefix="/api", tags=["rehearsal-reviews"])


@router.post(
    "/rehearsal-reviews/upload",
    response_model=RehearsalVideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上传排练 / 演出复盘视频附件到 MinIO",
)
def upload_rehearsal_video(
    file: UploadFile = File(..., description="建议 15-60 秒、仅供老师人工查看的视频片段"),
    settings: Settings = Depends(get_settings),
) -> RehearsalVideoUploadResponse:
    """保存单个 M08 视频附件；本接口不会触发任何视频分析。"""

    try:
        result = save_rehearsal_video_upload(file=file, settings=settings)
    except RehearsalStorageError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return RehearsalVideoUploadResponse(
        object_key=result.object_key,
        original_file_name=result.original_file_name,
        content_type=result.content_type,
        size_bytes=result.size_bytes,
    )


@router.post(
    "/rehearsal-reviews/generate",
    response_model=RehearsalReviewGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建排练 / 演出复盘报告生成任务",
)
def generate_rehearsal_review(
    request: RehearsalReviewGenerateRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RehearsalReviewGenerateResponse:
    """基于人工观察记录和可选 M04/M05 上下文创建 M08 异步任务。"""

    musical_script = db.get(MusicalScript, request.script_id)
    if musical_script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="剧本不存在。")
    script_content = musical_script.edited_content or musical_script.content
    if not script_content:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="剧本内容尚未生成，无法创建复盘报告。")

    project = db.get(MusicalProject, musical_script.project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="剧目基础信息不存在，无法创建复盘报告。")

    fusion_plan: MusicalFusionPlan | None = None
    fusion_content: dict | None = None
    if request.fusion_plan_id is not None:
        fusion_plan = db.get(MusicalFusionPlan, request.fusion_plan_id)
        if fusion_plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌舞融合方案不存在。")
        if fusion_plan.script_id != musical_script.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="歌舞融合方案不属于当前剧本，不能用于本次复盘。",
            )
        fusion_content = fusion_plan.edited_content or fusion_plan.content
        if not fusion_content:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="歌舞融合内容尚未生成，无法用于复盘。")

    role_training_plan: RoleTrainingPlan | None = None
    role_training_content: dict | None = None
    if request.role_training_plan_id is not None:
        role_training_plan = db.get(RoleTrainingPlan, request.role_training_plan_id)
        if role_training_plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分角色训练计划不存在。")
        if role_training_plan.script_id != musical_script.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="分角色训练计划不属于当前剧本，不能用于本次复盘。",
            )
        role_training_content = role_training_plan.edited_content or role_training_plan.content
        if not role_training_content:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="分角色训练内容尚未生成，无法用于复盘。")

    video_content_type = ""
    video_size_bytes: int | None = None
    if request.video_object_key:
        try:
            object_info = stat_rehearsal_video(request.video_object_key, settings=settings)
        except RehearsalStorageError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        if object_info.size_bytes != request.video_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="视频附件大小与 MinIO 中的对象不一致，请重新上传。",
            )
        video_content_type = object_info.content_type
        video_size_bytes = object_info.size_bytes

    llm_provider, llm_model, reasoning_level = _resolve_llm_options(
        request.llm_provider,
        request.llm_model,
        request.reasoning_level,
        settings,
    )
    event_label = "演出" if request.event_type == "performance" else "排练"
    review = RehearsalReview(
        project_id=musical_script.project_id,
        script_id=musical_script.id,
        fusion_plan_id=fusion_plan.id if fusion_plan else None,
        role_training_plan_id=role_training_plan.id if role_training_plan else None,
        title=f"{musical_script.title} · {request.event_date.isoformat()} {event_label}复盘",
        status="generating",
        event_type=request.event_type,
        event_date=request.event_date,
        rehearsal_content=request.rehearsal_content,
        observation_notes=request.observation_notes,
        strengths=request.strengths,
        issues=request.issues,
        review_focus=request.review_focus,
        next_goal=request.next_goal,
        video_object_key=request.video_object_key,
        video_original_file_name=request.video_original_file_name,
        video_content_type=video_content_type,
        video_size_bytes=video_size_bytes,
        video_notes=request.video_notes,
    )
    db.add(review)
    db.flush()

    # 严格排除 MinIO 对象键、文件名和视频内容。大模型只知道“有附件”和老师人工备注，
    # 避免模型误以为自己已经查看或分析了视频。
    input_snapshot = {
        "script_id": str(musical_script.id),
        "fusion_plan_id": str(fusion_plan.id) if fusion_plan else None,
        "role_training_plan_id": str(role_training_plan.id) if role_training_plan else None,
        "project_title": project.title,
        "script_title": musical_script.title,
        "event_type": request.event_type,
        "event_date": request.event_date.isoformat(),
        "rehearsal_content": request.rehearsal_content,
        "observation_notes": request.observation_notes,
        "strengths": request.strengths,
        "issues": request.issues,
        "review_focus": request.review_focus,
        "next_goal": request.next_goal,
        "has_video_attachment": bool(request.video_object_key),
        "video_notes": request.video_notes,
        "script_content": script_content,
        "fusion_plan_title": fusion_plan.title if fusion_plan else None,
        "fusion_content": fusion_content,
        "role_training_plan_title": role_training_plan.title if role_training_plan else None,
        "role_training_content": role_training_content,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "reasoning_level": reasoning_level,
    }
    task = AiTask(
        task_type="rehearsal_review.generate",
        status="PENDING",
        progress=5,
        business_id=review.id,
        input_snapshot=input_snapshot,
    )
    db.add(task)
    db.commit()

    try:
        enqueue_rehearsal_review_task(
            {
                "task_id": task.id,
                "rehearsal_review_id": review.id,
                "task_type": task.task_type,
            }
        )
    except QueueUnavailableError as exc:
        task.status = "FAILED"
        task.progress = 100
        task.error_code = "QUEUE_UNAVAILABLE"
        task.error_message = str(exc)
        task.finished_at = datetime.utcnow()
        review.status = "failed"
        review.updated_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return RehearsalReviewGenerateResponse(
        task_id=task.id,
        rehearsal_review_id=review.id,
        status=task.status,
        message="排练复盘任务已创建，前端可以通过 task_id 轮询进度。",
    )


@router.get(
    "/rehearsal-reviews",
    response_model=list[RehearsalReviewSummaryResponse],
    summary="查询已保存排练 / 演出复盘报告列表",
)
def list_rehearsal_reviews(db: Session = Depends(get_db)) -> list[RehearsalReviewSummaryResponse]:
    """按更新时间倒序返回 M08 复盘报告摘要。"""

    reviews = db.query(RehearsalReview).order_by(desc(RehearsalReview.updated_at)).all()
    return [rehearsal_review_summary(review) for review in reviews]


@router.get(
    "/rehearsal-reviews/{rehearsal_review_id}",
    response_model=RehearsalReviewResponse,
    summary="读取排练 / 演出复盘报告详情",
)
def get_rehearsal_review(
    rehearsal_review_id: UUID,
    db: Session = Depends(get_db),
) -> RehearsalReviewResponse:
    """返回 M08 AI 初稿、人工编辑稿和安全附件元数据。"""

    review = db.get(RehearsalReview, rehearsal_review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排练复盘报告不存在。")
    return review


@router.put(
    "/rehearsal-reviews/{rehearsal_review_id}",
    response_model=RehearsalReviewResponse,
    summary="保存老师或编导编辑后的复盘报告",
)
def update_rehearsal_review(
    rehearsal_review_id: UUID,
    request: RehearsalReviewUpdateRequest,
    db: Session = Depends(get_db),
) -> RehearsalReviewResponse:
    """保存人工确认稿，并保留原始 AI 初稿供后续回溯。"""

    review = db.get(RehearsalReview, rehearsal_review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排练复盘报告不存在。")
    edited_content = request.edited_content.model_dump()
    review.edited_content = edited_content
    review.content = review.content or edited_content
    review.title = request.edited_content.title
    review.status = "reviewed"
    review.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(review)
    return review


@router.get(
    "/rehearsal-reviews/{rehearsal_review_id}/markdown",
    response_class=PlainTextResponse,
    summary="导出排练 / 演出复盘报告 Markdown",
)
def export_rehearsal_review_markdown(
    rehearsal_review_id: UUID,
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    """导出 Markdown，优先使用老师或编导编辑确认稿。"""

    review = db.get(RehearsalReview, rehearsal_review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排练复盘报告不存在。")
    markdown = render_rehearsal_review_markdown(review)
    if markdown is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="复盘报告尚未生成，无法导出。")
    return PlainTextResponse(content=markdown, media_type="text/markdown; charset=utf-8")


@router.get(
    "/rehearsal-reviews/{rehearsal_review_id}/video",
    summary="代理播放 MinIO 中的排练 / 演出视频附件",
)
def stream_rehearsal_video(
    rehearsal_review_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """通过报告 ID 代理私有桶对象，并支持浏览器单段 Range 播放。"""

    review = db.get(RehearsalReview, rehearsal_review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排练复盘报告不存在。")
    if not review.video_object_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="本报告没有视频附件。")

    try:
        object_info = stat_rehearsal_video(review.video_object_key, settings=settings)
        byte_range = parse_video_range(request.headers.get("range"), object_info.size_bytes)
    except RehearsalStorageError as exc:
        headers = {"Content-Range": f"bytes */{review.video_size_bytes or 0}"} if exc.status_code == 416 else None
        raise HTTPException(status_code=exc.status_code, detail=str(exc), headers=headers) from exc

    response_status = status.HTTP_206_PARTIAL_CONTENT if byte_range else status.HTTP_200_OK
    content_length = byte_range.length if byte_range else object_info.size_bytes
    try:
        minio_response = open_rehearsal_video(
            review.video_object_key,
            offset=byte_range.start if byte_range else 0,
            length=byte_range.length if byte_range else None,
            settings=settings,
        )
    except RehearsalStorageError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    safe_name = quote(review.video_original_file_name or "rehearsal-video", safe="")
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Disposition": f"inline; filename*=UTF-8''{safe_name}",
    }
    if byte_range:
        headers["Content-Range"] = f"bytes {byte_range.start}-{byte_range.end}/{object_info.size_bytes}"
    return StreamingResponse(
        iter_minio_response(minio_response),
        status_code=response_status,
        media_type=object_info.content_type,
        headers=headers,
    )


@router.delete(
    "/rehearsal-reviews/{rehearsal_review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除排练 / 演出复盘报告",
)
def delete_rehearsal_review(
    rehearsal_review_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    """删除报告、关联 AI 任务和 MinIO 视频，不删除上游剧本或训练计划。"""

    try:
        deleted = delete_rehearsal_review_with_related_data(db, rehearsal_review_id)
    except RehearsalStorageError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排练复盘报告不存在。")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _resolve_llm_options(
    requested_provider: str | None,
    requested_model: str | None,
    requested_reasoning_level: str | None,
    settings: Settings,
) -> tuple[str, str, str]:
    """解析并校验 M08 使用的大模型选项。"""

    default_provider = settings.llm_default_provider if settings.llm_default_provider in {"deepseek", "qwen"} else "deepseek"
    provider = requested_provider or default_provider
    if provider not in {"deepseek", "qwen"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的大模型供应商。")

    fallback_model = "qwen3.7-plus" if provider == "qwen" else "deepseek-v4-flash"
    model = requested_model or (settings.llm_default_model if is_supported_model(provider, settings.llm_default_model) else fallback_model)
    if not is_supported_model(provider, model):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{provider} 不支持模型 {model}。")

    reasoning_level = requested_reasoning_level or settings.llm_default_reasoning_level
    if reasoning_level not in REASONING_LEVELS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的推理强度。")
    return provider, model, reasoning_level
