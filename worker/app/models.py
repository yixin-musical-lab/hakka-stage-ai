import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> uuid.UUID:
    """生成 PostgreSQL UUID 主键。"""

    return uuid.uuid4()


def _now() -> datetime:
    """生成 UTC-naive 时间。"""

    return datetime.utcnow()


class Course(Base):
    """课程基础信息。"""

    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(200))
    dance_style: Mapped[str] = mapped_column(String(120))
    theme: Mapped[str] = mapped_column(String(200))
    age_group: Mapped[str] = mapped_column(String(80))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    student_count: Mapped[int] = mapped_column(Integer)
    learning_level: Mapped[str] = mapped_column(String(120))
    course_style: Mapped[str] = mapped_column(String(120))
    teaching_goal: Mapped[str] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(80), default="demo-teacher")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class LessonPlan(Base):
    """教案生成结果。"""

    __tablename__ = "lesson_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"))
    title: Mapped[str] = mapped_column(String(200), default="待生成教案")
    status: Mapped[str] = mapped_column(String(40), default="draft")
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    edited_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_model_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class LessonPlanVariant(Base):
    """T02 教案变体关系表的 Worker 侧镜像。

    Worker 主要通过任务快照生成正文，但仍注册此模型，保证 Worker 单独启动时
    ``create_all`` 能看到完整的新表结构。
    """

    __tablename__ = "lesson_plan_variants"

    lesson_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lesson_plans.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source_lesson_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lesson_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    variant_type: Mapped[str] = mapped_column(String(40))
    adjustment_direction: Mapped[str] = mapped_column(Text, default="")
    source_title_snapshot: Mapped[str] = mapped_column(String(200))
    source_content_snapshot: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class MusicalProject(Base):
    """歌舞剧项目基础信息。"""

    __tablename__ = "musical_projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(200))
    theme: Mapped[str] = mapped_column(String(200))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    actor_count: Mapped[int] = mapped_column(Integer)
    age_group: Mapped[str] = mapped_column(String(80))
    style_requirements: Mapped[str] = mapped_column(Text)
    required_elements: Mapped[str] = mapped_column(Text, default="")
    forbidden_content: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(80), default="demo-teacher")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class MusicalScript(Base):
    """M01 剧本与剧情结构生成结果。"""

    __tablename__ = "musical_scripts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("musical_projects.id"))
    title: Mapped[str] = mapped_column(String(200), default="待生成剧本")
    status: Mapped[str] = mapped_column(String(40), default="draft")
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    edited_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_model_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class SongAdaptation(Base):
    """M03 唱段适配与歌词改写建议。"""

    __tablename__ = "song_adaptations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("musical_projects.id"))
    script_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("musical_scripts.id"))
    title: Mapped[str] = mapped_column(String(200), default="待生成唱段适配建议")
    status: Mapped[str] = mapped_column(String(40), default="draft")
    source_song: Mapped[str] = mapped_column(String(200), default="")
    related_scene: Mapped[str] = mapped_column(String(240), default="")
    lyrics_text: Mapped[str] = mapped_column(Text)
    music_structure: Mapped[str] = mapped_column(Text)
    adaptation_goal: Mapped[str] = mapped_column(Text)
    singing_roles: Mapped[str] = mapped_column(Text, default="")
    rewrite_intensity: Mapped[str] = mapped_column(String(80), default="light_rewrite")
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    edited_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_model_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class MusicalFusionPlan(Base):
    """M04 歌舞融合结构设计结果，字段必须与 Backend ORM 保持一致。"""

    __tablename__ = "musical_fusion_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("musical_projects.id"))
    script_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("musical_scripts.id"))
    song_adaptation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("song_adaptations.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), default="待生成歌舞融合建议")
    status: Mapped[str] = mapped_column(String(40), default="draft")
    source_mode: Mapped[str] = mapped_column(String(40), default="manual")
    music_title: Mapped[str] = mapped_column(String(200), default="")
    related_scene: Mapped[str] = mapped_column(String(240))
    manual_music_structure: Mapped[str] = mapped_column(Text, default="")
    manual_lyrics_summary: Mapped[str] = mapped_column(Text, default="")
    actor_count: Mapped[int] = mapped_column(Integer)
    stage_space: Mapped[str] = mapped_column(Text)
    fusion_goal: Mapped[str] = mapped_column(Text)
    additional_constraints: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    edited_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_model_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class RoleTrainingPlan(Base):
    """M05 分角色训练计划生成结果。"""

    __tablename__ = "role_training_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("musical_projects.id"))
    script_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("musical_scripts.id"))
    title: Mapped[str] = mapped_column(String(200), default="待生成分角色训练计划")
    status: Mapped[str] = mapped_column(String(40), default="draft")
    rehearsal_days: Mapped[int] = mapped_column(Integer)
    session_minutes: Mapped[int] = mapped_column(Integer)
    training_focus: Mapped[str] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    edited_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_model_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class RehearsalReview(Base):
    """M08 排练 / 演出复盘报告，字段必须与 Backend ORM 保持一致。"""

    __tablename__ = "rehearsal_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("musical_projects.id"))
    script_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("musical_scripts.id"))
    fusion_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("musical_fusion_plans.id", ondelete="SET NULL"), nullable=True
    )
    role_training_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("role_training_plans.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), default="待生成排练复盘报告")
    status: Mapped[str] = mapped_column(String(40), default="draft")
    event_type: Mapped[str] = mapped_column(String(40), default="rehearsal")
    event_date: Mapped[date] = mapped_column(Date)
    rehearsal_content: Mapped[str] = mapped_column(Text)
    observation_notes: Mapped[str] = mapped_column(Text)
    strengths: Mapped[str] = mapped_column(Text, default="")
    issues: Mapped[str] = mapped_column(Text, default="")
    review_focus: Mapped[list] = mapped_column(JSONB, default=list)
    next_goal: Mapped[str] = mapped_column(Text)
    video_object_key: Mapped[str] = mapped_column(String(500), default="")
    video_original_file_name: Mapped[str] = mapped_column(String(240), default="")
    video_content_type: Mapped[str] = mapped_column(String(120), default="")
    video_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    video_notes: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    edited_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_model_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class ClassInteraction(Base):
    """T05 老师可现场执行的课堂互动方案。"""

    __tablename__ = "class_interactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    source_lesson_plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(String(200), default="待生成课堂互动方案")
    status: Mapped[str] = mapped_column(String(40), default="draft")
    course_theme: Mapped[str] = mapped_column(String(200))
    age_group: Mapped[str] = mapped_column(String(80))
    teaching_phase: Mapped[str] = mapped_column(String(40))
    interaction_goal: Mapped[str] = mapped_column(Text)
    class_style: Mapped[str] = mapped_column(String(120))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    student_count: Mapped[int] = mapped_column(Integer)
    space_materials: Mapped[str] = mapped_column(Text, default="")
    lesson_context: Mapped[str] = mapped_column(Text, default="")
    lesson_context_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    edited_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_model_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class AiTask(Base):
    """AI 异步任务状态。"""

    __tablename__ = "ai_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    task_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="PENDING")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    input_snapshot: Mapped[dict] = mapped_column(JSONB)
    result_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str] = mapped_column(String(80), default="demo-teacher")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class WorkflowTemplate(Base):
    """Worker 侧 RunningHub 工作流模板镜像。"""

    __tablename__ = "workflow_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(40), default="runninghub")
    external_workflow_id: Mapped[str] = mapped_column(String(120), default="")
    media_type: Mapped[str] = mapped_column(String(40), default="audio")
    status: Mapped[str] = mapped_column(String(40), default="draft")
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class WorkflowTemplateVersion(Base):
    """Worker 侧工作流版本镜像，只读取已发布参数。"""

    __tablename__ = "workflow_template_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_templates.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    source_filename: Mapped[str] = mapped_column(String(240))
    workflow_hash: Mapped[str] = mapped_column(String(64), index=True)
    workflow_json: Mapped[dict] = mapped_column(JSONB)
    analysis: Mapped[dict] = mapped_column(JSONB, default=dict)
    parameter_config: Mapped[list] = mapped_column(JSONB, default=list)
    output_config: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(40), default="draft")
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MediaWorkbenchConfig(Base):
    """Worker 侧工作台配置镜像；运行参数已固化在媒体任务中，Worker 通常只需注册表结构。"""

    __tablename__ = "media_workbench_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(40), index=True)
    capability: Mapped[str] = mapped_column(String(40))
    workflow_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_template_versions.id", ondelete="SET NULL"), nullable=True
    )
    model: Mapped[str] = mapped_column(String(120), default="")
    provider_api_mode: Mapped[str] = mapped_column(String(40), default="")
    default_parameters: Mapped[dict] = mapped_column(JSONB, default=dict)
    input_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class MediaGeneration(Base):
    """Worker 侧统一媒体任务镜像。"""

    __tablename__ = "media_generations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(200), default="未命名媒体任务")
    workbench_slug: Mapped[str] = mapped_column(String(80), default="", index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    capability: Mapped[str] = mapped_column(String(40), index=True)
    model: Mapped[str] = mapped_column(String(120), default="")
    workflow_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_template_versions.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="PENDING", index=True)
    prompt: Mapped[str] = mapped_column(Text, default="")
    request_parameters: Mapped[dict] = mapped_column(JSONB, default=dict)
    input_bindings: Mapped[dict] = mapped_column(JSONB, default=dict)
    client_request_id: Mapped[str] = mapped_column(String(100), default="", index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ProviderTaskRun(Base):
    """Worker 侧供应商运行记录镜像。"""

    __tablename__ = "provider_task_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("media_generations.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    external_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider_status: Mapped[str] = mapped_column(String(80), default="CREATED", index=True)
    request_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    response_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    poll_count: Mapped[int] = mapped_column(Integer, default=0)
    next_poll_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MediaAsset(Base):
    """Worker 侧媒体资产镜像。"""

    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    generation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("media_generations.id", ondelete="CASCADE"), nullable=True, index=True)
    provider_task_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("provider_task_runs.id", ondelete="SET NULL"), nullable=True)
    role: Mapped[str] = mapped_column(String(40), default="input")
    media_type: Mapped[str] = mapped_column(String(40), default="other")
    storage_mode: Mapped[str] = mapped_column(String(40), default="managed")
    bucket: Mapped[str] = mapped_column(String(120), default="")
    object_key: Mapped[str] = mapped_column(String(600), default="")
    external_url: Mapped[str] = mapped_column(Text, default="")
    original_file_name: Mapped[str] = mapped_column(String(240), default="")
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider: Mapped[str] = mapped_column(String(40), default="")
    provider_output_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    asset_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(40), default="AVAILABLE")
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
