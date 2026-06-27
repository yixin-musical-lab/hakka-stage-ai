from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class LessonPlanGenerateRequest(BaseModel):
    """教案生成请求。

    字段名使用英文，描述保留中文业务语义，保证 OpenAPI 文档能被课程组看懂。
    """

    dance_style: str = Field(..., min_length=1, max_length=120, description="舞种或教学方向，例如：客家山歌舞")
    theme: str = Field(..., min_length=1, max_length=200, description="课程主题，例如：乡土美育")
    age_group: str = Field(..., min_length=1, max_length=80, description="学生年龄段，例如：8-12 岁")
    duration_minutes: int = Field(..., ge=10, le=180, description="单节课时长，单位分钟")
    student_count: int = Field(..., ge=1, le=80, description="学生人数")
    teaching_goal: str = Field(..., min_length=4, max_length=1200, description="本节课教学目标")
    learning_level: str = Field(..., min_length=1, max_length=120, description="学生基础，例如：零基础/有基础")
    course_style: str = Field(..., min_length=1, max_length=120, description="课程风格，例如：活泼、沉浸式、舞台排练")
    notes: str = Field("", max_length=1200, description="注意事项或特殊要求")
    llm_provider: Literal["deepseek", "qwen"] | None = Field(None, description="大模型供应商")
    llm_model: str | None = Field(None, min_length=1, max_length=120, description="本次生成使用的模型")
    reasoning_level: Literal["off", "standard", "enhanced"] | None = Field(None, description="本次生成使用的推理强度")


class LessonPlanGenerateResponse(BaseModel):
    """创建教案生成任务后的响应。"""

    task_id: UUID
    lesson_plan_id: UUID
    status: str
    message: str


class LessonActivity(BaseModel):
    """教案中的一个教学活动环节。"""

    name: str
    duration_minutes: int = Field(ge=0)
    description: str


class MovementStep(BaseModel):
    """动作拆解步骤。"""

    name: str
    beats: str
    teaching_tips: str


class LessonPlanContent(BaseModel):
    """LLM 需要返回、前端可编辑的结构化教案正文。"""

    title: str
    course_overview: str
    teaching_goals: list[str]
    key_points: list[str]
    common_mistakes: list[str]
    warmup: list[LessonActivity]
    main_teaching: list[LessonActivity]
    movement_breakdown: list[MovementStep]
    cooldown: list[LessonActivity]
    homework: list[str]
    teacher_notes: list[str]


class LessonPlanResponse(BaseModel):
    """教案详情响应。"""

    id: UUID
    course_id: UUID
    title: str
    status: str
    content: LessonPlanContent | None
    edited_content: LessonPlanContent | None
    raw_model_info: dict | None
    created_at: datetime
    updated_at: datetime


class LessonPlanSummaryResponse(BaseModel):
    """教案列表摘要响应。"""

    id: UUID
    course_id: UUID
    title: str
    status: str
    provider: str | None
    model: str | None
    reasoning_level: str | None = None
    created_at: datetime
    updated_at: datetime


class LessonPlanUpdateRequest(BaseModel):
    """保存老师编辑稿。"""

    edited_content: LessonPlanContent


class AiTaskResponse(BaseModel):
    """AI 任务状态响应。"""

    id: UUID
    task_type: str
    status: Literal["PENDING", "RUNNING", "SUCCESS", "FAILED", "CANCELLED"]
    progress: int
    business_id: UUID
    result_id: UUID | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class LlmModelOption(BaseModel):
    """前端可选择的单个模型。"""

    id: str
    label: str


class LlmProviderOption(BaseModel):
    """前端可选择的大模型供应商。"""

    id: Literal["deepseek", "qwen"]
    label: str
    configured: bool
    models: list[LlmModelOption]


class ReasoningLevelOption(BaseModel):
    """统一推理强度选项。"""

    id: Literal["off", "standard", "enhanced"]
    label: str
    description: str


class LlmOptionsResponse(BaseModel):
    """模型选择配置，供教案生成页初始化下拉框。"""

    default_provider: Literal["deepseek", "qwen"]
    default_model: str
    default_reasoning_level: Literal["off", "standard", "enhanced"]
    providers: list[LlmProviderOption]
    reasoning_levels: list[ReasoningLevelOption]
