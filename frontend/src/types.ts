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

export type AccountRole = "teacher" | "student";

export type UserAccount = {
  id: string;
  email: string;
  display_name: string;
  role: AccountRole;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AuthSession = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: UserAccount;
};

export type LoginForm = {
  email: string;
  password: string;
};

export type AccountCreateForm = LoginForm & {
  display_name: string;
  role: AccountRole;
};

export type BatchAccountCreateResponse = {
  created_count: number;
  users: UserAccount[];
};

export type WorkspaceLatestItem = {
  id: string;
  title: string;
  status: string;
  updated_at: string;
};

export type WorkspaceModuleOverview = {
  count: number;
  latest: WorkspaceLatestItem | null;
};

/** 首页轻量概览；只包含统计和最新摘要，不携带业务正文。 */
export type WorkspaceOverviewResponse = {
  lesson_plans: WorkspaceModuleOverview;
  class_interactions: WorkspaceModuleOverview;
  musical_scripts: WorkspaceModuleOverview;
  song_adaptations: WorkspaceModuleOverview;
  musical_fusion_plans: WorkspaceModuleOverview;
  role_training_plans: WorkspaceModuleOverview;
  movement_guides: WorkspaceModuleOverview;
  practice_submissions: WorkspaceModuleOverview;
  rehearsal_reviews: WorkspaceModuleOverview;
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

export type LessonPlanVariantType = "younger" | "basic" | "advanced" | "performance";

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
  applicable_audience: string | null;
  adjustment_summary: string[];
};

export type LessonPlanVariantInfo = {
  source_lesson_plan_id: string | null;
  source_title_snapshot: string;
  source_content_snapshot: LessonPlanContent;
  variant_type: LessonPlanVariantType;
  adjustment_direction: string;
};

export type LessonPlanResponse = {
  id: string;
  course_id: string;
  title: string;
  status: string;
  content: LessonPlanContent | null;
  edited_content: LessonPlanContent | null;
  raw_model_info: Record<string, unknown> | null;
  variant_info: LessonPlanVariantInfo | null;
  created_at: string;
  updated_at: string;
};

export type LessonPlanSummary = {
  id: string;
  course_id: string;
  title: string;
  status: string;
  provider: string | null;
  model: string | null;
  reasoning_level: string | null;
  source_lesson_plan_id: string | null;
  variant_type: LessonPlanVariantType | null;
  source_title_snapshot: string | null;
  created_at: string;
  updated_at: string;
};

export type LessonPlanVariantForm = {
  variant_type: LessonPlanVariantType;
  adjustment_direction: string;
  llm_provider: "deepseek" | "qwen";
  llm_model: string;
  reasoning_level: "off" | "standard" | "enhanced";
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

export type TeachingPhase = "开场" | "热身" | "动作学习" | "分组展示" | "收束";

export type TeacherScriptStep = {
  step_no: number;
  name: string;
  duration_hint: string;
  teacher_action: string;
  teacher_cue: string;
  student_action: string;
};

export type ClassInteractionContent = {
  title: string;
  teaching_phase: TeachingPhase;
  interaction_goal: string;
  duration_minutes: number;
  space_materials: string;
  game_rules: string[];
  teacher_script: TeacherScriptStep[];
  command_phrases: string[];
  student_actions: string[];
  grouping_method: string;
  encouragement_phrases: string[];
  safety_notes: string[];
  variations: string[];
  teacher_check_notes: string[];
};

export type ClassInteractionForm = {
  course_theme: string;
  age_group: string;
  teaching_phase: TeachingPhase;
  interaction_goal: string;
  class_style: string;
  duration_minutes: number;
  student_count: number;
  space_materials: string;
  lesson_context: string;
  source_lesson_plan_id: string | null;
  llm_provider: "deepseek" | "qwen";
  llm_model: string;
  reasoning_level: "off" | "standard" | "enhanced";
};

export type ClassInteractionResponse = {
  id: string;
  source_lesson_plan_id: string | null;
  title: string;
  status: string;
  course_theme: string;
  age_group: string;
  teaching_phase: TeachingPhase;
  interaction_goal: string;
  class_style: string;
  duration_minutes: number;
  student_count: number;
  space_materials: string;
  lesson_context: string;
  content: ClassInteractionContent | null;
  edited_content: ClassInteractionContent | null;
  raw_model_info: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type ClassInteractionSummary = {
  id: string;
  source_lesson_plan_id: string | null;
  title: string;
  status: string;
  course_theme: string;
  teaching_phase: TeachingPhase;
  duration_minutes: number;
  provider: string | null;
  model: string | null;
  reasoning_level: string | null;
  created_at: string;
  updated_at: string;
};

export type LessonInteractionPrefill = {
  source_lesson_plan_id: string;
  source_lesson_plan_title: string;
  source_variant_type: LessonPlanVariantType | null;
  course_theme: string;
  age_group: string;
  student_count: number;
  class_style: string;
  space_materials: string;
  lesson_context: string;
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

export type MusicalFusionSourceMode = "song_adaptation" | "manual";

export type MusicalFusionSegment = {
  segment_no: string;
  story_content: string;
  music_position: string;
  singing_mode: string;
  singing_roles: string[];
  dance_form: string;
  formation_suggestion: string;
  emotion: string;
  song_dance_relationship: string;
  transition_note: string;
  rehearsal_tip: string;
  safety_note: string;
  is_highlight: boolean;
};

export type MusicalFusionContent = {
  title: string;
  related_scene: string;
  fusion_goal: string;
  stage_space: string;
  actor_count: number;
  overall_design: string;
  segments: MusicalFusionSegment[];
  highlight_summary: string;
  rehearsal_notes: string[];
  director_review_notes: string[];
};

export type MusicalFusionForm = {
  script_id: string;
  source_mode: MusicalFusionSourceMode;
  song_adaptation_id: string | null;
  related_scene: string;
  manual_music_title: string;
  manual_music_structure: string;
  manual_lyrics_summary: string;
  actor_count: number;
  stage_space: string;
  fusion_goal: string;
  additional_constraints: string;
  llm_provider: "deepseek" | "qwen";
  llm_model: string;
  reasoning_level: "off" | "standard" | "enhanced";
};

export type MusicalFusionPlanResponse = {
  id: string;
  project_id: string;
  script_id: string;
  song_adaptation_id: string | null;
  title: string;
  status: string;
  source_mode: MusicalFusionSourceMode;
  music_title: string;
  related_scene: string;
  manual_music_structure: string;
  manual_lyrics_summary: string;
  actor_count: number;
  stage_space: string;
  fusion_goal: string;
  additional_constraints: string;
  content: MusicalFusionContent | null;
  edited_content: MusicalFusionContent | null;
  raw_model_info: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type MusicalFusionPlanSummary = {
  id: string;
  project_id: string;
  script_id: string;
  song_adaptation_id: string | null;
  title: string;
  status: string;
  source_mode: MusicalFusionSourceMode;
  music_title: string;
  related_scene: string;
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
  fusion_plan_id: string | null;
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

export type RehearsalReviewEventType = "rehearsal" | "performance";

export type RehearsalReviewForm = {
  script_id: string;
  fusion_plan_id: string | null;
  role_training_plan_id: string | null;
  event_type: RehearsalReviewEventType;
  event_date: string;
  rehearsal_content: string;
  observation_notes: string;
  strengths: string;
  issues: string;
  review_focus: string[];
  next_goal: string;
  video_object_key: string;
  video_original_file_name: string;
  video_content_type: string;
  video_size_bytes: number | null;
  video_notes: string;
  llm_provider: "deepseek" | "qwen";
  llm_model: string;
  reasoning_level: "off" | "standard" | "enhanced";
};

export type RehearsalVideoUploadResponse = {
  object_key: string;
  original_file_name: string;
  content_type: string;
  size_bytes: number;
  storage_mode: "minio";
};

export type RehearsalIssue = {
  category: string;
  observation: string;
  possible_cause: string;
  improvement_action: string;
  priority: "high" | "medium" | "low";
  next_check: string;
};

export type RehearsalRoleSuggestion = {
  role_name: string;
  observation: string;
  suggestion: string;
  next_tasks: string[];
};

export type NextRehearsalPlan = {
  goal: string;
  focus_items: string[];
  action_steps: string[];
  teacher_checkpoints: string[];
};

export type ReusableReviewTemplate = {
  template_title: string;
  review_focus: string[];
  observation_prompts: string[];
  closing_checklist: string[];
};

export type RehearsalReviewContent = {
  title: string;
  overview: string;
  highlights: string[];
  issues: RehearsalIssue[];
  role_suggestions: RehearsalRoleSuggestion[];
  singing_and_rhythm_advice: string;
  dance_and_formation_advice: string;
  performance_and_blocking_advice: string;
  next_rehearsal_plan: NextRehearsalPlan;
  teaching_reflection: string;
  reusable_template: ReusableReviewTemplate;
  reviewer_notes: string[];
  boundary_note: string;
};

export type RehearsalReviewResponse = {
  id: string;
  project_id: string;
  script_id: string;
  fusion_plan_id: string | null;
  role_training_plan_id: string | null;
  title: string;
  status: string;
  event_type: RehearsalReviewEventType;
  event_date: string;
  rehearsal_content: string;
  observation_notes: string;
  strengths: string;
  issues: string;
  review_focus: string[];
  next_goal: string;
  has_video_attachment: boolean;
  video_original_file_name: string;
  video_content_type: string;
  video_size_bytes: number | null;
  video_notes: string;
  content: RehearsalReviewContent | null;
  edited_content: RehearsalReviewContent | null;
  raw_model_info: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type RehearsalReviewSummary = {
  id: string;
  project_id: string;
  script_id: string;
  fusion_plan_id: string | null;
  role_training_plan_id: string | null;
  title: string;
  status: string;
  event_type: RehearsalReviewEventType;
  event_date: string;
  has_video_attachment: boolean;
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
