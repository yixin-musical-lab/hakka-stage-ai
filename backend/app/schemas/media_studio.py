from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# 旧 Veo 值只用于兼容 Redis 中尚未过期的历史任务；新任务仅开放 Wan 2.7。
VeoModelCode = Literal["wan2.7-i2v-2026-04-25", "veo3.1-fast", "veo3.1-pro"]
VeoAspectRatio = Literal["auto", "16:9", "9:16"]
VeoResolution = Literal["720P", "1080P"]
VeoTaskStatus = Literal["submitting", "running", "succeeded", "failed"]


class VeoModelOption(BaseModel):
    """媒体工作台可展示的视频模型，不把第三方原始配置直接暴露给前端。"""

    code: VeoModelCode
    name: str
    description: str


class VeoOptionsResponse(BaseModel):
    """图生视频页面初始化所需的稳定选项。"""

    provider: str = "dashscope"
    configured: bool
    mock_mode: bool
    file_upload_available: bool
    image_max_upload_mb: int
    accepted_image_types: list[str]
    models: list[VeoModelOption]
    aspect_ratios: list[VeoAspectRatio]
    resolutions: list[VeoResolution]
    duration_min_seconds: int = 2
    duration_max_seconds: int = 15
    default_duration_seconds: int = 5
    output_ratio_note: str
    supports_last_frame: bool = True
    supports_reference_images: bool = True
    reference_images_note: str
    result_url_ttl_hours: int = 24


class VeoTaskResponse(BaseModel):
    """平台归一化后的视频任务状态，隐藏供应商密钥与原始请求快照。"""

    id: str
    status: VeoTaskStatus
    progress: int = Field(ge=0, le=100)
    provider: Literal["dashscope", "grsai"] = "dashscope"
    model: VeoModelCode
    prompt: str
    aspect_ratio: VeoAspectRatio = "auto"
    resolution: VeoResolution = "720P"
    duration_seconds: int = Field(5, ge=2, le=15)
    source_file_name: str = ""
    source_mode: Literal["upload", "url"]
    has_last_frame: bool = False
    video_url: str = ""
    failure_reason: str = ""
    error_message: str = ""
    created_at: datetime
    updated_at: datetime
    expires_at: datetime

