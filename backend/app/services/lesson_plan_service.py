from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AiTask, Course, LessonPlan
from app.schemas import LessonPlanGenerateRequest, LessonPlanSummaryResponse


def build_course_title(request: LessonPlanGenerateRequest) -> str:
    """根据表单内容生成课程标题，方便列表和任务页面显示。"""

    return f"{request.theme} · {request.dance_style}教案"


def model_info(lesson_plan: LessonPlan) -> tuple[str | None, str | None]:
    """从模型信息里提取供应商和模型名。"""

    raw_model_info = lesson_plan.raw_model_info or {}
    provider = raw_model_info.get("provider")
    model = raw_model_info.get("model")
    return (
        provider if isinstance(provider, str) else None,
        model if isinstance(model, str) else None,
    )


def reasoning_level(lesson_plan: LessonPlan) -> str | None:
    """从模型信息里提取本次生成的推理强度。"""

    raw_model_info = lesson_plan.raw_model_info or {}
    value = raw_model_info.get("reasoning_level")
    return value if isinstance(value, str) else None


def lesson_plan_summary(lesson_plan: LessonPlan) -> LessonPlanSummaryResponse:
    """把 ORM 教案记录转成列表摘要。"""

    provider, model = model_info(lesson_plan)
    return LessonPlanSummaryResponse(
        id=lesson_plan.id,
        course_id=lesson_plan.course_id,
        title=lesson_plan.title,
        status=lesson_plan.status,
        provider=provider,
        model=model,
        reasoning_level=reasoning_level(lesson_plan),
        created_at=lesson_plan.created_at,
        updated_at=lesson_plan.updated_at,
    )


def render_lesson_plan_markdown(lesson_plan: LessonPlan) -> str | None:
    """把结构化教案渲染成 Markdown 文本。

    返回 None 表示教案正文尚未生成，HTTP 层再决定具体响应状态码。
    """

    content = lesson_plan.edited_content or lesson_plan.content
    if not content:
        return None

    raw_model_info = lesson_plan.raw_model_info or {}
    provider = raw_model_info.get("provider", "unknown")
    model = raw_model_info.get("model", "unknown")
    generated_at = raw_model_info.get("generated_at", "unknown")

    return "\n\n".join(
        [
            f"# {content.get('title', lesson_plan.title)}",
            "## 课程概况\n" + str(content.get("course_overview", "")),
            "## 教学目标\n" + _markdown_list(content.get("teaching_goals", [])),
            "## 教学重难点\n" + _markdown_list(content.get("key_points", [])),
            "## 易错点\n" + _markdown_list(content.get("common_mistakes", [])),
            "## 热身\n" + _activity_markdown(content.get("warmup", [])),
            "## 主体教学\n" + _activity_markdown(content.get("main_teaching", [])),
            "## 动作拆解\n" + _movement_markdown(content.get("movement_breakdown", [])),
            "## 放松\n" + _activity_markdown(content.get("cooldown", [])),
            "## 课后任务\n" + _markdown_list(content.get("homework", [])),
            "## 老师提醒\n" + _markdown_list(content.get("teacher_notes", [])),
            f"---\n\n模型信息：{provider} / {model} / {generated_at}",
        ]
    )


def delete_lesson_plan_with_related_data(db: Session, lesson_plan_id: UUID) -> bool:
    """删除教案、关联 AI 任务，并在课程草稿无人引用时清理课程。

    返回 False 表示目标教案不存在；调用方负责转换成 HTTP 404。
    """

    lesson_plan = db.get(LessonPlan, lesson_plan_id)
    if lesson_plan is None:
        return False

    course_id = lesson_plan.course_id

    # AI 任务通过 business_id 关联业务记录；这里删除同一教案的生成任务，避免列表数据被清掉后
    # 任务表仍保留孤立记录。后续如果引入审计日志，可以把这里改成软删除。
    db.query(AiTask).filter(AiTask.business_id == lesson_plan.id).delete(synchronize_session=False)

    # 使用 SQL 级删除明确先删除子表 lesson_plans，再清理父表 courses，避免 ORM flush 顺序
    # 在没有 relationship 配置时触发外键约束错误。
    db.query(LessonPlan).filter(LessonPlan.id == lesson_plan_id).delete(synchronize_session=False)
    db.flush()

    remaining_lesson_plan_count = db.query(LessonPlan).filter(LessonPlan.course_id == course_id).count()
    if remaining_lesson_plan_count == 0:
        course = db.get(Course, course_id)
        if course is not None:
            db.query(Course).filter(Course.id == course_id).delete(synchronize_session=False)

    db.commit()
    return True


def _markdown_list(items: list[str]) -> str:
    """把字符串列表渲染成 Markdown 列表。"""

    if not items:
        return "- 暂无"
    return "\n".join(f"- {item}" for item in items)


def _activity_markdown(items: list[dict]) -> str:
    """把课堂活动列表渲染成 Markdown。"""

    if not items:
        return "- 暂无"
    lines: list[str] = []
    for item in items:
        lines.append(f"- **{item.get('name', '未命名环节')}**（{item.get('duration_minutes', 0)} 分钟）")
        lines.append(f"  - {item.get('description', '')}")
    return "\n".join(lines)


def _movement_markdown(items: list[dict]) -> str:
    """把动作拆解列表渲染成 Markdown。"""

    if not items:
        return "- 暂无"
    lines: list[str] = []
    for item in items:
        lines.append(f"- **{item.get('name', '未命名动作')}**：{item.get('beats', '')}")
        lines.append(f"  - {item.get('teaching_tips', '')}")
    return "\n".join(lines)
