import type { LessonPlanForm, MusicalScriptForm, RoleTrainingForm } from "../types";

export const initialLessonPlanForm: LessonPlanForm = {
  dance_style: "客家山歌舞",
  theme: "乡土美育主题",
  age_group: "8-12 岁",
  duration_minutes: 40,
  student_count: 12,
  teaching_goal: "让学生理解客家山歌的节奏特点，掌握一个适合舞台展示的基础组合，并能用身体动作表达乡土情感。",
  learning_level: "零基础到初级，有基础节奏模仿能力",
  course_style: "活泼、沉浸式、带舞台排练感",
  notes: "动作设计要安全，避免高难度跳跃；课堂语言适合少儿理解。",
  llm_provider: "deepseek",
  llm_model: "deepseek-v4-flash",
  reasoning_level: "standard",
};

export const futureModules = [
  "课堂互动",
  "示范材料",
  "课后练习",
  "排练复盘",
];

export const initialMusicalScriptForm: MusicalScriptForm = {
  theme: "客家山歌与乡土美育",
  duration_minutes: 10,
  actor_count: 12,
  age_group: "8-12 岁",
  style_requirements: "温暖、积极、适合校园展示，有客家文化气质但语言要适合小学生。",
  required_elements: "客家山歌、劳动场景、集体舞、奶奶讲故事、终场齐唱。",
  forbidden_content: "台词不能太长，动作不能太难，不要设计专业舞台设备才能完成的效果。",
  llm_provider: "deepseek",
  llm_model: "deepseek-v4-flash",
  reasoning_level: "standard",
};

export const initialRoleTrainingForm = (scriptId: string): RoleTrainingForm => ({
  script_id: scriptId,
  rehearsal_days: 7,
  session_minutes: 60,
  training_focus: "台词、唱段、舞蹈、走位、群演同步和终场造型。",
  notes: "训练计划要区分主角、配角、旁白、群演、领舞和独唱；任务要短句、可执行。",
  llm_provider: "deepseek",
  llm_model: "deepseek-v4-flash",
  reasoning_level: "standard",
});
