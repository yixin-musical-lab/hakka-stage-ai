import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _uuid() -> uuid.UUID:
    """生成 PostgreSQL UUID 主键。"""

    return uuid.uuid4()


def _now() -> datetime:
    """统一生成 UTC-naive 时间，保持与现有业务表排序方式一致。"""

    return datetime.utcnow()


class ClassInteraction(Base):
    """T05 老师可现场照着执行的课堂互动方案。

    source_lesson_plan_id 只记录来源，不建立数据库外键。这样教案和互动方案可以独立保存、
    编辑和删除；lesson_context_snapshot 用于保留生成当时的教案上下文，避免后续教案修改
    影响已经生成的方案。
    """

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
