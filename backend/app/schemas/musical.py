from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1600)]


class MusicalScriptGenerateRequest(BaseModel):
    """M01 剧本生成请求。"""

    theme: str = Field(..., min_length=1, max_length=200, description="剧目主题，例如：客家文化、乡土美育")
    duration_minutes: int = Field(..., ge=3, le=60, description="演出时长，单位分钟")
    actor_count: int = Field(..., ge=1, le=120, description="演员人数")
    age_group: str = Field(..., min_length=1, max_length=80, description="演员年龄段，例如：8-12 岁")
    style_requirements: str = Field(..., min_length=1, max_length=1200, description="风格要求，例如：温暖、积极、校园展示")
    required_elements: str = Field("", max_length=1200, description="必须出现的元素，例如：客家山歌、劳动场景")
    forbidden_content: str = Field("", max_length=1200, description="禁忌内容或限制，例如：台词不能太长")
    llm_provider: Literal["deepseek", "qwen"] | None = Field(None, description="大模型供应商")
    llm_model: str | None = Field(None, min_length=1, max_length=120, description="本次生成使用的模型")
    reasoning_level: Literal["off", "standard", "enhanced"] | None = Field(None, description="本次生成使用的推理强度")


class MusicalScriptGenerateResponse(BaseModel):
    """创建剧本生成任务后的响应。"""

    task_id: UUID
    musical_script_id: UUID
    status: str
    message: str


class ScriptDialogueLine(BaseModel):
    """剧本中的一句台词或旁白。"""

    role_name: str
    line: str
    stage_direction: str


class ScriptAct(BaseModel):
    """剧本中的一幕或一个剧情段落。"""

    name: str
    duration_minutes: int = Field(ge=0)
    story_outline: str
    emotion: str
    narrator_text: str
    dialogues: list[ScriptDialogueLine]


class ScriptCharacter(BaseModel):
    """剧本角色卡。"""

    name: str
    role_type: str
    personality: str
    character_arc: str
    performance_tips: str
    key_lines: list[str]


class PerformanceSlot(BaseModel):
    """舞蹈、独唱、群舞等留白段落。"""

    act_name: str
    slot_type: str
    description: str
    suggested_duration: str
    notes: str


class MusicalScriptContent(BaseModel):
    """M01 结构化剧本正文。"""

    title: str
    synopsis: str
    acts: list[ScriptAct]
    characters: list[ScriptCharacter]
    performance_slots: list[PerformanceSlot]
    director_notes: list[str]


class MusicalScriptResponse(BaseModel):
    """剧本详情响应。"""

    id: UUID
    project_id: UUID
    title: str
    status: str
    content: MusicalScriptContent | None
    edited_content: MusicalScriptContent | None
    raw_model_info: dict | None
    created_at: datetime
    updated_at: datetime


class MusicalScriptSummaryResponse(BaseModel):
    """剧本列表摘要响应。"""

    id: UUID
    project_id: UUID
    title: str
    status: str
    provider: str | None
    model: str | None
    reasoning_level: str | None = None
    created_at: datetime
    updated_at: datetime


class MusicalScriptUpdateRequest(BaseModel):
    """保存编导编辑后的剧本。"""

    edited_content: MusicalScriptContent


class SongAdaptationGenerateRequest(BaseModel):
    """M03-lite 唱段适配生成请求。"""

    script_id: UUID = Field(..., description="要引用的剧本 ID")
    related_scene: str = Field(..., min_length=1, max_length=240, description="关联剧情段落，例如：第二幕：一起排练")
    source_song: str = Field("", max_length=200, description="原曲名称或音乐来源，例如：客家山歌类曲目")
    lyrics_text: str = Field(..., min_length=1, max_length=8000, description="原歌词或待改写歌词文本")
    music_structure: str = Field(..., min_length=1, max_length=4000, description="人工整理的音乐段落表，例如：0:00-0:18 前奏")
    adaptation_goal: str = Field(..., min_length=1, max_length=1200, description="唱段要服务的剧情表达目标")
    singing_roles: str = Field("", max_length=1200, description="建议参与演唱的角色，可从剧本角色中整理")
    rewrite_intensity: Literal["structure_only", "light_rewrite", "strong_rewrite"] = Field(
        "light_rewrite",
        description="改写强度：只做结构标注、轻微改词或明显改编",
    )
    llm_provider: Literal["deepseek", "qwen"] | None = Field(None, description="大模型供应商")
    llm_model: str | None = Field(None, min_length=1, max_length=120, description="本次生成使用的模型")
    reasoning_level: Literal["off", "standard", "enhanced"] | None = Field(None, description="本次生成使用的推理强度")


class SongAdaptationGenerateResponse(BaseModel):
    """创建唱段适配任务后的响应。"""

    task_id: UUID
    song_adaptation_id: UUID
    status: str
    message: str


class SongSection(BaseModel):
    """唱段适配中的一个音乐 / 歌词段落。"""

    section_no: str
    music_position: str
    original_lyrics: str
    adapted_lyrics: str
    singing_mode: str
    suggested_roles: list[str]
    emotion: str
    dance_opportunity: str
    transition_note: str


class DanceInterlude(BaseModel):
    """间奏或歌词留白处的舞蹈安排建议。"""

    music_position: str
    suggestion: str


class SongAdaptationContent(BaseModel):
    """M03-lite 结构化唱段适配正文。"""

    title: str
    source_song: str
    related_scene: str
    adaptation_goal: str
    sections: list[SongSection]
    dance_interludes: list[DanceInterlude]
    review_notes: list[str]


class SongAdaptationResponse(BaseModel):
    """唱段适配详情响应。"""

    id: UUID
    project_id: UUID
    script_id: UUID
    title: str
    status: str
    source_song: str
    related_scene: str
    lyrics_text: str
    music_structure: str
    adaptation_goal: str
    singing_roles: str
    rewrite_intensity: str
    content: SongAdaptationContent | None
    edited_content: SongAdaptationContent | None
    raw_model_info: dict | None
    created_at: datetime
    updated_at: datetime


class SongAdaptationSummaryResponse(BaseModel):
    """唱段适配列表摘要响应。"""

    id: UUID
    project_id: UUID
    script_id: UUID
    title: str
    status: str
    related_scene: str
    source_song: str
    provider: str | None
    model: str | None
    reasoning_level: str | None = None
    created_at: datetime
    updated_at: datetime


class SongAdaptationUpdateRequest(BaseModel):
    """保存音乐负责人或编导编辑后的唱段适配。"""

    edited_content: SongAdaptationContent


class MusicalFusionGenerateRequest(BaseModel):
    """M04 歌舞融合结构建议生成请求。"""

    script_id: UUID = Field(..., description="要引用的歌舞剧剧本 ID")
    source_mode: Literal["song_adaptation", "manual"] = Field(
        "song_adaptation",
        description="唱段来源：引用已保存 M03，或手工填写音乐段落",
    )
    song_adaptation_id: UUID | None = Field(None, description="引用的 M03 唱段适配 ID")
    related_scene: str = Field(..., min_length=1, max_length=240, description="本次歌舞融合覆盖的剧情段落")
    manual_music_title: str = Field("", max_length=200, description="手工模式下的音乐名称或来源")
    manual_music_structure: str = Field("", max_length=5000, description="手工整理的音乐段落表")
    manual_lyrics_summary: str = Field("", max_length=4000, description="手工模式下的歌词或唱段摘要")
    actor_count: int = Field(..., ge=1, le=120, description="参与本段排演的演员人数")
    stage_space: str = Field(..., min_length=1, max_length=1200, description="教室、小舞台等实际场地条件")
    fusion_goal: str = Field(..., min_length=2, max_length=1200, description="剧情、演唱和舞蹈的融合目标")
    additional_constraints: str = Field("", max_length=1600, description="年龄、安全、道具和排练时长等限制")
    llm_provider: Literal["deepseek", "qwen"] | None = Field(None, description="大模型供应商")
    llm_model: str | None = Field(None, min_length=1, max_length=120, description="本次生成使用的模型")
    reasoning_level: Literal["off", "standard", "enhanced"] | None = Field(None, description="本次生成使用的推理强度")

    @model_validator(mode="after")
    def validate_source_fields(self) -> Self:
        """确保 M03 和手工来源互斥，避免生成快照来源不明确。"""

        manual_values = [self.manual_music_title, self.manual_music_structure, self.manual_lyrics_summary]
        if self.source_mode == "song_adaptation":
            if self.song_adaptation_id is None:
                raise ValueError("引用 M03 时必须提供 song_adaptation_id。")
            if any(value.strip() for value in manual_values):
                raise ValueError("引用 M03 时不能同时填写手工音乐段落字段。")
        else:
            if self.song_adaptation_id is not None:
                raise ValueError("手工模式不能同时提供 song_adaptation_id。")
            if not self.manual_music_structure.strip():
                raise ValueError("手工模式必须填写 manual_music_structure。")
        return self


class MusicalFusionGenerateResponse(BaseModel):
    """创建 M04 异步任务后的响应。"""

    task_id: UUID
    musical_fusion_plan_id: UUID
    status: str
    message: str


class MusicalFusionSegment(BaseModel):
    """歌舞融合结构表中的一个可排练段落。"""

    segment_no: str = Field(..., min_length=1, max_length=40)
    story_content: str = Field(..., min_length=1, max_length=1600)
    music_position: str = Field(..., min_length=1, max_length=240)
    singing_mode: str = Field(..., min_length=1, max_length=240)
    singing_roles: list[NonEmptyText] = Field(..., min_length=1)
    dance_form: str = Field(..., min_length=1, max_length=1200)
    formation_suggestion: str = Field(..., min_length=1, max_length=1200)
    emotion: str = Field(..., min_length=1, max_length=240)
    song_dance_relationship: str = Field(..., min_length=1, max_length=1600)
    transition_note: str = Field(..., min_length=1, max_length=1600)
    rehearsal_tip: str = Field(..., min_length=1, max_length=1600)
    safety_note: str = Field(..., min_length=1, max_length=1200)
    is_highlight: bool


class MusicalFusionContent(BaseModel):
    """M04 结构化歌舞融合建议正文。"""

    title: str = Field(..., min_length=1, max_length=200)
    related_scene: str = Field(..., min_length=1, max_length=240)
    fusion_goal: str = Field(..., min_length=2, max_length=1200)
    stage_space: str = Field(..., min_length=1, max_length=1200)
    actor_count: int = Field(..., ge=1, le=120)
    overall_design: str = Field(..., min_length=1, max_length=2400)
    segments: list[MusicalFusionSegment] = Field(..., min_length=2)
    highlight_summary: str = Field(..., min_length=1, max_length=1600)
    rehearsal_notes: list[NonEmptyText] = Field(..., min_length=1)
    director_review_notes: list[NonEmptyText] = Field(..., min_length=1)

    @model_validator(mode="after")
    def ensure_highlight_segment(self) -> Self:
        """验收要求至少标记一个高潮或重点段落。"""

        if not any(segment.is_highlight for segment in self.segments):
            raise ValueError("歌舞融合结果必须至少标记一个高潮段落。")
        return self


class MusicalFusionPlanResponse(BaseModel):
    """歌舞融合方案详情响应。"""

    id: UUID
    project_id: UUID
    script_id: UUID
    song_adaptation_id: UUID | None
    title: str
    status: str
    source_mode: str
    music_title: str
    related_scene: str
    manual_music_structure: str
    manual_lyrics_summary: str
    actor_count: int
    stage_space: str
    fusion_goal: str
    additional_constraints: str
    content: MusicalFusionContent | None
    edited_content: MusicalFusionContent | None
    raw_model_info: dict | None
    created_at: datetime
    updated_at: datetime


class MusicalFusionPlanSummaryResponse(BaseModel):
    """歌舞融合方案列表摘要。"""

    id: UUID
    project_id: UUID
    script_id: UUID
    song_adaptation_id: UUID | None
    title: str
    status: str
    source_mode: str
    music_title: str
    related_scene: str
    provider: str | None
    model: str | None
    reasoning_level: str | None = None
    created_at: datetime
    updated_at: datetime


class MusicalFusionPlanUpdateRequest(BaseModel):
    """保存编导编辑后的歌舞融合方案。"""

    edited_content: MusicalFusionContent


class RoleTrainingGenerateRequest(BaseModel):
    """M05 分角色训练计划生成请求。"""

    script_id: UUID = Field(..., description="要引用的剧本 ID")
    fusion_plan_id: UUID | None = Field(None, description="可选的 M04 歌舞融合方案 ID")
    rehearsal_days: int = Field(..., ge=1, le=60, description="排练周期，单位天")
    session_minutes: int = Field(..., ge=10, le=240, description="每次排练时长，单位分钟")
    training_focus: str = Field(..., min_length=1, max_length=1200, description="训练重点，例如：台词、唱段、舞蹈、走位")
    notes: str = Field("", max_length=1200, description="补充说明或排练限制")
    llm_provider: Literal["deepseek", "qwen"] | None = Field(None, description="大模型供应商")
    llm_model: str | None = Field(None, min_length=1, max_length=120, description="本次生成使用的模型")
    reasoning_level: Literal["off", "standard", "enhanced"] | None = Field(None, description="本次生成使用的推理强度")


class RoleTrainingGenerateResponse(BaseModel):
    """创建分角色训练计划任务后的响应。"""

    task_id: UUID
    role_training_plan_id: UUID
    status: str
    message: str


class RoleDailyPlan(BaseModel):
    """某一天的排练安排。"""

    day: str
    focus: str
    tasks: list[str]
    expected_result: str


class RoleTrainingItem(BaseModel):
    """单个角色的训练任务。"""

    role_name: str
    role_type: str
    line_focus: str
    singing_focus: str
    dance_focus: str
    blocking_tips: str
    daily_tasks: list[str]
    teacher_checkpoints: list[str]


class RoleTrainingContent(BaseModel):
    """M05 结构化分角色训练计划正文。"""

    title: str
    project_overview: str
    role_tasks: list[RoleTrainingItem]
    daily_plan: list[RoleDailyPlan]
    teacher_checkpoints: list[str]


class RoleTrainingPlanResponse(BaseModel):
    """分角色训练计划详情响应。"""

    id: UUID
    project_id: UUID
    script_id: UUID
    title: str
    status: str
    rehearsal_days: int
    session_minutes: int
    training_focus: str
    notes: str
    content: RoleTrainingContent | None
    edited_content: RoleTrainingContent | None
    raw_model_info: dict | None
    created_at: datetime
    updated_at: datetime


class RoleTrainingPlanSummaryResponse(BaseModel):
    """分角色训练计划列表摘要响应。"""

    id: UUID
    project_id: UUID
    script_id: UUID
    title: str
    status: str
    provider: str | None
    model: str | None
    reasoning_level: str | None = None
    created_at: datetime
    updated_at: datetime


class RoleTrainingPlanUpdateRequest(BaseModel):
    """保存老师编辑后的分角色训练计划。"""

    edited_content: RoleTrainingContent
