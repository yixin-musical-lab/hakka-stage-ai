from pydantic import BaseModel, Field


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
