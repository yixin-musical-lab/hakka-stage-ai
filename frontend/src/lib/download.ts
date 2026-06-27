import { fetchLessonPlanMarkdown } from "./api";

export async function downloadMarkdown(lessonPlanId: string, title: string) {
  const markdown = await fetchLessonPlanMarkdown(lessonPlanId);
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${safeFileName(title)}.md`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function safeFileName(title: string) {
  const normalized = title.trim().replace(/[\\/:*?"<>|]/g, "-").replace(/\s+/g, "-");
  return normalized || "lesson-plan";
}
