export type DependencyConfig = {
  name: string;
  configured: boolean;
  endpoint: string;
};

export type HealthResponse = {
  status: string;
  service: string;
  message: string;
  dependencies: DependencyConfig[];
};

export type LessonActivity = {
  name: string;
  duration_minutes: number;
  description: string;
};

export type MovementStep = {
  name: string;
  beats: string;
  teaching_tips: string;
};

export type LessonPlanContent = {
  title: string;
  course_overview: string;
  teaching_goals: string[];
  key_points: string[];
  common_mistakes: string[];
  warmup: LessonActivity[];
  main_teaching: LessonActivity[];
  movement_breakdown: MovementStep[];
  cooldown: LessonActivity[];
  homework: string[];
  teacher_notes: string[];
};

export type LessonPlanResponse = {
  id: string;
  course_id: string;
  title: string;
  status: string;
  content: LessonPlanContent | null;
  edited_content: LessonPlanContent | null;
  raw_model_info: Record<string, unknown> | null;
};

export type LessonPlanSummary = {
  id: string;
  course_id: string;
  title: string;
  status: string;
  provider: string | null;
  model: string | null;
  reasoning_level: string | null;
  created_at: string;
  updated_at: string;
};

export type AiTaskResponse = {
  id: string;
  task_type: string;
  status: "PENDING" | "RUNNING" | "SUCCESS" | "FAILED" | "CANCELLED";
  progress: number;
  result_id: string | null;
  error_code: string | null;
  error_message: string | null;
};

export type LessonPlanForm = {
  dance_style: string;
  theme: string;
  age_group: string;
  duration_minutes: number;
  student_count: number;
  teaching_goal: string;
  learning_level: string;
  course_style: string;
  notes: string;
  llm_provider: "deepseek" | "qwen";
  llm_model: string;
  reasoning_level: "off" | "standard" | "enhanced";
};

export type LlmModelOption = {
  id: string;
  label: string;
};

export type LlmProviderOption = {
  id: "deepseek" | "qwen";
  label: string;
  configured: boolean;
  models: LlmModelOption[];
};

export type ReasoningLevelOption = {
  id: "off" | "standard" | "enhanced";
  label: string;
  description: string;
};

export type LlmOptionsResponse = {
  default_provider: "deepseek" | "qwen";
  default_model: string;
  default_reasoning_level: "off" | "standard" | "enhanced";
  providers: LlmProviderOption[];
  reasoning_levels: ReasoningLevelOption[];
};
