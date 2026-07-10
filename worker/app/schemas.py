from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)]


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
    """大模型必须返回的结构化教案正文。"""

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
    """M01 大模型必须返回的结构化剧本正文。"""

    title: str
    synopsis: str
    acts: list[ScriptAct]
    characters: list[ScriptCharacter]
    performance_slots: list[PerformanceSlot]
    director_notes: list[str]


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
    """M03-lite 大模型必须返回的结构化唱段适配正文。"""

    title: str
    source_song: str
    related_scene: str
    adaptation_goal: str
    sections: list[SongSection]
    dance_interludes: list[DanceInterlude]
    review_notes: list[str]


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
    """M05 大模型必须返回的结构化分角色训练计划正文。"""

    title: str
    project_overview: str
    role_tasks: list[RoleTrainingItem]
    daily_plan: list[RoleDailyPlan]
    teacher_checkpoints: list[str]


class TeacherScriptStep(BaseModel):
    """老师可以在课堂现场逐项照着执行的一个步骤。"""

    step_no: int = Field(ge=1)
    name: str = Field(min_length=1)
    duration_hint: str = Field(min_length=1)
    teacher_action: str = Field(min_length=1)
    teacher_cue: str = Field(min_length=1)
    student_action: str = Field(min_length=1)


class ClassInteractionContent(BaseModel):
    """T05 大模型必须返回的结构化课堂互动方案。"""

    title: str = Field(min_length=1)
    teaching_phase: Literal["开场", "热身", "动作学习", "分组展示", "收束"]
    interaction_goal: str = Field(min_length=2)
    duration_minutes: int = Field(ge=1, le=45)
    space_materials: str = Field(min_length=1)
    game_rules: list[NonEmptyText] = Field(min_length=1)
    teacher_script: list[TeacherScriptStep] = Field(min_length=1)
    command_phrases: list[NonEmptyText] = Field(min_length=1)
    student_actions: list[NonEmptyText] = Field(min_length=1)
    grouping_method: str = Field(min_length=1)
    encouragement_phrases: list[NonEmptyText] = Field(min_length=1)
    safety_notes: list[NonEmptyText] = Field(min_length=1)
    variations: list[NonEmptyText] = Field(min_length=1)
    teacher_check_notes: list[NonEmptyText] = Field(min_length=1)
