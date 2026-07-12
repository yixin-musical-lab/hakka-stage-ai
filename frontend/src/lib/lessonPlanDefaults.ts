import type {
  ClassInteractionForm,
  LessonPlanForm,
  MovementGuideForm,
  MusicalFusionForm,
  MusicalScriptContent,
  MusicalScriptForm,
  PracticeSubmissionForm,
  RoleTrainingForm,
  SongAdaptationForm,
} from "../types";

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
  "曲目队形编排",
  "排练复盘",
];

export const initialClassInteractionForm: ClassInteractionForm = {
  course_theme: "客家山歌节奏体验",
  age_group: "8-12 岁",
  teaching_phase: "热身",
  interaction_goal: "帮助学生快速进入节奏状态，并通过动作接龙建立合作意识。",
  class_style: "活泼、协作、口令清楚",
  duration_minutes: 8,
  student_count: 24,
  space_materials: "清空教室中间区域，不使用额外道具；学生之间保持一臂距离。",
  lesson_context: "",
  source_lesson_plan_id: null,
  llm_provider: "deepseek",
  llm_model: "deepseek-v4-flash",
  reasoning_level: "standard",
};

export const initialMovementGuideForm: MovementGuideForm = {
  action_name: "双手打开转身",
  action_description: "双手从胸前打开，同时向右转身一圈，最后回到面向正前方的站位。",
  course_context: "客家山歌主题舞蹈体验课",
  beats: "4 拍完成，前 2 拍打开双手，后 2 拍向右转身。",
  body_direction: "面向正前方开始，向右转身一圈后回到正前方。",
  difficulty: "适合 8-12 岁零基础学生。",
  teaching_tips: "提醒学生先站稳重心，转身时眼睛找前方定点。",
  reference_video_url: "",
  digital_human_image_url: "",
};

export const initialPracticeSubmissionForm: PracticeSubmissionForm = {
  course_title: "客家山歌主题舞蹈体验课",
  task_title: "30 秒客家山歌律动打卡",
  task_description: "跟随课堂练习音乐完成一段 30 秒短组合，重点保持全身入镜和节奏稳定。",
  student_name: "演示学生",
  student_group: "第一组",
  video_url: "https://example.com/practice-demo.mp4",
  video_file_name: "演示学生_客家山歌律动_第1次.mp4",
  video_duration_seconds: 30,
  video_notes: "手机固定在桌面上拍摄，练习了两遍后提交。",
  reference_action_name: "双手打开转身",
  reference_video_url: "",
  evaluation_focus: ["拍摄质量", "节奏", "动作完整度", "动作稳定"],
};

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
  fusion_plan_id: null,
  rehearsal_days: 7,
  session_minutes: 60,
  training_focus: "台词、唱段、舞蹈、走位、群演同步和终场造型。",
  notes: "训练计划要区分主角、配角、旁白、群演、领舞和独唱；任务要短句、可执行。",
  llm_provider: "deepseek",
  llm_model: "deepseek-v4-flash",
  reasoning_level: "standard",
});

export const initialSongAdaptationForm = (scriptId: string): SongAdaptationForm => ({
  script_id: scriptId,
  related_scene: "第二幕：一起排练",
  source_song: "客家山歌类曲目",
  lyrics_text: "山歌唱出家乡路，清清风里有回声。\n大家一起唱，山歌响满堂。",
  music_structure: "0:00-0:18 前奏：旁白铺垫，动作轻。\n0:18-0:55 主歌一：独唱或主角领唱。\n0:55-1:25 副歌一：适合齐唱和群舞。\n1:25-1:45 间奏：适合队形变化。",
  adaptation_goal: "让唱段承接剧情，表现孩子们从好奇到一起唱响客家山歌的过程。",
  singing_roles: "主角、奶奶、旁白、全体、领舞",
  rewrite_intensity: "light_rewrite",
  llm_provider: "deepseek",
  llm_model: "deepseek-v4-flash",
  reasoning_level: "standard",
});

/**
 * 使用当前剧本确认稿为 M03 填充剧情和角色信息。
 * 独立生成页与其他入口共用该规则，避免默认值在不同页面逐渐漂移。
 */
export function buildSongAdaptationFormFromScript(
  scriptId: string,
  content: MusicalScriptContent | null,
): SongAdaptationForm {
  const form = initialSongAdaptationForm(scriptId);
  if (!content) {
    return form;
  }

  const firstAct = content.acts[0];
  const characterNames = content.characters.map((character) => character.name).join("、");
  return {
    ...form,
    related_scene: firstAct?.name ?? form.related_scene,
    adaptation_goal: firstAct
      ? `让唱段承接“${firstAct.name}”的剧情，表达${firstAct.emotion || "角色情绪"}，并为后续舞蹈留出清楚位置。`
      : form.adaptation_goal,
    singing_roles: characterNames || form.singing_roles,
  };
}

export const initialMusicalFusionForm = (
  scriptId: string,
  songAdaptationId: string | null = null,
): MusicalFusionForm => ({
  script_id: scriptId,
  source_mode: songAdaptationId ? "song_adaptation" : "manual",
  song_adaptation_id: songAdaptationId,
  related_scene: "第二幕：一起排练",
  manual_music_title: songAdaptationId ? "" : "客家山歌类曲目",
  manual_music_structure: songAdaptationId
    ? ""
    : "0:00-0:18 前奏：旁白铺垫。\n0:18-0:55 主歌：主角领唱。\n0:55-1:25 副歌：全员齐唱和群舞。\n1:25-1:45 间奏：队形变化。",
  manual_lyrics_summary: songAdaptationId ? "" : "主角从好奇到理解客家山歌，最后和全体演员一起齐唱。",
  actor_count: 12,
  stage_space: "普通教室或小舞台，表演区约 6 米 × 4 米，不使用升降设备。",
  fusion_goal: "让剧情从旁白铺垫自然进入主角领唱，再推进到全员齐唱和群舞高潮。",
  additional_constraints: "适合 8-12 岁学生；避免高难度跳跃、快速连续转圈和交叉奔跑。",
  llm_provider: "deepseek",
  llm_model: "deepseek-v4-flash",
  reasoning_level: "standard",
});
