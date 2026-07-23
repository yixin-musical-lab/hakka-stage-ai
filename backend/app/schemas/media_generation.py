from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.base import ApiSchema as BaseModel


MediaProviderName = Literal["grsai", "runninghub"]
MediaCapability = Literal["image", "video", "audio"]


class MediaGenerationCreateRequest(BaseModel):
    """创建统一媒体生成任务的请求。"""

    title: str = Field("", max_length=200, description="便于在任务列表中识别的名称")
    provider: MediaProviderName = Field(description="供应商：grsai 或 runninghub")
    capability: MediaCapability = Field(description="目标媒体类型")
    model: str = Field("", max_length=120, description="GRS AI 模型标识")
    workflow_version_id: UUID | None = Field(None, description="RunningHub 已发布工作流版本 ID")
    prompt: str = Field("", max_length=20000, description="提示词或主要文本内容")
    parameters: dict[str, Any] = Field(default_factory=dict, description="模型或工作流参数")
    input_asset_ids: dict[str, UUID] = Field(
        default_factory=dict,
        description="输入绑定名到媒体资产 ID 的映射，例如 reference_audio -> UUID",
    )
    client_request_id: str = Field("", max_length=100, description="客户端幂等请求标识")

    @model_validator(mode="after")
    def validate_provider_fields(self) -> "MediaGenerationCreateRequest":
        """在 OpenAPI 校验阶段就提示缺失的供应商特有字段。"""

        if self.provider == "grsai" and self.capability != "image":
            raise ValueError("当前阶段 GRS AI 仅开放 Nano Banana 生图能力")
        if self.provider == "grsai" and not self.model:
            self.model = "nano-banana-fast"
        if self.provider == "runninghub" and self.workflow_version_id is None:
            raise ValueError("RunningHub 任务必须选择已发布的工作流版本")
        return self


class ProviderTaskRunResponse(BaseModel):
    id: UUID
    provider: str
    external_task_id: str | None
    provider_status: str
    poll_count: int
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class MediaAssetResponse(BaseModel):
    id: UUID
    role: str
    media_type: str
    storage_mode: str
    url: str
    original_file_name: str
    content_type: str
    size_bytes: int | None
    provider: str
    status: str
    created_at: datetime


class MediaAssetUploadResponse(BaseModel):
    asset: MediaAssetResponse
    message: str = "媒体文件已保存到 MinIO，可用于创建任务"


class MediaGenerationResponse(BaseModel):
    id: UUID
    task_id: UUID | None
    title: str
    workbench_slug: str
    provider: str
    capability: str
    model: str
    workflow_version_id: UUID | None
    status: str
    prompt: str
    parameters: dict[str, Any]
    input_asset_ids: dict[str, UUID]
    runs: list[ProviderTaskRunResponse]
    assets: list[MediaAssetResponse]
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None


class MediaProviderOption(BaseModel):
    key: str
    label: str
    configured: bool
    capabilities: list[str]
    storage_policy: str
    models: list[str] = Field(default_factory=list)


class MediaProviderOptionsResponse(BaseModel):
    mock_mode: bool
    providers: list[MediaProviderOption]


class WorkflowParameterConfig(BaseModel):
    """工作流字段的二次配置，可由课程组修改自动识别草稿。"""

    key: str = Field(min_length=1, max_length=100)
    node_id: str = Field(min_length=1, max_length=40)
    field_name: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=120)
    value_type: Literal["text", "number", "boolean", "file", "select", "json"]
    required: bool = False
    default: Any = None
    minimum: float | None = None
    maximum: float | None = None
    options: list[Any] = Field(default_factory=list)
    visibility: Literal["basic", "advanced", "hidden"] = "advanced"
    asset_role: str | None = None
    order: int = 0
    description: str = ""


class WorkflowOutputConfig(BaseModel):
    node_id: str
    class_type: str
    label: str
    media_type: MediaCapability
    enabled: bool = True
    primary: bool = False


class WorkbenchFieldConfig(BaseModel):
    """一个用户侧输入控件及其供应商参数映射。"""

    label: str = Field(min_length=1, max_length=120)
    help_text: str = Field("", max_length=500)
    required: bool = False
    media_type: Literal["image", "audio", "video"] | None = None
    target_parameter_key: str = Field("", max_length=100)


class MediaWorkbenchInputConfig(BaseModel):
    prompt: WorkbenchFieldConfig
    primary_asset: WorkbenchFieldConfig
    secondary_asset: WorkbenchFieldConfig | None = None
    exposed_parameter_keys: list[str] = Field(default_factory=list)


class MediaWorkbenchConfigUpdateRequest(BaseModel):
    """教师配置工作台；供应商种类和用途由工作台 slug 固定。"""

    display_name: str = Field(min_length=1, max_length=120)
    description: str = Field("", max_length=2000)
    workflow_version_id: UUID | None = None
    model: str = Field("", max_length=120)
    provider_api_mode: Literal["workflow", "unified", "legacy"]
    default_parameters: dict[str, Any] = Field(default_factory=dict)
    input_config: MediaWorkbenchInputConfig
    enabled: bool = True


class MediaWorkbenchConfigResponse(BaseModel):
    id: UUID
    slug: str
    display_name: str
    description: str
    provider: str
    capability: str
    workflow_version_id: UUID | None
    model: str
    provider_api_mode: str
    default_parameters: dict[str, Any]
    input_config: MediaWorkbenchInputConfig
    enabled: bool
    provider_configured: bool
    configured: bool
    configuration_issues: list[str]
    workflow_parameters: list[WorkflowParameterConfig]
    updated_at: datetime


class MediaWorkbenchRunRequest(BaseModel):
    """从专注工作台创建任务时使用的用户侧参数。"""

    prompt: str = Field(min_length=1, max_length=20000, description="生成或修改要求")
    primary_asset_id: UUID | None = Field(
        None,
        description="单个主输入素材 ID；保留给克隆音频和旧版单图客户端使用",
    )
    primary_asset_ids: list[UUID] = Field(
        default_factory=list,
        max_length=10,
        description="图生图参考素材 ID 列表，按数组顺序传给模型，最多 10 张",
    )
    secondary_asset_id: UUID | None = Field(None, description="可选的第二输入素材 ID")
    parameters: dict[str, Any] = Field(default_factory=dict, description="工作台允许用户调整的参数")
    client_request_id: str = Field("", max_length=100, description="客户端幂等请求标识")

    @model_validator(mode="after")
    def validate_primary_asset_ids(self) -> "MediaWorkbenchRunRequest":
        """重复引用同一素材没有额外信息量，应在任务入队前直接提示。"""

        if len(set(self.primary_asset_ids)) != len(self.primary_asset_ids):
            raise ValueError("图生图参考素材不能重复")
        return self


class WorkflowVersionConfigureRequest(BaseModel):
    parameters: list[WorkflowParameterConfig]
    outputs: list[WorkflowOutputConfig]


class WorkflowTemplateUpdateRequest(BaseModel):
    """修改模板级信息；不会覆盖任何已保存的工作流 JSON。"""

    name: str = Field(min_length=1, max_length=200)
    description: str = Field("", max_length=2000)
    external_workflow_id: str = Field("", max_length=120, description="RunningHub 平台 workflowId")
    media_type: MediaCapability = "audio"


class WorkflowVersionResponse(BaseModel):
    id: UUID
    template_id: UUID
    version_number: int
    source_filename: str
    workflow_hash: str
    analysis: dict[str, Any]
    parameters: list[WorkflowParameterConfig]
    outputs: list[WorkflowOutputConfig]
    status: str
    created_at: datetime
    published_at: datetime | None


class WorkflowTemplateResponse(BaseModel):
    id: UUID
    name: str
    description: str
    provider: str
    external_workflow_id: str
    media_type: str
    status: str
    versions: list[WorkflowVersionResponse]
    created_at: datetime
    updated_at: datetime
