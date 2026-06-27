import type { LessonPlanForm } from "../types";

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
  "剧本创编",
  "分角色训练",
  "排练复盘",
];
