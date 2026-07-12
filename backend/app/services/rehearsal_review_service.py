from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AiTask, RehearsalReview
from app.schemas import RehearsalReviewSummaryResponse
from app.services.rehearsal_storage import remove_rehearsal_video


def rehearsal_review_summary(review: RehearsalReview) -> RehearsalReviewSummaryResponse:
    """把 M08 ORM 记录转换为列表摘要，并隐藏 MinIO 对象键。"""

    raw_model_info = review.raw_model_info or {}
    provider = raw_model_info.get("provider")
    model = raw_model_info.get("model")
    reasoning_level = raw_model_info.get("reasoning_level")
    return RehearsalReviewSummaryResponse(
        id=review.id,
        project_id=review.project_id,
        script_id=review.script_id,
        fusion_plan_id=review.fusion_plan_id,
        role_training_plan_id=review.role_training_plan_id,
        title=review.title,
        status=review.status,
        event_type=review.event_type,
        event_date=review.event_date,
        has_video_attachment=review.has_video_attachment,
        provider=provider if isinstance(provider, str) else None,
        model=model if isinstance(model, str) else None,
        reasoning_level=reasoning_level if isinstance(reasoning_level, str) else None,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def render_rehearsal_review_markdown(review: RehearsalReview) -> str | None:
    """把结构化复盘报告渲染成老师可继续编辑的 Markdown。"""

    content = review.edited_content or review.content
    if not content:
        return None

    raw_model_info = review.raw_model_info or {}
    provider = raw_model_info.get("provider", "unknown")
    model = raw_model_info.get("model", "unknown")
    generated_at = raw_model_info.get("generated_at", "unknown")
    event_label = "演出" if review.event_type == "performance" else "排练"
    attachment = review.video_original_file_name if review.has_video_attachment else "未上传"
    overview = "\n".join(
        [
            f"- 类型：{event_label}",
            f"- 日期：{review.event_date.isoformat()}",
            f"- 本次内容：{review.rehearsal_content}",
            f"- 复盘重点：{'、'.join(review.review_focus)}",
            f"- 视频附件：{attachment}（仅供人工查看，AI 未分析视频）",
        ]
    )
    next_plan = content.get("next_rehearsal_plan", {})
    template = content.get("reusable_template", {})

    return "\n\n".join(
        [
            f"# {content.get('title', review.title)}",
            "## 记录信息\n" + overview,
            "## 排练 / 演出概况\n" + str(content.get("overview", "")),
            "## 完成较好的部分\n" + _markdown_list(content.get("highlights", [])),
            "## 问题、原因与改进措施\n" + _issues_markdown(content.get("issues", [])),
            "## 分角色建议\n" + _role_suggestions_markdown(content.get("role_suggestions", [])),
            "## 唱段与节奏建议\n" + str(content.get("singing_and_rhythm_advice", "")),
            "## 舞蹈与队形建议\n" + str(content.get("dance_and_formation_advice", "")),
            "## 表演与调度建议\n" + str(content.get("performance_and_blocking_advice", "")),
            "## 下一次排练计划\n" + _next_plan_markdown(next_plan),
            "## 教学反思\n" + str(content.get("teaching_reflection", "")),
            "## 可复用复盘模板\n" + _template_markdown(template),
            "## 编导复核提醒\n" + _markdown_list(content.get("reviewer_notes", [])),
            "## 能力边界\n" + str(content.get("boundary_note", "")),
            f"---\n\n模型信息：{provider} / {model} / {generated_at}",
        ]
    )


def delete_rehearsal_review_with_related_data(db: Session, rehearsal_review_id: UUID) -> bool:
    """删除 M08 报告、关联任务和 MinIO 视频，不影响上游创编成果。"""

    review = db.get(RehearsalReview, rehearsal_review_id)
    if review is None:
        return False

    # 先删除对象存储，再提交数据库删除；MinIO 故障时保留业务记录，便于用户重试。
    if review.video_object_key:
        remove_rehearsal_video(review.video_object_key)
    db.query(AiTask).filter(AiTask.business_id == review.id).delete(synchronize_session=False)
    db.query(RehearsalReview).filter(RehearsalReview.id == review.id).delete(synchronize_session=False)
    db.commit()
    return True


def _markdown_list(items: list[str]) -> str:
    if not items:
        return "- 暂无"
    return "\n".join(f"- {item}" for item in items)


def _issues_markdown(items: list[dict]) -> str:
    if not items:
        return "- 暂无"
    lines = []
    priority_labels = {"high": "高", "medium": "中", "low": "低"}
    for item in items:
        lines.extend(
            [
                f"### {item.get('category', '问题')}（优先级：{priority_labels.get(item.get('priority'), '中')}）",
                f"- 观察：{item.get('observation', '')}",
                f"- 可能原因：{item.get('possible_cause', '')}",
                f"- 改进措施：{item.get('improvement_action', '')}",
                f"- 下次检查：{item.get('next_check', '')}",
            ]
        )
    return "\n".join(lines)


def _role_suggestions_markdown(items: list[dict]) -> str:
    if not items:
        return "- 暂无"
    lines = []
    for item in items:
        lines.extend(
            [
                f"### {item.get('role_name', '角色组')}",
                f"- 观察：{item.get('observation', '')}",
                f"- 建议：{item.get('suggestion', '')}",
                "- 下次任务：",
                _markdown_list(item.get("next_tasks", [])),
            ]
        )
    return "\n".join(lines)


def _next_plan_markdown(plan: dict) -> str:
    return "\n".join(
        [
            f"- 目标：{plan.get('goal', '')}",
            "- 重点：",
            _markdown_list(plan.get("focus_items", [])),
            "- 执行步骤：",
            _markdown_list(plan.get("action_steps", [])),
            "- 老师检查点：",
            _markdown_list(plan.get("teacher_checkpoints", [])),
        ]
    )


def _template_markdown(template: dict) -> str:
    return "\n".join(
        [
            f"- 模板名称：{template.get('template_title', '')}",
            "- 建议复盘重点：",
            _markdown_list(template.get("review_focus", [])),
            "- 观察提示：",
            _markdown_list(template.get("observation_prompts", [])),
            "- 结束检查清单：",
            _markdown_list(template.get("closing_checklist", [])),
        ]
    )
