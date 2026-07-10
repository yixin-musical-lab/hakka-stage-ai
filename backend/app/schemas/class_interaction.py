from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints


TeachingPhase = Literal["开场", "热身", "动作学习", "分组展示", "收束"]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)]


class ClassInteractionGenerateRequest(BaseModel):
    """T05 课堂互动方案生成请求。

    字段描述使用老师熟悉的课堂语言，同时保留英文路径和字段名，方便前端调用并保证
    OpenAPI 文档对课程组成员可读。
    """

    course_theme: str = Field(..., min_length=1, max_length=200, description="课程或本节课主题")
    age_group: str = Field(..., min_length=1, max_length=80, description="学生年龄段，例如：9-12 岁")
    teaching_phase: TeachingPhase = Field(..., description="互动发生的课堂阶段")
    interaction_goal: str = Field(..., min_length=2, max_length=800, description="本次互动希望达成的课堂目标")
    class_style: str = Field(..., min_length=1, max_length=120, description="课堂风格，例如：活泼、沉浸式")
    duration_minutes: int = Field(..., ge=1, le=45, description="互动可用时长，单位分钟")
    student_count: int = Field(..., ge=1, le=80, description="参与学生人数")
    space_materials: str = Field(
        "",
        max_length=1200,
        description="场地、材料和行动限制；没有额外材料时也可明确填写",
    )
    lesson_context: str = Field(
        "",
        max_length=4000,
        description="可选的关联教案目标、课堂内容和老师备注快照",
    )
    source_lesson_plan_id: UUID | None = Field(None, description="可选的来源教案 ID，仅用于追溯和预填")
    llm_provider: Literal["deepseek", "qwen"] | None = Field(None, description="大模型供应商")
    llm_model: str | None = Field(None, min_length=1, max_length=120, description="本次生成使用的模型")
    reasoning_level: Literal["off", "standard", "enhanced"] | None = Field(
        None,
        description="本次生成使用的推理强度",
    )


class ClassInteractionGenerateResponse(BaseModel):
    """创建课堂互动方案异步任务后的响应。"""

    task_id: UUID
    class_interaction_id: UUID
    status: str
    message: str


class TeacherScriptStep(BaseModel):
    """老师可在课堂现场逐项照着执行的一个步骤。"""

    step_no: int = Field(..., ge=1, description="执行顺序，从 1 开始")
    name: str = Field(..., min_length=1, max_length=120, description="步骤名称")
    duration_hint: str = Field(..., min_length=1, max_length=80, description="建议耗时，例如：2 分钟")
    teacher_action: str = Field(..., min_length=1, max_length=1000, description="老师需要做什么")
    teacher_cue: str = Field(..., min_length=1, max_length=800, description="老师可直接说出的课堂口令")
    student_action: str = Field(..., min_length=1, max_length=1000, description="学生预期动作或回应")


class ClassInteractionContent(BaseModel):
    """LLM 返回、老师可编辑的课堂互动方案正文。"""

    title: str = Field(..., min_length=1, max_length=200)
    teaching_phase: TeachingPhase
    interaction_goal: str = Field(..., min_length=2, max_length=800)
    duration_minutes: int = Field(..., ge=1, le=45)
    space_materials: str = Field(..., min_length=1, max_length=1600)
    game_rules: list[NonEmptyText] = Field(..., min_length=1, description="至少一条小游戏或互动规则")
    teacher_script: list[TeacherScriptStep] = Field(..., min_length=1, description="老师逐步执行脚本")
    command_phrases: list[NonEmptyText] = Field(..., min_length=1, description="老师可直接使用的口令")
    student_actions: list[NonEmptyText] = Field(..., min_length=1, description="学生动作或回应")
    grouping_method: str = Field(..., min_length=1, max_length=1000, description="分组方式或全班组织方式")
    encouragement_phrases: list[NonEmptyText] = Field(..., min_length=1, description="鼓励性课堂用语")
    safety_notes: list[NonEmptyText] = Field(..., min_length=1, description="现场安全提醒")
    variations: list[NonEmptyText] = Field(..., min_length=1, description="时间、空间或课堂状态变化时的备用方案")
    teacher_check_notes: list[NonEmptyText] = Field(..., min_length=1, description="开始前需要老师确认的事项")


class ClassInteractionResponse(BaseModel):
    """课堂互动方案详情响应。"""

    id: UUID
    source_lesson_plan_id: UUID | None
    title: str
    status: str
    course_theme: str
    age_group: str
    teaching_phase: TeachingPhase
    interaction_goal: str
    class_style: str
    duration_minutes: int
    student_count: int
    space_materials: str
    lesson_context: str
    content: ClassInteractionContent | None
    edited_content: ClassInteractionContent | None
    raw_model_info: dict | None
    created_at: datetime
    updated_at: datetime


class ClassInteractionSummaryResponse(BaseModel):
    """课堂互动方案列表摘要。"""

    id: UUID
    source_lesson_plan_id: UUID | None
    title: str
    status: str
    course_theme: str
    teaching_phase: TeachingPhase
    duration_minutes: int
    provider: str | None
    model: str | None
    reasoning_level: str | None
    created_at: datetime
    updated_at: datetime


class ClassInteractionUpdateRequest(BaseModel):
    """保存老师编辑后的课堂互动方案。"""

    edited_content: ClassInteractionContent


class LessonInteractionPrefillResponse(BaseModel):
    """从已保存教案提取的课堂互动表单预填信息。"""

    source_lesson_plan_id: UUID
    course_theme: str
    age_group: str
    student_count: int
    class_style: str
    space_materials: str
    lesson_context: str
