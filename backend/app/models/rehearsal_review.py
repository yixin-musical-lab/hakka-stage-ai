import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _uuid() -> uuid.UUID:
    """生成 PostgreSQL UUID 主键。"""

    return uuid.uuid4()


def _now() -> datetime:
    """统一生成 UTC-naive 时间，便于当前开发期排序。"""

    return datetime.utcnow()


class RehearsalReview(Base):
    """M08 排练 / 演出复盘报告。

    第一版以人工观察记录为事实来源。视频只作为老师查看的 MinIO 附件，
    不进入大模型输入，也不在本表保存公开访问地址。
    """

    __tablename__ = "rehearsal_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("musical_projects.id"))
    script_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("musical_scripts.id"))
    fusion_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("musical_fusion_plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    role_training_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("role_training_plans.id", ondelete="SET NULL"),
        nullable=True,
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

    @property
    def has_video_attachment(self) -> bool:
        """供 API 响应安全暴露附件状态，不返回 MinIO 对象键。"""

        return bool(self.video_object_key)
