from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import MovementGuide
from app.schemas import (
    MovementGuideCreateRequest,
    MovementGuideGeneratePlaceholderResponse,
    MovementGuideResponse,
    MovementGuideSummaryResponse,
    MovementGuideUpdateRequest,
)
from app.services.movement_guide_service import (
    build_initial_content,
    build_movement_guide_title,
    delete_movement_guide_with_related_data,
    movement_guide_summary,
    render_movement_guide_markdown,
)

router = APIRouter(prefix="/api", tags=["movement-guides"])


@router.post(
    "/movement-guides",
    response_model=MovementGuideResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建动作图解 / 示范材料",
)
def create_movement_guide(
    request: MovementGuideCreateRequest,
    db: Session = Depends(get_db),
) -> MovementGuideResponse:
    """创建 T03 动作图解材料。

    当前阶段先沉淀老师可编辑的文字拆解和材料链接，不触发本地视频生成或云端模型任务。
    """

    title = build_movement_guide_title(request)
    movement_guide = MovementGuide(
        title=title,
        action_name=request.action_name,
        action_description=request.action_description,
        course_context=request.course_context,
        beats=request.beats,
        body_direction=request.body_direction,
        difficulty=request.difficulty,
        teaching_tips=request.teaching_tips,
        reference_video_url=request.reference_video_url,
        digital_human_image_url=request.digital_human_image_url,
        status="draft",
        content=build_initial_content(request),
        raw_pipeline_info={
            "pipeline": "manual_first_stage",
            "kimodo": "not_connected",
            "digital_human_video": "not_connected",
        },
    )
    db.add(movement_guide)
    db.commit()
    db.refresh(movement_guide)
    return movement_guide


@router.get(
    "/movement-guides",
    response_model=list[MovementGuideSummaryResponse],
    summary="查询动作图解 / 示范材料列表",
)
def list_movement_guides(db: Session = Depends(get_db)) -> list[MovementGuideSummaryResponse]:
    """按更新时间倒序返回示范材料摘要列表。"""

    movement_guides = db.query(MovementGuide).order_by(desc(MovementGuide.updated_at)).all()
    return [movement_guide_summary(movement_guide) for movement_guide in movement_guides]


@router.get(
    "/movement-guides/{movement_guide_id}",
    response_model=MovementGuideResponse,
    summary="读取动作图解 / 示范材料详情",
)
def get_movement_guide(movement_guide_id: UUID, db: Session = Depends(get_db)) -> MovementGuideResponse:
    """返回动作图解初稿和老师编辑稿。"""

    movement_guide = db.get(MovementGuide, movement_guide_id)
    if movement_guide is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="动作图解材料不存在。")
    return movement_guide


@router.put(
    "/movement-guides/{movement_guide_id}",
    response_model=MovementGuideResponse,
    summary="保存老师编辑后的动作图解 / 示范材料",
)
def update_movement_guide(
    movement_guide_id: UUID,
    request: MovementGuideUpdateRequest,
    db: Session = Depends(get_db),
) -> MovementGuideResponse:
    """保存老师确认或修改后的动作图解版本。"""

    movement_guide = db.get(MovementGuide, movement_guide_id)
    if movement_guide is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="动作图解材料不存在。")

    edited_content = request.edited_content.model_dump()
    movement_guide.edited_content = edited_content
    movement_guide.content = movement_guide.content or edited_content
    movement_guide.title = request.edited_content.title
    movement_guide.action_name = request.edited_content.action_name
    movement_guide.action_description = request.edited_content.action_description
    movement_guide.course_context = request.edited_content.course_context
    movement_guide.beats = request.edited_content.beats
    movement_guide.body_direction = request.edited_content.body_direction
    movement_guide.difficulty = request.edited_content.difficulty
    movement_guide.teaching_tips = "；".join(request.edited_content.teaching_tips)
    movement_guide.status = _derive_status(edited_content)
    movement_guide.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(movement_guide)
    return movement_guide


@router.get(
    "/movement-guides/{movement_guide_id}/markdown",
    response_class=PlainTextResponse,
    summary="导出动作图解 / 示范材料 Markdown",
)
def export_movement_guide_markdown(movement_guide_id: UUID, db: Session = Depends(get_db)) -> PlainTextResponse:
    """导出 Markdown 文本，优先使用老师编辑稿。"""

    movement_guide = db.get(MovementGuide, movement_guide_id)
    if movement_guide is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="动作图解材料不存在。")

    markdown = render_movement_guide_markdown(movement_guide)
    if markdown is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="动作图解内容尚未创建，无法导出。")
    return PlainTextResponse(content=markdown, media_type="text/markdown; charset=utf-8")


@router.post(
    "/movement-guides/{movement_guide_id}/generate-candidates",
    response_model=MovementGuideGeneratePlaceholderResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="生成骨骼动画候选（第一阶段占位）",
)
def generate_movement_candidates(
    movement_guide_id: UUID,
    db: Session = Depends(get_db),
) -> MovementGuideGeneratePlaceholderResponse:
    """为后续 Kimodo / Worker 链路预留接口，不在本机 API 服务执行重型视频生成。"""

    movement_guide = db.get(MovementGuide, movement_guide_id)
    if movement_guide is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="动作图解材料不存在。")

    return MovementGuideGeneratePlaceholderResponse(
        movement_guide_id=movement_guide.id,
        status="not_implemented",
        message="第一阶段仅完成动作图解和示范材料管理；骨骼动画候选生成需要后续接入 Worker、Kimodo 和云端 GPU。",
    )


@router.delete(
    "/movement-guides/{movement_guide_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除动作图解 / 示范材料",
)
def delete_movement_guide(movement_guide_id: UUID, db: Session = Depends(get_db)) -> Response:
    """删除动作图解记录。"""

    deleted = delete_movement_guide_with_related_data(db, movement_guide_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="动作图解材料不存在。")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _derive_status(content: dict) -> str:
    """根据老师编辑稿中的确认材料状态推导列表状态。"""

    media_assets = content.get("media_assets", [])
    if isinstance(media_assets, list) and any(
        isinstance(item, dict) and item.get("status") == "confirmed" for item in media_assets
    ):
        return "confirmed"
    return "reviewed"
