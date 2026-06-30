import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _uuid() -> uuid.UUID:
    """生成 PostgreSQL UUID 主键。"""

    return uuid.uuid4()


def _now() -> datetime:
    """统一生成 UTC-naive 时间，便于本地演示和数据库排序。"""

    return datetime.utcnow()


class PracticeSubmission(Base):
    """T06 学生课后练习提交记录。

    第一阶段先保存练习任务、学生信息和视频对象地址，不在 API 服务里直接接收大文件或执行
    RTMPose / DTW 等重型视频分析。后续接入 MinIO 和 Worker 后，可以继续沿用这张表记录业务状态。
    """

    __tablename__ = "practice_submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    course_title: Mapped[str] = mapped_column(String(200), default="")
    task_title: Mapped[str] = mapped_column(String(200))
    task_description: Mapped[str] = mapped_column(Text, default="")
    student_name: Mapped[str] = mapped_column(String(80))
    student_group: Mapped[str] = mapped_column(String(120), default="")
    video_url: Mapped[str] = mapped_column(Text)
    video_file_name: Mapped[str] = mapped_column(String(240), default="")
    video_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    video_notes: Mapped[str] = mapped_column(Text, default="")
    reference_action_name: Mapped[str] = mapped_column(String(160), default="")
    reference_video_url: Mapped[str] = mapped_column(Text, default="")
    evaluation_focus: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(40), default="submitted")
    created_by: Mapped[str] = mapped_column(String(80), default="demo-student")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class PracticeReport(Base):
    """T06 练习辅助观察报告和老师复核意见。

    content 保存系统生成的基础观察稿，edited_content 保存老师复核后的确认稿；报告口径使用
    “观察建议”，避免第一阶段给出专业动作评分或正确率承诺。
    """

    __tablename__ = "practice_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("practice_submissions.id"))
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40), default="draft")
    analysis_mode: Mapped[str] = mapped_column(String(80), default="basic_observation")
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    edited_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    teacher_feedback: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[str] = mapped_column(String(80), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_analysis_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
