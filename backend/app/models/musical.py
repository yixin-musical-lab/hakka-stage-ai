import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _uuid() -> uuid.UUID:
    """生成 PostgreSQL UUID 主键。"""

    return uuid.uuid4()


def _now() -> datetime:
    """统一生成 UTC-naive 时间，便于本地演示和数据库排序。"""

    return datetime.utcnow()


class MusicalProject(Base):
    """歌舞剧项目基础信息。

    第一版不做复杂项目管理，只保存生成剧本和训练计划所需的核心条件。
    """

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
    """M01 剧本与剧情结构生成结果。

    content 保存 AI 初稿，edited_content 保存老师或编导确认后的编辑稿。
    """

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
    """M03 唱段适配与歌词改写建议。

    第一版只保存文本层面的唱段结构、演唱分配和歌词改写建议，不做音频自动分析。
    """

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
    """M04 歌舞融合结构设计结果。

    第一版只保存文本层面的唱、跳、队形和排练建议。引用 M03 时保留可空外键，
    同时由 AiTask 保存生成快照，避免来源内容后续修改或删除后影响已确认结果。
    """

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
