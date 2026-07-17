from copy import deepcopy
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.llm_options import is_supported_model, is_supported_reasoning_level, models_for_provider
from app.models import AiTask, Course, LessonPlan, LessonPlanVariant
from app.services.lesson_plan_queue import QueueUnavailableError, enqueue_lesson_plan_task
from app.services.lesson_plan_service import (
    build_course_title,
    delete_lesson_plan_with_related_data,
    lesson_plan_response,
    lesson_plan_summary,
    render_lesson_plan_markdown,
    variant_type_label,
)
from app.schemas import (
    AiTaskResponse,
    LessonPlanGenerateRequest,
    LessonPlanGenerateResponse,
    LessonPlanResponse,
    LessonPlanSummaryResponse,
    LessonPlanUpdateRequest,
    LessonPlanVariantGenerateRequest,
    LessonPlanVariantGenerateResponse,
)

router = APIRouter(prefix="/api", tags=["lesson-plans"])


@router.post(
    "/lesson-plans/generate",
    response_model=LessonPlanGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建课前教案生成任务",
)
def generate_lesson_plan(
    request: LessonPlanGenerateRequest,
    db: Session = Depends(get_db),
) -> LessonPlanGenerateResponse:
    """创建课程草稿、教案草稿和 AI 异步任务，并写入 Redis 队列。"""

    llm_provider, llm_model, reasoning_level = _resolve_llm_options(
        request.llm_provider,
        request.llm_model,
        request.reasoning_level,
    )

    course = Course(
        title=build_course_title(request),
        dance_style=request.dance_style,
        theme=request.theme,
        age_group=request.age_group,
        duration_minutes=request.duration_minutes,
        student_count=request.student_count,
        teaching_goal=request.teaching_goal,
        learning_level=request.learning_level,
        course_style=request.course_style,
        notes=request.notes,
    )
    db.add(course)
    db.flush()

    lesson_plan = LessonPlan(course_id=course.id, title=course.title, status="generating")
    db.add(lesson_plan)
    db.flush()

    input_snapshot = request.model_dump()
    input_snapshot["llm_provider"] = llm_provider
    input_snapshot["llm_model"] = llm_model
    input_snapshot["reasoning_level"] = reasoning_level
    task = AiTask(
        task_type="lesson_plan.generate",
        status="PENDING",
        progress=5,
        business_id=lesson_plan.id,
        input_snapshot=input_snapshot,
    )
    db.add(task)
    db.commit()

    try:
        enqueue_lesson_plan_task(
            {
                "task_id": task.id,
                "lesson_plan_id": lesson_plan.id,
                "course_id": course.id,
                "task_type": task.task_type,
            }
        )
    except QueueUnavailableError as exc:
        task.status = "FAILED"
        task.progress = 100
        task.error_code = "QUEUE_UNAVAILABLE"
        task.error_message = str(exc)
        task.finished_at = datetime.utcnow()
        lesson_plan.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return LessonPlanGenerateResponse(
        task_id=task.id,
        lesson_plan_id=lesson_plan.id,
        status=task.status,
        message="教案生成任务已创建，前端可以通过 task_id 轮询进度。",
    )


@router.get("/lesson-plans", response_model=list[LessonPlanSummaryResponse], summary="查询已保存教案列表")
def list_lesson_plans(db: Session = Depends(get_db)) -> list[LessonPlanSummaryResponse]:
    """按更新时间倒序返回教案摘要列表。"""

    lesson_plans = db.query(LessonPlan).order_by(desc(LessonPlan.updated_at)).all()
    variant_map = {variant.lesson_plan_id: variant for variant in db.query(LessonPlanVariant).all()}
    return [lesson_plan_summary(lesson_plan, variant_map.get(lesson_plan.id)) for lesson_plan in lesson_plans]


@router.post(
    "/lesson-plans/{source_lesson_plan_id}/variants/generate",
    response_model=LessonPlanVariantGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="基于原教案创建 T02 变体生成任务",
)
def generate_lesson_plan_variant(
    source_lesson_plan_id: UUID,
    request: LessonPlanVariantGenerateRequest,
    db: Session = Depends(get_db),
) -> LessonPlanVariantGenerateResponse:
    """冻结老师确认稿并创建一个独立的一级教案变体。"""

    source_lesson_plan = db.get(LessonPlan, source_lesson_plan_id)
    if source_lesson_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="原教案不存在。")
    if db.get(LessonPlanVariant, source_lesson_plan.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="第一版只允许从原教案生成一级变体，不能继续从变体派生。",
        )

    source_content = source_lesson_plan.edited_content or source_lesson_plan.content
    if not source_content:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="原教案尚未生成可用正文，无法创建变体。")
    course = db.get(Course, source_lesson_plan.course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="原教案关联的课程信息不存在。")

    llm_provider, llm_model, reasoning_level = _resolve_llm_options(
        request.llm_provider,
        request.llm_model,
        request.reasoning_level,
    )
    version_label = variant_type_label(request.variant_type)
    source_snapshot = deepcopy(source_content)
    lesson_plan = LessonPlan(
        course_id=source_lesson_plan.course_id,
        title=f"{source_lesson_plan.title} · {version_label}",
        status="generating",
    )
    db.add(lesson_plan)
    db.flush()

    db.add(
        LessonPlanVariant(
            lesson_plan_id=lesson_plan.id,
            source_lesson_plan_id=source_lesson_plan.id,
            variant_type=request.variant_type,
            adjustment_direction=request.adjustment_direction,
            source_title_snapshot=source_lesson_plan.title,
            source_content_snapshot=source_snapshot,
        )
    )

    input_snapshot = request.model_dump(mode="json")
    input_snapshot.update(
        {
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "reasoning_level": reasoning_level,
            "source_lesson_plan_id": str(source_lesson_plan.id),
            "source_title": source_lesson_plan.title,
            "source_content": source_snapshot,
            "course": {
                "title": course.title,
                "dance_style": course.dance_style,
                "theme": course.theme,
                "age_group": course.age_group,
                "duration_minutes": course.duration_minutes,
                "student_count": course.student_count,
                "learning_level": course.learning_level,
                "course_style": course.course_style,
                "teaching_goal": course.teaching_goal,
                "notes": course.notes,
            },
        }
    )
    task = AiTask(
        task_type="lesson_plan.variant.generate",
        status="PENDING",
        progress=5,
        business_id=lesson_plan.id,
        input_snapshot=input_snapshot,
    )
    db.add(task)
    db.commit()

    try:
        enqueue_lesson_plan_task(
            {
                "task_id": task.id,
                "lesson_plan_id": lesson_plan.id,
                "course_id": course.id,
                "task_type": task.task_type,
            }
        )
    except QueueUnavailableError as exc:
        task.status = "FAILED"
        task.progress = 100
        task.error_code = "QUEUE_UNAVAILABLE"
        task.error_message = str(exc)
        task.finished_at = datetime.utcnow()
        lesson_plan.status = "failed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return LessonPlanVariantGenerateResponse(
        task_id=task.id,
        lesson_plan_id=lesson_plan.id,
        status=task.status,
        message=f"{version_label}生成任务已创建，前端可以通过 task_id 轮询进度。",
    )


@router.get(
    "/lesson-plans/{source_lesson_plan_id}/variants",
    response_model=list[LessonPlanSummaryResponse],
    summary="查询原教案的 T02 变体列表",
)
def list_lesson_plan_variants(
    source_lesson_plan_id: UUID,
    db: Session = Depends(get_db),
) -> list[LessonPlanSummaryResponse]:
    """返回直接挂在原教案下的一级变体，不构建多级版本树。"""

    if db.get(LessonPlan, source_lesson_plan_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="原教案不存在。")
    variants = (
        db.query(LessonPlanVariant)
        .filter(LessonPlanVariant.source_lesson_plan_id == source_lesson_plan_id)
        .order_by(desc(LessonPlanVariant.created_at))
        .all()
    )
    results: list[LessonPlanSummaryResponse] = []
    for variant in variants:
        lesson_plan = db.get(LessonPlan, variant.lesson_plan_id)
        if lesson_plan is not None:
            results.append(lesson_plan_summary(lesson_plan, variant))
    return results


@router.get("/ai-tasks/{task_id}", response_model=AiTaskResponse, summary="查询 AI 任务状态")
def get_ai_task(task_id: UUID, db: Session = Depends(get_db)) -> AiTaskResponse:
    """返回 AI 任务状态，供前端轮询。"""

    task = db.get(AiTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 任务不存在。")
    return task


@router.get("/lesson-plans/{lesson_plan_id}", response_model=LessonPlanResponse, summary="读取教案详情")
def get_lesson_plan(lesson_plan_id: UUID, db: Session = Depends(get_db)) -> LessonPlanResponse:
    """返回 AI 初稿和老师编辑稿。"""

    lesson_plan = db.get(LessonPlan, lesson_plan_id)
    if lesson_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教案不存在。")
    variant = db.get(LessonPlanVariant, lesson_plan.id)
    return lesson_plan_response(lesson_plan, variant)


@router.get(
    "/lesson-plans/{lesson_plan_id}/markdown",
    response_class=PlainTextResponse,
    summary="导出教案 Markdown",
)
def export_lesson_plan_markdown(lesson_plan_id: UUID, db: Session = Depends(get_db)) -> PlainTextResponse:
    """导出 Markdown 文本，优先使用老师编辑稿。"""

    lesson_plan = db.get(LessonPlan, lesson_plan_id)
    if lesson_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教案不存在。")

    variant = db.get(LessonPlanVariant, lesson_plan.id)
    markdown = render_lesson_plan_markdown(lesson_plan, variant)
    if markdown is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="教案内容尚未生成，无法导出。")
    return PlainTextResponse(content=markdown, media_type="text/markdown; charset=utf-8")


@router.delete(
    "/lesson-plans/{lesson_plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除已保存教案",
)
def delete_lesson_plan(lesson_plan_id: UUID, db: Session = Depends(get_db)) -> Response:
    """删除教案、关联 AI 任务，并在课程草稿无人引用时一并清理。"""

    deleted = delete_lesson_plan_with_related_data(db, lesson_plan_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教案不存在。")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/lesson-plans/{lesson_plan_id}", response_model=LessonPlanResponse, summary="保存老师编辑后的教案")
def update_lesson_plan(
    lesson_plan_id: UUID,
    request: LessonPlanUpdateRequest,
    db: Session = Depends(get_db),
) -> LessonPlanResponse:
    """保存老师确认或修改后的教案版本。"""

    lesson_plan = db.get(LessonPlan, lesson_plan_id)
    if lesson_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教案不存在。")

    edited_content = request.edited_content.model_dump()
    lesson_plan.edited_content = edited_content
    lesson_plan.content = lesson_plan.content or edited_content
    lesson_plan.title = request.edited_content.title
    lesson_plan.status = "reviewed"
    lesson_plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lesson_plan)
    variant = db.get(LessonPlanVariant, lesson_plan.id)
    return lesson_plan_response(lesson_plan, variant)


def _resolve_llm_options(
    requested_provider: str | None,
    requested_model: str | None,
    requested_reasoning_level: str | None,
) -> tuple[str, str, str]:
    """统一解析 T01/T02 的模型供应商、模型和推理强度。"""

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
