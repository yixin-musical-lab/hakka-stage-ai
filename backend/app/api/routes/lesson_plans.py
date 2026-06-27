from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.llm_options import is_supported_model, is_supported_reasoning_level, models_for_provider
from app.models import AiTask, Course, LessonPlan
from app.services.lesson_plan_queue import QueueUnavailableError, enqueue_lesson_plan_task
from app.services.lesson_plan_service import (
    build_course_title,
    delete_lesson_plan_with_related_data,
    lesson_plan_summary,
    render_lesson_plan_markdown,
)
from app.schemas import (
    AiTaskResponse,
    LessonPlanGenerateRequest,
    LessonPlanGenerateResponse,
    LessonPlanResponse,
    LessonPlanSummaryResponse,
    LessonPlanUpdateRequest,
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

    settings = get_settings()
    default_provider = settings.llm_default_provider if settings.llm_default_provider in {"deepseek", "qwen"} else "deepseek"
    llm_provider = request.llm_provider or default_provider
    default_reasoning_level = (
        settings.llm_default_reasoning_level
        if is_supported_reasoning_level(settings.llm_default_reasoning_level)
        else "standard"
    )
    reasoning_level = request.reasoning_level or default_reasoning_level
    default_models = models_for_provider(llm_provider)
    default_model = settings.llm_default_model if settings.llm_default_model in default_models else default_models[0]
    llm_model = request.llm_model or default_model

    if llm_provider not in {"deepseek", "qwen"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的大模型供应商。")
    if not is_supported_model(llm_provider, llm_model):
        supported_models = "、".join(models_for_provider(llm_provider))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{llm_provider} 不支持模型 {llm_model}，可选模型：{supported_models}。",
        )
    if not is_supported_reasoning_level(reasoning_level):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的推理强度。")

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
    return [lesson_plan_summary(lesson_plan) for lesson_plan in lesson_plans]


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
    return lesson_plan


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

    markdown = render_lesson_plan_markdown(lesson_plan)
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
    return lesson_plan
