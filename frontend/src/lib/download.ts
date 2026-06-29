import { fetchLessonPlanMarkdown, fetchMovementGuideMarkdown, fetchMusicalScriptMarkdown, fetchRoleTrainingMarkdown } from "./api";

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

export async function downloadMovementGuideMarkdown(movementGuideId: string, title: string) {
  const markdown = await fetchMovementGuideMarkdown(movementGuideId);
  saveMarkdown(markdown, title, "movement-guide");
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
