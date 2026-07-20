import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _uuid() -> uuid.UUID:
    """为媒体生成领域对象创建 UUID 主键。"""

    return uuid.uuid4()


def _now() -> datetime:
    """沿用项目现有约定，保存 UTC-naive 时间。"""

    return datetime.utcnow()


class WorkflowTemplate(Base):
    """RunningHub ComfyUI 工作流的稳定业务标识。

    原始 JSON 不直接覆盖在本表中，而是写入不可变的版本表，便于回溯每次任务究竟使用了
    哪一版工作流和二次配置。
    """

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
    """工作流原文、自动识别结果与人工二次配置的版本快照。"""

    __tablename__ = "workflow_template_versions"
    __table_args__ = (
        UniqueConstraint("template_id", "version_number", name="uq_workflow_template_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_templates.id", ondelete="CASCADE"), index=True
    )
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
    """面向普通用户的媒体工作台配置。

    工作台名称和用途固定，教师只需把它绑定到一个已发布工作流或 GRS AI 模型。
    API Key 不进入本表，始终由服务端环境变量管理。
    """

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
    """一次图片、视频或音频生成请求的业务主记录。"""

    __tablename__ = "media_generations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(200), default="未命名媒体任务")
    workbench_slug: Mapped[str] = mapped_column(String(80), default="", index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    capability: Mapped[str] = mapped_column(String(40), index=True)
    model: Mapped[str] = mapped_column(String(120), default="")
    workflow_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_template_versions.id", ondelete="SET NULL"), nullable=True
    )
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
    """供应商任务运行记录，隔离各平台不同的状态与响应格式。"""

    __tablename__ = "provider_task_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    generation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_generations.id", ondelete="CASCADE"), index=True
    )
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
    """媒体输入和输出资产。

    ``managed`` 表示文件已转存 MinIO；``external`` 表示只保存供应商 URL。
    RunningHub 按业务要求使用后者，GRS AI 生成结果使用前者。
    """

    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    generation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_generations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    provider_task_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_task_runs.id", ondelete="SET NULL"), nullable=True
    )
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
