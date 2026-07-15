import {
  fetchClassInteractionMarkdown,
  fetchLessonPlanMarkdown,
  fetchMovementGuideMarkdown,
  fetchMusicalFusionMarkdown,
  fetchMusicalScriptMarkdown,
  fetchPracticeReportMarkdown,
  fetchRehearsalReviewMarkdown,
  fetchRoleTrainingCardMarkdown,
  fetchRoleTrainingMarkdown,
  fetchSongAdaptationMarkdown,
} from "./api";

export async function downloadClassInteractionMarkdown(classInteractionId: string, title: string) {
  const markdown = await fetchClassInteractionMarkdown(classInteractionId);
  saveMarkdown(markdown, title, "class-interaction");
}

export async function downloadMarkdown(lessonPlanId: string, title: string) {
  const markdown = await fetchLessonPlanMarkdown(lessonPlanId);
  saveMarkdown(markdown, title, "lesson-plan");
}

export async function downloadMusicalScriptMarkdown(musicalScriptId: string, title: string) {
  const markdown = await fetchMusicalScriptMarkdown(musicalScriptId);
  saveMarkdown(markdown, title, "musical-script");
}

export async function downloadRoleTrainingMarkdown(roleTrainingPlanId: string, title: string) {
  const markdown = await fetchRoleTrainingMarkdown(roleTrainingPlanId);
  saveMarkdown(markdown, title, "role-training-plan");
}

export async function downloadRoleTrainingCardMarkdown(
  roleTrainingPlanId: string,
  roleIndex: number,
  planTitle: string,
  roleName: string,
) {
  const markdown = await fetchRoleTrainingCardMarkdown(roleTrainingPlanId, roleIndex);
  const resolvedRoleName = roleName.trim() || `角色${roleIndex + 1}`;
  saveMarkdown(markdown, `${planTitle}-${resolvedRoleName}-训练卡`, `role-training-card-${roleIndex + 1}`);
}

export async function downloadSongAdaptationMarkdown(songAdaptationId: string, title: string) {
  const markdown = await fetchSongAdaptationMarkdown(songAdaptationId);
  saveMarkdown(markdown, title, "song-adaptation");
}

export async function downloadMusicalFusionMarkdown(musicalFusionPlanId: string, title: string) {
  const markdown = await fetchMusicalFusionMarkdown(musicalFusionPlanId);
  saveMarkdown(markdown, title, "musical-fusion-plan");
}

export async function downloadMovementGuideMarkdown(movementGuideId: string, title: string) {
  const markdown = await fetchMovementGuideMarkdown(movementGuideId);
  saveMarkdown(markdown, title, "movement-guide");
}

export async function downloadPracticeReportMarkdown(reportId: string, title: string) {
  const markdown = await fetchPracticeReportMarkdown(reportId);
  saveMarkdown(markdown, title, "practice-report");
}

export async function downloadRehearsalReviewMarkdown(rehearsalReviewId: string, title: string) {
  const markdown = await fetchRehearsalReviewMarkdown(rehearsalReviewId);
  saveMarkdown(markdown, title, "rehearsal-review");
}

function saveMarkdown(markdown: string, title: string, fallbackName: string) {
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${safeFileName(title, fallbackName)}.md`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function safeFileName(title: string, fallbackName: string) {
  const normalized = title.trim().replace(/[\\/:*?"<>|]/g, "-").replace(/\s+/g, "-");
  return normalized || fallbackName;
}
