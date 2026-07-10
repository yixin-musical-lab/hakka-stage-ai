from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AiTask, ClassInteraction
from app.schemas.class_interaction import ClassInteractionSummaryResponse, LessonInteractionPrefillResponse


def class_interaction_summary(class_interaction: ClassInteraction) -> ClassInteractionSummaryResponse:
    """把 ORM 课堂互动记录转换成列表摘要。"""

    raw_model_info = class_interaction.raw_model_info or {}
    return ClassInteractionSummaryResponse(
        id=class_interaction.id,
        source_lesson_plan_id=class_interaction.source_lesson_plan_id,
        title=class_interaction.title,
        status=class_interaction.status,
        course_theme=class_interaction.course_theme,
        teaching_phase=class_interaction.teaching_phase,
        duration_minutes=class_interaction.duration_minutes,
        provider=_optional_string(raw_model_info.get("provider")),
        model=_optional_string(raw_model_info.get("model")),
        reasoning_level=_optional_string(raw_model_info.get("reasoning_level")),
        created_at=class_interaction.created_at,
        updated_at=class_interaction.updated_at,
    )


def render_class_interaction_markdown(class_interaction: Any) -> str | None:
    """把结构化课堂互动方案渲染成老师可打印、可现场查看的 Markdown。"""

    content = class_interaction.edited_content or class_interaction.content
    if not content:
        return None

    raw_model_info = class_interaction.raw_model_info or {}
    provider = raw_model_info.get("provider", "unknown")
    model = raw_model_info.get("model", "unknown")
    generated_at = raw_model_info.get("generated_at", "unknown")
    overview = "\n".join(
        [
            f"- 课程主题：{class_interaction.course_theme}",
            f"- 年龄段：{class_interaction.age_group}",
            f"- 课堂阶段：{content.get('teaching_phase', class_interaction.teaching_phase)}",
            f"- 互动目标：{content.get('interaction_goal', class_interaction.interaction_goal)}",
            f"- 可用时长：{content.get('duration_minutes', class_interaction.duration_minutes)} 分钟",
            f"- 学生人数：{class_interaction.student_count} 人",
            f"- 课堂风格：{class_interaction.class_style}",
        ]
    )

    return "\n\n".join(
        [
            f"# {content.get('title', class_interaction.title)}",
            "## 基础信息\n" + overview,
            "## 场地、材料与限制\n" + str(content.get("space_materials", class_interaction.space_materials)),
            "## 小游戏与互动规则\n" + _markdown_list(content.get("game_rules", [])),
            "## 老师逐步执行脚本\n" + _teacher_script_markdown(content.get("teacher_script", [])),
            "## 老师口令\n" + _markdown_list(content.get("command_phrases", [])),
            "## 学生动作与回应\n" + _markdown_list(content.get("student_actions", [])),
            "## 分组与课堂组织\n" + str(content.get("grouping_method", "")),
            "## 鼓励用语\n" + _markdown_list(content.get("encouragement_phrases", [])),
            "## 安全提醒\n" + _markdown_list(content.get("safety_notes", [])),
            "## 变式与备用方案\n" + _markdown_list(content.get("variations", [])),
            "## 老师开始前确认\n" + _markdown_list(content.get("teacher_check_notes", [])),
            f"---\n\n模型信息：{provider} / {model} / {generated_at}",
        ]
    )


def build_lesson_interaction_prefill(course: Any, lesson_plan: Any) -> LessonInteractionPrefillResponse:
    """从教案和课程中提取 T05 表单预填信息。

    这里只生成文本快照，后续课堂互动方案可独立编辑和删除，不会反向修改原教案。
    """

    lesson_content = lesson_plan.edited_content or lesson_plan.content or {}
    context_sections = [
        f"课程教学目标：{course.teaching_goal}",
        _context_list("教案教学目标", lesson_content.get("teaching_goals", [])),
        _context_list("本课重点", lesson_content.get("key_points", [])),
        _context_list("老师备注", lesson_content.get("teacher_notes", [])),
    ]
    lesson_context = "\n".join(section for section in context_sections if section)

    return LessonInteractionPrefillResponse(
        source_lesson_plan_id=lesson_plan.id,
        course_theme=course.theme,
        age_group=course.age_group,
        student_count=course.student_count,
        class_style=course.course_style,
        space_materials=course.notes or "无额外场地或材料限制",
        lesson_context=lesson_context,
    )


def delete_class_interaction_with_task(db: Session, class_interaction_id: UUID) -> bool:
    """删除课堂互动方案和关联 AI 任务，不删除或修改来源教案。"""

    class_interaction = db.get(ClassInteraction, class_interaction_id)
    if class_interaction is None:
        return False

    db.query(AiTask).filter(AiTask.business_id == class_interaction.id).delete(synchronize_session=False)
    db.query(ClassInteraction).filter(ClassInteraction.id == class_interaction_id).delete(synchronize_session=False)
    db.commit()
    return True


def _teacher_script_markdown(steps: list[dict]) -> str:
    """把逐步执行脚本展开为便于打印查看的编号段落。"""

    blocks: list[str] = []
    for index, step in enumerate(steps, start=1):
        step_no = step.get("step_no", index)
        name = step.get("name", f"步骤 {step_no}")
        blocks.append(
            "\n".join(
                [
                    f"### {step_no}. {name}（{step.get('duration_hint', '')}）",
                    f"- 老师动作：{step.get('teacher_action', '')}",
                    f"- 老师口令：{step.get('teacher_cue', '')}",
                    f"- 学生动作：{step.get('student_action', '')}",
                ]
            )
        )
    return "\n\n".join(blocks) if blocks else "- 暂无"


def _markdown_list(items: list[str]) -> str:
    """把字符串列表转换为 Markdown 无序列表。"""

    return "\n".join(f"- {item}" for item in items) if items else "- 暂无"


def _context_list(label: str, items: list[str]) -> str:
    """把教案数组字段压缩为适合发送给模型的单行上下文。"""

    cleaned = [str(item).strip() for item in items if str(item).strip()]
    return f"{label}：{'；'.join(cleaned)}" if cleaned else ""


def _optional_string(value: object) -> str | None:
    """仅在模型信息字段确实为字符串时返回，避免异常 JSON 污染响应。"""

    return value if isinstance(value, str) else None
