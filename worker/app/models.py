import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
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
