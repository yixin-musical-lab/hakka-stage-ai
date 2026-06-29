import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _uuid() -> uuid.UUID:
    """生成 PostgreSQL UUID 主键。"""

    return uuid.uuid4()


def _now() -> datetime:
    """统一生成 UTC-naive 时间，便于本地演示和数据库排序。"""

    return datetime.utcnow()


class MovementGuide(Base):
    """T03 示范视频 / 动作图解材料。

    第一阶段只保存老师录入的动作描述、拆解说明和示范材料链接；Kimodo、Wan2.2
    Animate、Seedance 等重型生成链路后续交给 Worker 或云端 GPU，不放在 API 服务里直接执行。
    """

    __tablename__ = "movement_guides"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(200))
    action_name: Mapped[str] = mapped_column(String(160))
    action_description: Mapped[str] = mapped_column(Text)
    course_context: Mapped[str] = mapped_column(String(200), default="")
    beats: Mapped[str] = mapped_column(String(160), default="")
    body_direction: Mapped[str] = mapped_column(String(200), default="")
    difficulty: Mapped[str] = mapped_column(String(200), default="")
    teaching_tips: Mapped[str] = mapped_column(Text, default="")
    reference_video_url: Mapped[str] = mapped_column(Text, default="")
    digital_human_image_url: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="draft")
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    edited_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_pipeline_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[str] = mapped_column(String(80), default="demo-teacher")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
