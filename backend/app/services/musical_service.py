from uuid import UUID

from sqlalchemy.orm import Session

from app.models import (
    AiTask,
    MusicalFusionPlan,
    MusicalProject,
    MusicalScript,
    RehearsalReview,
    RoleTrainingPlan,
    SongAdaptation,
)
from app.schemas import (
    MusicalFusionPlanSummaryResponse,
    MusicalScriptGenerateRequest,
    MusicalScriptSummaryResponse,
    RoleTrainingPlanSummaryResponse,
    SongAdaptationSummaryResponse,
)
from app.services.rehearsal_storage import remove_rehearsal_video


def build_project_title(request: MusicalScriptGenerateRequest) -> str:
    """根据剧目生成表单构造列表标题。"""

    return f"{request.theme} · {request.duration_minutes}分钟歌舞剧"


def model_info(
    record: MusicalScript | MusicalFusionPlan | RoleTrainingPlan | SongAdaptation,
) -> tuple[str | None, str | None]:
    """从模型信息里提取供应商和模型名。"""

    raw_model_info = record.raw_model_info or {}
    provider = raw_model_info.get("provider")
    model = raw_model_info.get("model")
    return (
        provider if isinstance(provider, str) else None,
        model if isinstance(model, str) else None,
    )


def reasoning_level(record: MusicalScript | MusicalFusionPlan | RoleTrainingPlan | SongAdaptation) -> str | None:
    """从模型信息里提取本次生成的推理强度。"""

    raw_model_info = record.raw_model_info or {}
    value = raw_model_info.get("reasoning_level")
    return value if isinstance(value, str) else None


def musical_script_summary(musical_script: MusicalScript) -> MusicalScriptSummaryResponse:
    """把 ORM 剧本记录转成列表摘要。"""

    provider, model = model_info(musical_script)
    return MusicalScriptSummaryResponse(
        id=musical_script.id,
        project_id=musical_script.project_id,
        title=musical_script.title,
        status=musical_script.status,
        provider=provider,
        model=model,
        reasoning_level=reasoning_level(musical_script),
        created_at=musical_script.created_at,
        updated_at=musical_script.updated_at,
    )


def role_training_summary(role_training_plan: RoleTrainingPlan) -> RoleTrainingPlanSummaryResponse:
    """把 ORM 分角色训练计划转成列表摘要。"""

    provider, model = model_info(role_training_plan)
    return RoleTrainingPlanSummaryResponse(
        id=role_training_plan.id,
        project_id=role_training_plan.project_id,
        script_id=role_training_plan.script_id,
        title=role_training_plan.title,
        status=role_training_plan.status,
        provider=provider,
        model=model,
        reasoning_level=reasoning_level(role_training_plan),
        created_at=role_training_plan.created_at,
        updated_at=role_training_plan.updated_at,
    )


def song_adaptation_summary(song_adaptation: SongAdaptation) -> SongAdaptationSummaryResponse:
    """把 ORM 唱段适配记录转成列表摘要。"""

    provider, model = model_info(song_adaptation)
    return SongAdaptationSummaryResponse(
        id=song_adaptation.id,
        project_id=song_adaptation.project_id,
        script_id=song_adaptation.script_id,
        title=song_adaptation.title,
        status=song_adaptation.status,
        related_scene=song_adaptation.related_scene,
        source_song=song_adaptation.source_song,
        provider=provider,
        model=model,
        reasoning_level=reasoning_level(song_adaptation),
        created_at=song_adaptation.created_at,
        updated_at=song_adaptation.updated_at,
    )


def musical_fusion_summary(musical_fusion_plan: MusicalFusionPlan) -> MusicalFusionPlanSummaryResponse:
    """把 ORM 歌舞融合方案转换成列表摘要。"""

    provider, model = model_info(musical_fusion_plan)
    return MusicalFusionPlanSummaryResponse(
        id=musical_fusion_plan.id,
        project_id=musical_fusion_plan.project_id,
        script_id=musical_fusion_plan.script_id,
        song_adaptation_id=musical_fusion_plan.song_adaptation_id,
        title=musical_fusion_plan.title,
        status=musical_fusion_plan.status,
        source_mode=musical_fusion_plan.source_mode,
        music_title=musical_fusion_plan.music_title,
        related_scene=musical_fusion_plan.related_scene,
        provider=provider,
        model=model,
        reasoning_level=reasoning_level(musical_fusion_plan),
        created_at=musical_fusion_plan.created_at,
        updated_at=musical_fusion_plan.updated_at,
    )


def render_musical_script_markdown(musical_script: MusicalScript) -> str | None:
    """把结构化剧本渲染成 Markdown 文本。"""

    content = musical_script.edited_content or musical_script.content
    if not content:
        return None

    raw_model_info = musical_script.raw_model_info or {}
    provider = raw_model_info.get("provider", "unknown")
    model = raw_model_info.get("model", "unknown")
    generated_at = raw_model_info.get("generated_at", "unknown")

    return "\n\n".join(
        [
            f"# {content.get('title', musical_script.title)}",
            "## 剧目简介\n" + str(content.get("synopsis", "")),
            "## 分幕剧情\n" + _script_acts_markdown(content.get("acts", [])),
            "## 人物设定\n" + _characters_markdown(content.get("characters", [])),
            "## 表演留白段落\n" + _performance_slots_markdown(content.get("performance_slots", [])),
            "## 编导确认提醒\n" + _markdown_list(content.get("director_notes", [])),
            f"---\n\n模型信息：{provider} / {model} / {generated_at}",
        ]
    )


def render_song_adaptation_markdown(song_adaptation: SongAdaptation) -> str | None:
    """把结构化唱段适配建议渲染成 Markdown 文本。"""

    content = song_adaptation.edited_content or song_adaptation.content
    if not content:
        return None

    raw_model_info = song_adaptation.raw_model_info or {}
    provider = raw_model_info.get("provider", "unknown")
    model = raw_model_info.get("model", "unknown")
    generated_at = raw_model_info.get("generated_at", "unknown")

    return "\n\n".join(
        [
            f"# {content.get('title', song_adaptation.title)}",
            "## 基础信息\n" + _song_adaptation_overview_markdown(song_adaptation, content),
            "## 唱段结构与歌词建议\n" + _song_sections_markdown(content.get("sections", [])),
            "## 间奏舞蹈与留白\n" + _dance_interludes_markdown(content.get("dance_interludes", [])),
            "## 复核提醒\n" + _markdown_list(content.get("review_notes", [])),
            f"---\n\n模型信息：{provider} / {model} / {generated_at}",
        ]
    )


def render_musical_fusion_markdown(musical_fusion_plan: MusicalFusionPlan) -> str | None:
    """把结构化歌舞融合方案渲染成编导可复核的 Markdown。"""

    content = musical_fusion_plan.edited_content or musical_fusion_plan.content
    if not content:
        return None

    raw_model_info = musical_fusion_plan.raw_model_info or {}
    provider = raw_model_info.get("provider", "unknown")
    model = raw_model_info.get("model", "unknown")
    generated_at = raw_model_info.get("generated_at", "unknown")
    overview = "\n".join(
        [
            f"- 关联剧情：{content.get('related_scene', musical_fusion_plan.related_scene)}",
            f"- 音乐来源：{musical_fusion_plan.music_title or '手工音乐段落'}",
            f"- 演员人数：{content.get('actor_count', musical_fusion_plan.actor_count)}",
            f"- 舞台空间：{content.get('stage_space', musical_fusion_plan.stage_space)}",
            f"- 融合目标：{content.get('fusion_goal', musical_fusion_plan.fusion_goal)}",
        ]
    )

    return "\n\n".join(
        [
            f"# {content.get('title', musical_fusion_plan.title)}",
            "## 基础信息\n" + overview,
            "## 整体设计\n" + str(content.get("overall_design", "")),
            "## 歌舞融合结构表\n" + _musical_fusion_segments_markdown(content.get("segments", [])),
            "## 高潮设计\n" + str(content.get("highlight_summary", "")),
            "## 排练建议\n" + _markdown_list(content.get("rehearsal_notes", [])),
            "## 编导复核提醒\n" + _markdown_list(content.get("director_review_notes", [])),
            f"---\n\n模型信息：{provider} / {model} / {generated_at}",
        ]
    )


def render_role_training_markdown(role_training_plan: RoleTrainingPlan) -> str | None:
    """把结构化分角色训练计划渲染成 Markdown 文本。"""

    content = role_training_plan.edited_content or role_training_plan.content
    if not content:
        return None

    raw_model_info = role_training_plan.raw_model_info or {}
    provider = raw_model_info.get("provider", "unknown")
    model = raw_model_info.get("model", "unknown")
    generated_at = raw_model_info.get("generated_at", "unknown")

    return "\n\n".join(
        [
            f"# {content.get('title', role_training_plan.title)}",
            "## 排练概况\n" + str(content.get("project_overview", "")),
            "## 分角色任务\n" + _role_tasks_markdown(content.get("role_tasks", [])),
            "## 每日排练安排\n" + _daily_plan_markdown(content.get("daily_plan", [])),
            "## 老师检查点\n" + _markdown_list(content.get("teacher_checkpoints", [])),
            f"---\n\n模型信息：{provider} / {model} / {generated_at}",
        ]
    )


def delete_musical_script_with_related_data(db: Session, musical_script_id: UUID) -> bool:
    """删除剧本及其唱段、歌舞融合、训练计划、复盘报告和 AI 任务。"""

    musical_script = db.get(MusicalScript, musical_script_id)
    if musical_script is None:
        return False

    project_id = musical_script.project_id
    db.query(AiTask).filter(AiTask.business_id == musical_script.id).delete(synchronize_session=False)
    related_review_rows = db.query(RehearsalReview.id, RehearsalReview.video_object_key).filter(
        RehearsalReview.script_id == musical_script.id
    ).all()
    for _, object_key in related_review_rows:
        if object_key:
            remove_rehearsal_video(object_key)
    related_review_ids = [row[0] for row in related_review_rows]
    if related_review_ids:
        db.query(AiTask).filter(AiTask.business_id.in_(related_review_ids)).delete(synchronize_session=False)
        db.query(RehearsalReview).filter(RehearsalReview.id.in_(related_review_ids)).delete(synchronize_session=False)
    related_song_adaptation_ids = [
        row[0] for row in db.query(SongAdaptation.id).filter(SongAdaptation.script_id == musical_script.id).all()
    ]
    if related_song_adaptation_ids:
        db.query(AiTask).filter(AiTask.business_id.in_(related_song_adaptation_ids)).delete(synchronize_session=False)
    related_fusion_ids = [
        row[0] for row in db.query(MusicalFusionPlan.id).filter(MusicalFusionPlan.script_id == musical_script.id).all()
    ]
    if related_fusion_ids:
        db.query(AiTask).filter(AiTask.business_id.in_(related_fusion_ids)).delete(synchronize_session=False)
        db.query(MusicalFusionPlan).filter(MusicalFusionPlan.id.in_(related_fusion_ids)).delete(synchronize_session=False)
    if related_song_adaptation_ids:
        db.query(SongAdaptation).filter(SongAdaptation.id.in_(related_song_adaptation_ids)).delete(synchronize_session=False)
    related_training_ids = [
        row[0] for row in db.query(RoleTrainingPlan.id).filter(RoleTrainingPlan.script_id == musical_script.id).all()
    ]
    if related_training_ids:
        db.query(AiTask).filter(AiTask.business_id.in_(related_training_ids)).delete(synchronize_session=False)
        db.query(RoleTrainingPlan).filter(RoleTrainingPlan.id.in_(related_training_ids)).delete(synchronize_session=False)
    db.query(MusicalScript).filter(MusicalScript.id == musical_script_id).delete(synchronize_session=False)
    db.flush()
    _delete_project_if_unused(db, project_id)
    db.commit()
    return True


def delete_song_adaptation_with_related_data(db: Session, song_adaptation_id: UUID) -> bool:
    """删除唱段适配和关联 AI 任务，不删除原始剧本。"""

    song_adaptation = db.get(SongAdaptation, song_adaptation_id)
    if song_adaptation is None:
        return False

    project_id = song_adaptation.project_id
    db.query(AiTask).filter(AiTask.business_id == song_adaptation.id).delete(synchronize_session=False)
    # M04 已保存完整任务快照，删除 M03 时只解除来源关联，不删除已经确认的歌舞融合方案。
    db.query(MusicalFusionPlan).filter(MusicalFusionPlan.song_adaptation_id == song_adaptation.id).update(
        {MusicalFusionPlan.song_adaptation_id: None},
        synchronize_session=False,
    )
    db.query(SongAdaptation).filter(SongAdaptation.id == song_adaptation_id).delete(synchronize_session=False)
    db.flush()
    _delete_project_if_unused(db, project_id)
    db.commit()
    return True


def delete_musical_fusion_with_related_data(db: Session, musical_fusion_plan_id: UUID) -> bool:
    """删除歌舞融合方案及关联 AI 任务，不删除剧本或唱段适配。"""

    musical_fusion_plan = db.get(MusicalFusionPlan, musical_fusion_plan_id)
    if musical_fusion_plan is None:
        return False

    project_id = musical_fusion_plan.project_id
    db.query(AiTask).filter(AiTask.business_id == musical_fusion_plan.id).delete(synchronize_session=False)
    # 复盘任务已保留生成时快照，删除 M04 时只解除来源关联。
    db.query(RehearsalReview).filter(RehearsalReview.fusion_plan_id == musical_fusion_plan.id).update(
        {RehearsalReview.fusion_plan_id: None},
        synchronize_session=False,
    )
    db.query(MusicalFusionPlan).filter(MusicalFusionPlan.id == musical_fusion_plan_id).delete(synchronize_session=False)
    db.flush()
    _delete_project_if_unused(db, project_id)
    db.commit()
    return True


def delete_role_training_with_related_data(db: Session, role_training_plan_id: UUID) -> bool:
    """删除分角色训练计划和关联 AI 任务，不删除原始剧本。"""

    role_training_plan = db.get(RoleTrainingPlan, role_training_plan_id)
    if role_training_plan is None:
        return False

    project_id = role_training_plan.project_id
    db.query(AiTask).filter(AiTask.business_id == role_training_plan.id).delete(synchronize_session=False)
    # 复盘报告引用 M05 仅用于追踪来源，删除训练计划后仍保留复盘正文和快照。
    db.query(RehearsalReview).filter(RehearsalReview.role_training_plan_id == role_training_plan.id).update(
        {RehearsalReview.role_training_plan_id: None},
        synchronize_session=False,
    )
    db.query(RoleTrainingPlan).filter(RoleTrainingPlan.id == role_training_plan_id).delete(synchronize_session=False)
    db.flush()
    _delete_project_if_unused(db, project_id)
    db.commit()
    return True


def _delete_project_if_unused(db: Session, project_id: UUID) -> None:
    """当剧目没有剧本、唱段、融合、训练或复盘记录时清理剧目草稿。"""

    script_count = db.query(MusicalScript).filter(MusicalScript.project_id == project_id).count()
    song_adaptation_count = db.query(SongAdaptation).filter(SongAdaptation.project_id == project_id).count()
    fusion_count = db.query(MusicalFusionPlan).filter(MusicalFusionPlan.project_id == project_id).count()
    training_count = db.query(RoleTrainingPlan).filter(RoleTrainingPlan.project_id == project_id).count()
    review_count = db.query(RehearsalReview).filter(RehearsalReview.project_id == project_id).count()
    if (
        script_count == 0
        and song_adaptation_count == 0
        and fusion_count == 0
        and training_count == 0
        and review_count == 0
    ):
        project = db.get(MusicalProject, project_id)
        if project is not None:
            db.query(MusicalProject).filter(MusicalProject.id == project_id).delete(synchronize_session=False)


def _markdown_list(items: list[str]) -> str:
    """把字符串列表渲染成 Markdown 列表。"""

    if not items:
        return "- 暂无"
    return "\n".join(f"- {item}" for item in items)


def _script_acts_markdown(items: list[dict]) -> str:
    """渲染分幕剧情、旁白和台词。"""

    if not items:
        return "- 暂无"
    lines: list[str] = []
    for item in items:
        lines.append(f"### {item.get('name', '未命名段落')}（{item.get('duration_minutes', 0)} 分钟）")
        lines.append(f"- 剧情：{item.get('story_outline', '')}")
        lines.append(f"- 情绪：{item.get('emotion', '')}")
        narrator_text = item.get("narrator_text", "")
        if narrator_text:
            lines.append(f"- 旁白：{narrator_text}")
        dialogues = item.get("dialogues", [])
        if dialogues:
            lines.append("- 台词：")
            for dialogue in dialogues:
                lines.append(
                    f"  - **{dialogue.get('role_name', '角色')}**：{dialogue.get('line', '')}"
                    f"（{dialogue.get('stage_direction', '')}）"
                )
    return "\n".join(lines)


def _characters_markdown(items: list[dict]) -> str:
    """渲染人物设定。"""

    if not items:
        return "- 暂无"
    lines: list[str] = []
    for item in items:
        lines.append(f"- **{item.get('name', '未命名角色')}**（{item.get('role_type', '')}）")
        lines.append(f"  - 性格：{item.get('personality', '')}")
        lines.append(f"  - 弧光：{item.get('character_arc', '')}")
        lines.append(f"  - 表演提示：{item.get('performance_tips', '')}")
        lines.append(f"  - 关键台词：{'；'.join(item.get('key_lines', []))}")
    return "\n".join(lines)


def _performance_slots_markdown(items: list[dict]) -> str:
    """渲染舞蹈、独唱、群舞留白段落。"""

    if not items:
        return "- 暂无"
    lines: list[str] = []
    for item in items:
        lines.append(f"- **{item.get('act_name', '未命名段落')} / {item.get('slot_type', '')}**")
        lines.append(f"  - {item.get('description', '')}")
        lines.append(f"  - 建议时长：{item.get('suggested_duration', '')}")
        lines.append(f"  - 提醒：{item.get('notes', '')}")
    return "\n".join(lines)


def _song_adaptation_overview_markdown(song_adaptation: SongAdaptation, content: dict) -> str:
    """渲染唱段适配基础信息。"""

    return "\n".join(
        [
            f"- 原曲 / 音乐来源：{content.get('source_song') or song_adaptation.source_song or '未填写'}",
            f"- 关联剧情段落：{content.get('related_scene') or song_adaptation.related_scene}",
            f"- 改写目标：{content.get('adaptation_goal') or song_adaptation.adaptation_goal}",
            f"- 改写强度：{song_adaptation.rewrite_intensity}",
            f"- 演唱角色：{song_adaptation.singing_roles or '未单独填写'}",
        ]
    )


def _song_sections_markdown(items: list[dict]) -> str:
    """渲染每个唱段的歌词、演唱方式和舞蹈留白。"""

    if not items:
        return "- 暂无"
    lines: list[str] = []
    for item in items:
        lines.append(f"### {item.get('section_no', '未编号')} / {item.get('music_position', '未标注位置')}")
        lines.append(f"- 原歌词：{item.get('original_lyrics', '')}")
        lines.append(f"- 改写建议：{item.get('adapted_lyrics', '')}")
        lines.append(f"- 演唱方式：{item.get('singing_mode', '')}")
        lines.append(f"- 建议角色：{'、'.join(item.get('suggested_roles', [])) or '未指定'}")
        lines.append(f"- 情绪：{item.get('emotion', '')}")
        lines.append(f"- 舞蹈留白：{item.get('dance_opportunity', '')}")
        lines.append(f"- 衔接说明：{item.get('transition_note', '')}")
    return "\n".join(lines)


def _dance_interludes_markdown(items: list[dict]) -> str:
    """渲染间奏、过门或歌词留白处的舞蹈建议。"""

    if not items:
        return "- 暂无"
    return "\n".join(
        f"- **{item.get('music_position', '未标注位置')}**：{item.get('suggestion', '')}" for item in items
    )


def _musical_fusion_segments_markdown(items: list[dict]) -> str:
    """把歌舞融合段落渲染成紧凑的 Markdown 表格。"""

    if not items:
        return "- 暂无"
    lines = [
        "| 段落 | 剧情 / 音乐 | 演唱 | 舞蹈 / 队形 | 衔接与排练 | 重点 |",
        "|---|---|---|---|---|---|",
    ]
    for item in items:
        story_music = f"{item.get('story_content', '')}<br>{item.get('music_position', '')}"
        singing = f"{item.get('singing_mode', '')}<br>{'、'.join(item.get('singing_roles', []))}"
        dance = f"{item.get('dance_form', '')}<br>{item.get('formation_suggestion', '')}"
        rehearsal = (
            f"{item.get('song_dance_relationship', '')}<br>{item.get('transition_note', '')}<br>"
            f"排练：{item.get('rehearsal_tip', '')}<br>安全：{item.get('safety_note', '')}"
        )
        highlight = "高潮" if item.get("is_highlight") else "普通段落"
        cells = [item.get("segment_no", "未编号"), story_music, singing, dance, rehearsal, highlight]
        lines.append("| " + " | ".join(_escape_markdown_cell(str(cell)) for cell in cells) + " |")
    return "\n".join(lines)


def _escape_markdown_cell(value: str) -> str:
    """转义 Markdown 表格分隔符并把换行转换成 HTML 换行。"""

    return value.replace("|", "\\|").replace("\r\n", "<br>").replace("\n", "<br>")


def _role_tasks_markdown(items: list[dict]) -> str:
    """渲染角色维度训练任务。"""

    if not items:
        return "- 暂无"
    lines: list[str] = []
    for item in items:
        lines.append(f"### {item.get('role_name', '未命名角色')}（{item.get('role_type', '')}）")
        lines.append(f"- 台词训练：{item.get('line_focus', '')}")
        lines.append(f"- 演唱训练：{item.get('singing_focus', '')}")
        lines.append(f"- 舞蹈训练：{item.get('dance_focus', '')}")
        lines.append(f"- 走位提醒：{item.get('blocking_tips', '')}")
        lines.append("- 每日任务：" + ("；".join(item.get("daily_tasks", [])) or "暂无"))
        lines.append("- 老师检查点：" + ("；".join(item.get("teacher_checkpoints", [])) or "暂无"))
    return "\n".join(lines)


def _daily_plan_markdown(items: list[dict]) -> str:
    """渲染每日训练安排。"""

    if not items:
        return "- 暂无"
    lines: list[str] = []
    for item in items:
        lines.append(f"- **{item.get('day', '未命名日期')}**：{item.get('focus', '')}")
        lines.append(f"  - 任务：{'；'.join(item.get('tasks', []))}")
        lines.append(f"  - 预期结果：{item.get('expected_result', '')}")
    return "\n".join(lines)
