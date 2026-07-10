from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.llm_options import is_supported_model, is_supported_reasoning_level, models_for_provider
from app.models import AiTask, ClassInteraction, Course, LessonPlan
from app.schemas import (
    ClassInteractionGenerateRequest,
    ClassInteractionGenerateResponse,
    ClassInteractionResponse,
    ClassInteractionSummaryResponse,
    ClassInteractionUpdateRequest,
    LessonInteractionPrefillResponse,
)
from app.services.class_interaction_queue import QueueUnavailableError, enqueue_class_interaction_task
from app.services.class_interaction_service import (
    build_lesson_interaction_prefill,
    class_interaction_summary,
    delete_class_interaction_with_task,
    render_class_interaction_markdown,
)


router = APIRouter(prefix="/api", tags=["class-interactions"])


@router.post(
    "/interactions/generate",
    response_model=ClassInteractionGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建课堂互动方案生成任务",
)
def generate_class_interaction(
    request: ClassInteractionGenerateRequest,
    db: Session = Depends(get_db),
) -> ClassInteractionGenerateResponse:
    """创建 T05 课堂互动方案草稿和 AI 异步任务，并写入 Redis 队列。"""

    llm_provider, llm_model, reasoning_level = _resolve_llm_options(
        request.llm_provider,
        request.llm_model,
        request.reasoning_level,
    )
    lesson_context_snapshot = _build_lesson_context_snapshot(db, request.source_lesson_plan_id)

    class_interaction = ClassInteraction(
        source_lesson_plan_id=request.source_lesson_plan_id,
        title=f"{request.course_theme} · {request.teaching_phase}互动",
        status="generating",
        course_theme=request.course_theme,
        age_group=request.age_group,
        teaching_phase=request.teaching_phase,
        interaction_goal=request.interaction_goal,
        class_style=request.class_style,
        duration_minutes=request.duration_minutes,
        student_count=request.student_count,
        space_materials=request.space_materials,
        lesson_context=request.lesson_context,
        lesson_context_snapshot=lesson_context_snapshot,
    )
    db.add(class_interaction)
    db.flush()

    input_snapshot = request.model_dump(mode="json")
    input_snapshot["llm_provider"] = llm_provider
    input_snapshot["llm_model"] = llm_model
    input_snapshot["reasoning_level"] = reasoning_level
    task = AiTask(
        task_type="class_interaction.generate",
        status="PENDING",
        progress=5,
        business_id=class_interaction.id,
        input_snapshot=input_snapshot,
    )
    db.add(task)
    db.commit()

    try:
        enqueue_class_interaction_task(
            {
                "task_id": task.id,
                "class_interaction_id": class_interaction.id,
                "task_type": task.task_type,
            }
        )
    except QueueUnavailableError as exc:
        task.status = "FAILED"
        task.progress = 100
        task.error_code = "QUEUE_UNAVAILABLE"
        task.error_message = str(exc)
        task.finished_at = datetime.utcnow()
        class_interaction.status = "failed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return ClassInteractionGenerateResponse(
        task_id=task.id,
        class_interaction_id=class_interaction.id,
        status=task.status,
        message="课堂互动方案生成任务已创建，前端可以通过 task_id 轮询进度。",
    )


@router.get(
    "/interactions",
    response_model=list[ClassInteractionSummaryResponse],
    summary="查询已保存课堂互动方案列表",
)
def list_class_interactions(db: Session = Depends(get_db)) -> list[ClassInteractionSummaryResponse]:
    """按更新时间倒序返回课堂互动方案摘要。"""

    interactions = db.query(ClassInteraction).order_by(desc(ClassInteraction.updated_at)).all()
    return [class_interaction_summary(interaction) for interaction in interactions]


@router.get(
    "/interactions/prefill-from-lesson/{lesson_plan_id}",
    response_model=LessonInteractionPrefillResponse,
    summary="从教案预填课堂互动生成表单",
)
def prefill_class_interaction_from_lesson(
    lesson_plan_id: UUID,
    db: Session = Depends(get_db),
) -> LessonInteractionPrefillResponse:
    """读取课程和老师确认稿，返回独立的表单预填快照，不修改原教案。"""

    lesson_plan = db.get(LessonPlan, lesson_plan_id)
    if lesson_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教案不存在。")
    course = db.get(Course, lesson_plan.course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="教案关联的课程信息不存在。")
    return build_lesson_interaction_prefill(course, lesson_plan)


@router.get(
    "/interactions/{class_interaction_id}",
    response_model=ClassInteractionResponse,
    summary="读取课堂互动方案详情",
)
def get_class_interaction(
    class_interaction_id: UUID,
    db: Session = Depends(get_db),
) -> ClassInteractionResponse:
    """返回 AI 初稿和老师编辑稿。"""

    class_interaction = db.get(ClassInteraction, class_interaction_id)
    if class_interaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课堂互动方案不存在。")
    return class_interaction


@router.put(
    "/interactions/{class_interaction_id}",
    response_model=ClassInteractionResponse,
    summary="保存老师编辑后的课堂互动方案",
)
def update_class_interaction(
    class_interaction_id: UUID,
    request: ClassInteractionUpdateRequest,
    db: Session = Depends(get_db),
) -> ClassInteractionResponse:
    """保存老师确认稿，同时同步列表展示所需的标题、阶段、目标和时长。"""

    class_interaction = db.get(ClassInteraction, class_interaction_id)
    if class_interaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课堂互动方案不存在。")

    edited_content = request.edited_content.model_dump()
    class_interaction.edited_content = edited_content
    class_interaction.content = class_interaction.content or edited_content
    class_interaction.title = request.edited_content.title
    class_interaction.teaching_phase = request.edited_content.teaching_phase
    class_interaction.interaction_goal = request.edited_content.interaction_goal
    class_interaction.duration_minutes = request.edited_content.duration_minutes
    class_interaction.space_materials = request.edited_content.space_materials
    class_interaction.status = "reviewed"
    class_interaction.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(class_interaction)
    return class_interaction


@router.get(
    "/interactions/{class_interaction_id}/markdown",
    response_class=PlainTextResponse,
    summary="导出课堂互动方案 Markdown",
)
def export_class_interaction_markdown(
    class_interaction_id: UUID,
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    """导出可打印的 Markdown 文本，优先使用老师编辑稿。"""

    class_interaction = db.get(ClassInteraction, class_interaction_id)
    if class_interaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课堂互动方案不存在。")
    markdown = render_class_interaction_markdown(class_interaction)
    if markdown is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="课堂互动方案尚未生成，无法导出。")
    return PlainTextResponse(content=markdown, media_type="text/markdown; charset=utf-8")


@router.delete(
    "/interactions/{class_interaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除已保存课堂互动方案",
)
def delete_class_interaction(class_interaction_id: UUID, db: Session = Depends(get_db)) -> Response:
    """删除课堂互动方案和关联任务，不删除或修改来源教案。"""

    deleted = delete_class_interaction_with_task(db, class_interaction_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课堂互动方案不存在。")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _build_lesson_context_snapshot(db: Session, lesson_plan_id: UUID | None) -> dict | None:
    """在创建任务时保存来源教案快照，供追溯使用。"""

    if lesson_plan_id is None:
        return None

    lesson_plan = db.get(LessonPlan, lesson_plan_id)
    if lesson_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="来源教案不存在。")
    course = db.get(Course, lesson_plan.course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="来源教案关联的课程信息不存在。")
    return {
        "source_lesson_plan_id": str(lesson_plan.id),
        "lesson_title": lesson_plan.title,
        "lesson_content": lesson_plan.edited_content or lesson_plan.content,
        "course": {
            "theme": course.theme,
            "age_group": course.age_group,
            "student_count": course.student_count,
            "course_style": course.course_style,
            "teaching_goal": course.teaching_goal,
            "notes": course.notes,
        },
    }


def _resolve_llm_options(
    requested_provider: str | None,
    requested_model: str | None,
    requested_reasoning_level: str | None,
) -> tuple[str, str, str]:
    """解析并校验本次任务使用的供应商、模型和推理强度。"""

    settings = get_settings()
    default_provider = settings.llm_default_provider if settings.llm_default_provider in {"deepseek", "qwen"} else "deepseek"
    llm_provider = requested_provider or default_provider
    if llm_provider not in {"deepseek", "qwen"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的大模型供应商。")

    default_reasoning_level = (
        settings.llm_default_reasoning_level
        if is_supported_reasoning_level(settings.llm_default_reasoning_level)
        else "standard"
    )
    reasoning_level = requested_reasoning_level or default_reasoning_level
    supported_models = models_for_provider(llm_provider)
    default_model = settings.llm_default_model if settings.llm_default_model in supported_models else supported_models[0]
    llm_model = requested_model or default_model

    if not is_supported_model(llm_provider, llm_model):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{llm_provider} 不支持模型 {llm_model}，可选模型：{'、'.join(supported_models)}。",
        )
    if not is_supported_reasoning_level(reasoning_level):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的推理强度。")
    return llm_provider, llm_model, reasoning_level
