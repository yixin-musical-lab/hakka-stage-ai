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

export type SongAdaptationRewriteIntensity = "structure_only" | "light_rewrite" | "strong_rewrite";

export type SongSection = {
  section_no: string;
  music_position: string;
  original_lyrics: string;
  adapted_lyrics: string;
  singing_mode: string;
  suggested_roles: string[];
  emotion: string;
  dance_opportunity: string;
  transition_note: string;
};

export type DanceInterlude = {
  music_position: string;
  suggestion: string;
};

export type SongAdaptationContent = {
  title: string;
  source_song: string;
  related_scene: string;
  adaptation_goal: string;
  sections: SongSection[];
  dance_interludes: DanceInterlude[];
  review_notes: string[];
};

export type SongAdaptationForm = {
  script_id: string;
  related_scene: string;
  source_song: string;
  lyrics_text: string;
  music_structure: string;
  adaptation_goal: string;
  singing_roles: string;
  rewrite_intensity: SongAdaptationRewriteIntensity;
  llm_provider: "deepseek" | "qwen";
  llm_model: string;
  reasoning_level: "off" | "standard" | "enhanced";
};

export type SongAdaptationResponse = {
  id: string;
  project_id: string;
  script_id: string;
  title: string;
  status: string;
  source_song: string;
  related_scene: string;
  lyrics_text: string;
  music_structure: string;
  adaptation_goal: string;
  singing_roles: string;
  rewrite_intensity: SongAdaptationRewriteIntensity;
  content: SongAdaptationContent | null;
  edited_content: SongAdaptationContent | null;
  raw_model_info: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type SongAdaptationSummary = {
  id: string;
  project_id: string;
  script_id: string;
  title: string;
  status: string;
  related_scene: string;
  source_song: string;
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

export type MovementAssetType =
  | "reference_video"
  | "skeleton_preview"
  | "confirmed_skeleton"
  | "digital_human_video"
  | "courseware_video"
  | "image";

export type MovementAssetStatus = "draft" | "candidate" | "confirmed" | "rejected";

export type MovementStepDetail = {
  name: string;
  beats: string;
  description: string;
  teacher_cue: string;
};

export type MovementMediaAsset = {
  asset_type: MovementAssetType;
  title: string;
  url: string;
  status: MovementAssetStatus;
  notes: string;
};

export type MovementGuideContent = {
  title: string;
  action_name: string;
  action_description: string;
  course_context: string;
  beats: string;
  body_direction: string;
  difficulty: string;
  normalized_motion_script: string;
  breakdown_steps: MovementStepDetail[];
  rhythm_tips: string[];
  common_mistakes: string[];
  correction_cues: string[];
  teaching_tips: string[];
  media_assets: MovementMediaAsset[];
  teacher_review_notes: string;
};

export type MovementGuideForm = {
  action_name: string;
  action_description: string;
  course_context: string;
  beats: string;
  body_direction: string;
  difficulty: string;
  teaching_tips: string;
  reference_video_url: string;
  digital_human_image_url: string;
};

export type MovementGuideResponse = {
  id: string;
  title: string;
  action_name: string;
  action_description: string;
  course_context: string;
  beats: string;
  body_direction: string;
  difficulty: string;
  teaching_tips: string;
  reference_video_url: string;
  digital_human_image_url: string;
  status: string;
  content: MovementGuideContent | null;
  edited_content: MovementGuideContent | null;
  raw_pipeline_info: Record<string, unknown> | null;
};

export type MovementGuideSummary = {
  id: string;
  title: string;
  action_name: string;
  course_context: string;
  status: string;
  asset_count: number;
  confirmed_asset_count: number;
  created_at: string;
  updated_at: string;
};

export type PracticeSubmissionForm = {
  course_title: string;
  task_title: string;
  task_description: string;
  student_name: string;
  student_group: string;
  video_url: string;
  video_file_name: string;
  video_duration_seconds: number | null;
  video_notes: string;
  reference_action_name: string;
  reference_video_url: string;
  evaluation_focus: string[];
};

export type PracticeVideoUploadResponse = {
  url: string;
  original_file_name: string;
  stored_file_name: string;
  content_type: string;
  size_bytes: number;
  storage_mode: "local_dev";
};

export type PracticeSubmissionSummary = {
  id: string;
  course_title: string;
  task_title: string;
  student_name: string;
  student_group: string;
  status: string;
  report_status: string | null;
  analysis_mode: string | null;
  created_at: string;
  updated_at: string;
};

export type PracticeIssuePoint = {
  category: string;
  description: string;
  suggestion: string;
};

export type PracticeReportContent = {
  title: string;
  observation_mode: "basic_observation" | "reference_comparison_pending" | "reference_comparison";
  summary: string;
  video_basic_info: string[];
  shooting_quality_feedback: string[];
  rhythm_and_completion_observations: string[];
  posture_and_stability_observations: string[];
  structured_issue_points: PracticeIssuePoint[];
  ai_suggestions: string[];
  teacher_review_points: string[];
  next_practice_tasks: string[];
  teacher_final_comment: string;
  boundary_note: string;
};

export type PracticeReportResponse = {
  id: string;
  submission_id: string;
  title: string;
  status: string;
  analysis_mode: string;
  content: PracticeReportContent | null;
  edited_content: PracticeReportContent | null;
  teacher_feedback: string;
  reviewed_by: string;
  reviewed_at: string | null;
  raw_analysis_info: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type PracticeSubmissionDetail = {
  id: string;
  course_title: string;
  task_title: string;
  task_description: string;
  student_name: string;
  student_group: string;
  video_url: string;
  video_file_name: string;
  video_duration_seconds: number | null;
  video_notes: string;
  reference_action_name: string;
  reference_video_url: string;
  evaluation_focus: string[];
  status: string;
  report: PracticeReportResponse | null;
  created_at: string;
  updated_at: string;
};

export type PracticeAnalyzeResponse = {
  task_id: string;
  submission_id: string;
  report_id: string;
  status: "SUCCESS";
  message: string;
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
