from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.base import ApiSchema as BaseModel


class MovementGuideCreateRequest(BaseModel):
    """T03 动作图解 / 示范材料创建请求。

    第一阶段只录入可复用的动作说明和材料链接，不在 API 服务里直接生成视频。
    字段名使用英文，中文描述用于保证 OpenAPI 文档可读。
    """

    action_name: str = Field(..., min_length=1, max_length=160, description="动作名称，例如：双手打开转身")
    action_description: str = Field(..., min_length=4, max_length=1600, description="动作文字描述，例如：双手从胸前打开，同时向右转身一圈")
    course_context: str = Field("", max_length=200, description="适用课程或剧目片段，例如：客家山歌主题舞蹈体验课")
    beats: str = Field("", max_length=160, description="动作节拍，例如：4 拍完成，前 2 拍打开双手，后 2 拍转身")
    body_direction: str = Field("", max_length=200, description="身体方向，例如：面向正前方开始，向右转身")
    difficulty: str = Field("", max_length=200, description="难度要求，例如：适合 8-12 岁零基础学生")
    teaching_tips: str = Field("", max_length=1600, description="教学提示，例如：注意重心稳定")
    reference_video_url: str = Field("", max_length=1200, description="老师参考视频链接，后续可替换为 MinIO 对象地址")
    digital_human_image_url: str = Field("", max_length=1200, description="数字人形象图链接，后续用于真人 / 数字人风格视频生成")


class MovementStepDetail(BaseModel):
    """动作拆解中的一个教学步骤。"""

    name: str = Field(..., min_length=1, max_length=160, description="步骤名称")
    beats: str = Field("", max_length=160, description="对应节拍")
    description: str = Field("", max_length=800, description="步骤说明")
    teacher_cue: str = Field("", max_length=400, description="老师口令或提醒话术")


class MovementMediaAsset(BaseModel):
    """示范材料中的一个媒体条目。"""

    asset_type: Literal["reference_video", "skeleton_preview", "confirmed_skeleton", "digital_human_video", "courseware_video", "image"] = Field(
        ...,
        description="材料类型：参考视频、骨骼预览、确认骨骼示范、真人/数字人视频、课件展示视频或图片",
    )
    title: str = Field(..., min_length=1, max_length=160, description="材料标题")
    url: str = Field("", max_length=1200, description="材料访问地址，第一阶段可填写外部链接或留空")
    status: Literal["draft", "candidate", "confirmed", "rejected"] = Field("draft", description="材料确认状态")
    notes: str = Field("", max_length=800, description="材料备注")


class MovementGuideContent(BaseModel):
    """动作图解详情，前端可编辑后保存为老师确认稿。"""

    title: str = Field(..., min_length=1, max_length=200, description="示范材料标题")
    action_name: str = Field(..., min_length=1, max_length=160, description="动作名称")
    action_description: str = Field(..., min_length=4, max_length=1600, description="动作文字描述")
    course_context: str = Field("", max_length=200, description="适用课程或剧目片段")
    beats: str = Field("", max_length=160, description="动作节拍")
    body_direction: str = Field("", max_length=200, description="身体方向")
    difficulty: str = Field("", max_length=200, description="难度要求")
    normalized_motion_script: str = Field("", max_length=2000, description="后续供动作生成模型使用的规范动作脚本")
    breakdown_steps: list[MovementStepDetail] = Field(default_factory=list, description="动作步骤拆解")
    rhythm_tips: list[str] = Field(default_factory=list, description="节奏提示")
    common_mistakes: list[str] = Field(default_factory=list, description="常见错误")
    correction_cues: list[str] = Field(default_factory=list, description="纠正话术")
    teaching_tips: list[str] = Field(default_factory=list, description="教学提示")
    media_assets: list[MovementMediaAsset] = Field(default_factory=list, description="示范视频、骨骼动画或图片材料")
    teacher_review_notes: str = Field("", max_length=1600, description="老师验收或复核说明")


class MovementGuideResponse(BaseModel):
    """动作图解 / 示范材料详情响应。"""

    id: UUID
    title: str
    action_name: str
    action_description: str
    course_context: str
    beats: str
    body_direction: str
    difficulty: str
    teaching_tips: str
    reference_video_url: str
    digital_human_image_url: str
    status: str
    content: MovementGuideContent | None
    edited_content: MovementGuideContent | None
    raw_pipeline_info: dict | None
    created_at: datetime
    updated_at: datetime


class MovementGuideSummaryResponse(BaseModel):
    """动作图解 / 示范材料列表摘要响应。"""

    id: UUID
    title: str
    action_name: str
    course_context: str
    status: str
    asset_count: int
    confirmed_asset_count: int
    created_at: datetime
    updated_at: datetime


class MovementGuideUpdateRequest(BaseModel):
    """保存老师编辑后的动作图解。"""

    edited_content: MovementGuideContent


class MovementGuideGeneratePlaceholderResponse(BaseModel):
    """动作生成占位响应。

    用 501 明确告知前端和协作者：当前只完成材料管理骨架，真实 Kimodo / 视频生成链路
    需要后续 Worker 和云端 GPU 能力接入。
    """

    movement_guide_id: UUID
    status: Literal["not_implemented"]
    message: str
