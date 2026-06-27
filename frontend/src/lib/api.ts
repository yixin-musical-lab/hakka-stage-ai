import { apiBaseUrl } from "./config";
import type {
  AiTaskResponse,
  HealthResponse,
  LessonPlanContent,
  LessonPlanForm,
  LessonPlanResponse,
  LessonPlanSummary,
  LlmOptionsResponse,
} from "../types";

export async function fetchHealth(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/health`, { signal });
  if (!response.ok) {
    throw new Error(`后端返回异常状态码：${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}

export async function createLessonPlanTask(form: LessonPlanForm) {
  const response = await fetch(`${apiBaseUrl}/api/lesson-plans/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as { task_id: string; lesson_plan_id: string; status: string };
}

export async function fetchLlmOptions(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/llm-options`, { signal });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as LlmOptionsResponse;
}

export async function fetchAiTask(taskId: string) {
  const response = await fetch(`${apiBaseUrl}/api/ai-tasks/${taskId}`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as AiTaskResponse;
}

export async function fetchLessonPlans(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/lesson-plans`, { signal });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as LessonPlanSummary[];
}

export async function fetchLessonPlan(lessonPlanId: string) {
  const response = await fetch(`${apiBaseUrl}/api/lesson-plans/${lessonPlanId}`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as LessonPlanResponse;
}

export async function updateLessonPlan(lessonPlanId: string, editedContent: LessonPlanContent) {
  const response = await fetch(`${apiBaseUrl}/api/lesson-plans/${lessonPlanId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ edited_content: editedContent }),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as LessonPlanResponse;
}

export async function deleteLessonPlan(lessonPlanId: string) {
  const response = await fetch(`${apiBaseUrl}/api/lesson-plans/${lessonPlanId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
}

export async function fetchLessonPlanMarkdown(lessonPlanId: string) {
  const response = await fetch(`${apiBaseUrl}/api/lesson-plans/${lessonPlanId}/markdown`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return response.text();
}

async function readApiError(response: Response) {
  try {
    const data = (await response.json()) as { detail?: string };
    return data.detail ?? `请求失败：${response.status}`;
  } catch {
    return `请求失败：${response.status}`;
  }
}
