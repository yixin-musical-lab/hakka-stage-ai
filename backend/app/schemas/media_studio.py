from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# 旧 Veo 值只用于兼容 Redis 中尚未过期的历史任务；新任务仅开放 Wan 2.7。
VeoModelCode = Literal["wan2.7-i2v-2026-04-25", "veo3.1-fast", "veo3.1-pro"]
VeoAspectRatio = Literal["auto", "16:9", "9:16"]
VeoResolution = Literal["720P", "1080P"]
VeoTaskStatus = Literal["submitting", "running", "succeeded", "failed"]
MotionTransferModelCode = Literal["wan2.2-animate-move"]
MotionTransferMode = Literal["wan-std", "wan-pro"]


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


class MotionTransferModeOption(BaseModel):
    """动作模仿页面展示的质量档位与费用提示。"""

    code: MotionTransferMode
    name: str
    description: str
    frames_per_second: int = Field(ge=1)
    price_cny_per_second: float = Field(ge=0)


class MotionTransferOptionsResponse(BaseModel):
    """Wan 2.2 图生动作工作台初始化所需的公开能力信息。"""

    provider: Literal["dashscope"] = "dashscope"
    configured: bool
    mock_mode: bool
    file_upload_available: bool
    model: MotionTransferModelCode = "wan2.2-animate-move"
    modes: list[MotionTransferModeOption]
    image_max_upload_mb: int = 5
    video_max_upload_mb: int = 200
    accepted_image_types: list[str]
    accepted_video_types: list[str]
    duration_min_seconds: int = 2
    duration_max_seconds: int = 30
    image_dimension_min_pixels: int = 200
    image_dimension_max_pixels: int = 4096
    video_dimension_min_pixels: int = 200
    video_dimension_max_pixels: int = 2048
    aspect_ratio_min: float = Field(1 / 3, gt=0)
    aspect_ratio_max: float = Field(3, gt=0)
    resolution: Literal["720P"] = "720P"
    result_url_ttl_hours: int = 24
    input_guidance: list[str]


class MotionTransferTaskResponse(BaseModel):
    """动作模仿任务的安全响应，不返回供应商任务 ID 或 MinIO 对象键。"""

    id: str
    status: VeoTaskStatus
    progress: int = Field(ge=0, le=100)
    provider: Literal["dashscope"] = "dashscope"
    model: MotionTransferModelCode = "wan2.2-animate-move"
    mode: MotionTransferMode
    resolution: Literal["720P"] = "720P"
    watermark: bool
    person_file_name: str
    motion_file_name: str
    motion_duration_seconds: float | None = Field(None, ge=0)
    result_available: bool = False
    result_persisted: bool = False
    storage_warning: str = ""
    failure_reason: str = ""
    error_message: str = ""
    created_at: datetime
    updated_at: datetime
    expires_at: datetime

