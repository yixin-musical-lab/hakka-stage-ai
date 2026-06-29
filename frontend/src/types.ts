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

export type ScriptDialogueLine = {
  role_name: string;
  line: string;
  stage_direction: string;
};

export type ScriptAct = {
  name: string;
  duration_minutes: number;
  story_outline: string;
  emotion: string;
  narrator_text: string;
  dialogues: ScriptDialogueLine[];
};

export type ScriptCharacter = {
  name: string;
  role_type: string;
  personality: string;
  character_arc: string;
  performance_tips: string;
  key_lines: string[];
};

export type PerformanceSlot = {
  act_name: string;
  slot_type: string;
  description: string;
  suggested_duration: string;
  notes: string;
};

export type MusicalScriptContent = {
  title: string;
  synopsis: string;
  acts: ScriptAct[];
  characters: ScriptCharacter[];
  performance_slots: PerformanceSlot[];
  director_notes: string[];
};

export type MusicalScriptForm = {
  theme: string;
  duration_minutes: number;
  actor_count: number;
  age_group: string;
  style_requirements: string;
  required_elements: string;
  forbidden_content: string;
  llm_provider: "deepseek" | "qwen";
  llm_model: string;
  reasoning_level: "off" | "standard" | "enhanced";
};

export type MusicalScriptResponse = {
  id: string;
  project_id: string;
  title: string;
  status: string;
  content: MusicalScriptContent | null;
  edited_content: MusicalScriptContent | null;
  raw_model_info: Record<string, unknown> | null;
};

export type MusicalScriptSummary = {
  id: string;
  project_id: string;
  title: string;
  status: string;
  provider: string | null;
  model: string | null;
  reasoning_level: string | null;
  created_at: string;
  updated_at: string;
};

export type RoleDailyPlan = {
  day: string;
  focus: string;
  tasks: string[];
  expected_result: string;
};

export type RoleTrainingItem = {
  role_name: string;
  role_type: string;
  line_focus: string;
  singing_focus: string;
  dance_focus: string;
  blocking_tips: string;
  daily_tasks: string[];
  teacher_checkpoints: string[];
};

export type RoleTrainingContent = {
  title: string;
  project_overview: string;
  role_tasks: RoleTrainingItem[];
  daily_plan: RoleDailyPlan[];
  teacher_checkpoints: string[];
};

export type RoleTrainingForm = {
  script_id: string;
  rehearsal_days: number;
  session_minutes: number;
  training_focus: string;
  notes: string;
  llm_provider: "deepseek" | "qwen";
  llm_model: string;
  reasoning_level: "off" | "standard" | "enhanced";
};

export type RoleTrainingPlanResponse = {
  id: string;
  project_id: string;
  script_id: string;
  title: string;
  status: string;
  rehearsal_days: number;
  session_minutes: number;
  training_focus: string;
  notes: string;
  content: RoleTrainingContent | null;
  edited_content: RoleTrainingContent | null;
  raw_model_info: Record<string, unknown> | null;
};

export type RoleTrainingPlanSummary = {
  id: string;
  project_id: string;
  script_id: string;
  title: string;
  status: string;
  provider: string | null;
  model: string | null;
  reasoning_level: string | null;
  created_at: string;
  updated_at: string;
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
