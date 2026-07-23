import re
from datetime import date, datetime
from pathlib import Path
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.base import ApiSchema as BaseModel


M08_OBJECT_KEY_PATTERN = re.compile(
    r"^rehearsal-reviews/[0-9a-f]{32}\.(?:mp4|mov|m4v|webm|avi|mkv)$"
)
M08_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}


class RehearsalReviewGenerateRequest(BaseModel):
    """M08 排练 / 演出复盘报告生成请求。"""

    script_id: UUID = Field(..., description="必选的歌舞剧剧本 ID")
    fusion_plan_id: UUID | None = Field(None, description="可选的同剧本 M04 歌舞融合方案 ID")
    role_training_plan_id: UUID | None = Field(None, description="可选的同剧本 M05 分角色训练计划 ID")
    event_type: Literal["rehearsal", "performance"] = Field("rehearsal", description="记录类型：排练或演出")
    event_date: date = Field(..., description="排练或演出日期")
    rehearsal_content: str = Field(..., min_length=1, max_length=4000, description="本次排练或演出的主要内容")
    observation_notes: str = Field(..., min_length=2, max_length=8000, description="老师或编导的原始观察记录")
    strengths: str = Field("", max_length=4000, description="本次完成较好的部分")
    issues: str = Field("", max_length=5000, description="已经明确的问题，可为空并由观察记录归纳")
    review_focus: list[str] = Field(..., min_length=1, max_length=8, description="复盘重点，例如唱段、队形、表情")
    next_goal: str = Field(..., min_length=1, max_length=2000, description="下一次排练或演出的目标")
    video_object_key: str = Field("", max_length=500, description="上传接口返回的 MinIO 对象键")
    video_original_file_name: str = Field("", max_length=240, description="视频原始文件名")
    video_content_type: str = Field("", max_length=120, description="视频 MIME 类型")
    video_size_bytes: int | None = Field(None, ge=1, description="视频大小，单位字节")
    video_notes: str = Field("", max_length=1600, description="老师对视频片段的人工备注；AI 不读取视频")
    llm_provider: Literal["deepseek", "qwen"] | None = Field(None, description="大模型供应商")
    llm_model: str | None = Field(None, min_length=1, max_length=120, description="本次生成使用的模型")
    reasoning_level: Literal["off", "standard", "enhanced"] | None = Field(None, description="本次生成使用的推理强度")

    @model_validator(mode="after")
    def validate_video_metadata(self) -> Self:
        """确保附件元数据成组出现，且对象只能位于 M08 专用目录。"""

        metadata_present = bool(
            self.video_original_file_name or self.video_content_type or self.video_size_bytes is not None
        )
        if not self.video_object_key:
            if metadata_present:
                raise ValueError("未提供视频对象键时不能同时提供视频文件元数据。")
            return self
        if not M08_OBJECT_KEY_PATTERN.fullmatch(self.video_object_key):
            raise ValueError("视频对象键必须是上传接口生成的 rehearsal-reviews/{uuid}.{ext} 格式。")
        if not self.video_original_file_name or not self.video_content_type or self.video_size_bytes is None:
            raise ValueError("视频附件必须同时提供原始文件名、MIME 类型和文件大小。")
        if (
            "/" in self.video_original_file_name
            or "\\" in self.video_original_file_name
            or any(ord(character) < 32 for character in self.video_original_file_name)
        ):
            raise ValueError("视频原始文件名不能包含路径或控制字符。")
        extension = Path(self.video_original_file_name).suffix.lower()
        if extension not in M08_VIDEO_EXTENSIONS:
            raise ValueError("视频原始文件名扩展名不受支持。")
        if not (self.video_content_type.startswith("video/") or extension in {".mov", ".m4v"}):
            raise ValueError("视频附件 MIME 类型无效。")
        return self


class RehearsalReviewGenerateResponse(BaseModel):
    """创建 M08 异步任务后的响应。"""

    task_id: UUID
    rehearsal_review_id: UUID
    status: str
    message: str


class RehearsalVideoUploadResponse(BaseModel):
    """M08 视频附件上传到 MinIO 后的安全元数据。"""

    object_key: str
    original_file_name: str
    content_type: str
    size_bytes: int = Field(..., ge=1)
    storage_mode: Literal["minio"] = "minio"


class RehearsalIssue(BaseModel):
    """复盘报告中的一个结构化问题。"""

    category: str = Field(..., min_length=1, max_length=80)
    observation: str = Field(..., min_length=1, max_length=1600)
    possible_cause: str = Field(..., min_length=1, max_length=1200)
    improvement_action: str = Field(..., min_length=1, max_length=1600)
    priority: Literal["high", "medium", "low"]
    next_check: str = Field(..., min_length=1, max_length=1200)


class RehearsalRoleSuggestion(BaseModel):
    """某个角色或角色组的改进建议。"""

    role_name: str = Field(..., min_length=1, max_length=120)
    observation: str = Field(..., min_length=1, max_length=1200)
    suggestion: str = Field(..., min_length=1, max_length=1600)
    next_tasks: list[str] = Field(..., min_length=1, max_length=8)


class NextRehearsalPlan(BaseModel):
    """下一次排练的可执行安排。"""

    goal: str = Field(..., min_length=1, max_length=1200)
    focus_items: list[str] = Field(..., min_length=1, max_length=8)
    action_steps: list[str] = Field(..., min_length=1, max_length=12)
    teacher_checkpoints: list[str] = Field(..., min_length=1, max_length=8)


class ReusableReviewTemplate(BaseModel):
    """保存在报告内部、可用于下一次复盘的轻量模板。"""

    template_title: str = Field(..., min_length=1, max_length=200)
    review_focus: list[str] = Field(..., min_length=1, max_length=8)
    observation_prompts: list[str] = Field(..., min_length=1, max_length=10)
    closing_checklist: list[str] = Field(..., min_length=1, max_length=8)


class RehearsalReviewContent(BaseModel):
    """M08 结构化复盘报告正文。"""

    title: str = Field(..., min_length=1, max_length=200)
    overview: str = Field(..., min_length=1, max_length=2400)
    highlights: list[str] = Field(..., min_length=1, max_length=10)
    issues: list[RehearsalIssue] = Field(..., min_length=1, max_length=12)
    role_suggestions: list[RehearsalRoleSuggestion] = Field(..., min_length=1, max_length=20)
    singing_and_rhythm_advice: str = Field(..., min_length=1, max_length=1800)
    dance_and_formation_advice: str = Field(..., min_length=1, max_length=1800)
    performance_and_blocking_advice: str = Field(..., min_length=1, max_length=1800)
    next_rehearsal_plan: NextRehearsalPlan
    teaching_reflection: str = Field(..., min_length=1, max_length=2400)
    reusable_template: ReusableReviewTemplate
    reviewer_notes: list[str] = Field(..., min_length=1, max_length=8)
    boundary_note: str = Field(..., min_length=1, max_length=1200)


class RehearsalReviewResponse(BaseModel):
    """复盘报告详情响应。"""

    id: UUID
    project_id: UUID
    script_id: UUID
    fusion_plan_id: UUID | None
    role_training_plan_id: UUID | None
    title: str
    status: str
    event_type: str
    event_date: date
    rehearsal_content: str
    observation_notes: str
    strengths: str
    issues: str
    review_focus: list[str]
    next_goal: str
    has_video_attachment: bool
    video_original_file_name: str
    video_content_type: str
    video_size_bytes: int | None
    video_notes: str
    content: RehearsalReviewContent | None
    edited_content: RehearsalReviewContent | None
    raw_model_info: dict | None
    created_at: datetime
    updated_at: datetime


class RehearsalReviewSummaryResponse(BaseModel):
    """复盘报告列表摘要。"""

    id: UUID
    project_id: UUID
    script_id: UUID
    fusion_plan_id: UUID | None
    role_training_plan_id: UUID | None
    title: str
    status: str
    event_type: str
    event_date: date
    has_video_attachment: bool
    provider: str | None
    model: str | None
    reasoning_level: str | None = None
    created_at: datetime
    updated_at: datetime


class RehearsalReviewUpdateRequest(BaseModel):
    """保存老师或编导编辑后的复盘报告。"""

    edited_content: RehearsalReviewContent
