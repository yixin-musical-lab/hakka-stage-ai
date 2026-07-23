from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


VeoModelCode = Literal["veo3.1-fast", "veo3.1-pro"]
VeoAspectRatio = Literal["16:9", "9:16"]
VeoTaskStatus = Literal["submitting", "running", "succeeded", "failed"]


class VeoModelOption(BaseModel):
    """媒体工作台可展示的 Veo 模型，不把第三方原始配置直接暴露给前端。"""

    code: VeoModelCode
    name: str
    description: str


class VeoOptionsResponse(BaseModel):
    """图生视频页面初始化所需的稳定选项。"""

    provider: str = "grsai"
    configured: bool
    mock_mode: bool
    file_upload_available: bool
    image_max_upload_mb: int
    accepted_image_types: list[str]
    models: list[VeoModelOption]
    aspect_ratios: list[VeoAspectRatio]
    supports_last_frame: bool = True
    supports_reference_images: bool = True
    reference_images_note: str
    result_url_ttl_hours: int = 2


class VeoTaskResponse(BaseModel):
    """平台归一化后的 Veo 任务状态，隐藏供应商密钥与原始请求快照。"""

    id: str
    status: VeoTaskStatus
    progress: int = Field(ge=0, le=100)
    model: VeoModelCode
    prompt: str
    aspect_ratio: VeoAspectRatio
    source_file_name: str = ""
    source_mode: Literal["upload", "url"]
    has_last_frame: bool = False
    video_url: str = ""
    failure_reason: str = ""
    error_message: str = ""
    created_at: datetime
    updated_at: datetime
    expires_at: datetime

