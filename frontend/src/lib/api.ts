import { apiBaseUrl } from "./config";
// 模块内统一把现有 fetch 指向鉴权封装，避免 60 余个业务请求逐个维护令牌请求头。
import { authenticatedFetch as fetch, getAccessToken } from "./authStorage";
import type {
  AiTaskResponse,
  ClassInteractionContent,
  ClassInteractionForm,
  ClassInteractionResponse,
  ClassInteractionSummary,
  HealthResponse,
  LessonInteractionPrefill,
  LessonPlanContent,
  LessonPlanForm,
  LessonPlanResponse,
  LessonPlanSummary,
  LessonPlanVariantForm,
  LlmOptionsResponse,
  MovementGuideContent,
  MovementGuideForm,
  MovementGuideResponse,
  MovementGuideSummary,
  MusicalFusionContent,
  MusicalFusionForm,
  MusicalFusionPlanResponse,
  MusicalFusionPlanSummary,
  MusicalScriptContent,
  MusicalScriptForm,
  MusicalScriptResponse,
  MusicalScriptSummary,
  PracticeAnalyzeResponse,
  PracticeReportContent,
  PracticeReportResponse,
  PracticeSubmissionDetail,
  PracticeSubmissionForm,
  PracticeSubmissionSummary,
  PracticeVideoUploadResponse,
  RehearsalReviewContent,
  RehearsalReviewForm,
  RehearsalReviewResponse,
  RehearsalReviewSummary,
  RehearsalVideoUploadResponse,
  RoleTrainingContent,
  RoleTrainingForm,
  RoleTrainingPlanResponse,
  RoleTrainingPlanSummary,
  SongAdaptationContent,
  SongAdaptationForm,
  SongAdaptationResponse,
  SongAdaptationSummary,
  VeoModelCode,
  VeoOptionsResponse,
  VeoResolution,
  VeoTaskResponse,
  WorkspaceOverviewResponse,
  MediaAsset,
  MediaGeneration,
  MediaProviderOptions,
  MediaWorkbenchConfig,
  MediaWorkbenchInputConfig,
  WorkflowOutputConfig,
  WorkflowParameterConfig,
  WorkflowTemplate,
  WorkflowVersion,
} from "../types";

/**
 * 判断请求失败是否由 AbortController 主动取消导致。
 *
 * React StrictMode 会在开发环境中额外执行一次 effect 清理；此时 fetch 可能抛出
 * DOMException，也可能由不同运行时包装为普通 Error，因此统一按错误名称识别。
 */
export function isAbortError(error: unknown): boolean {
  return (
    (error instanceof DOMException && error.name === "AbortError") ||
    (error instanceof Error && error.name === "AbortError")
  );
}

export async function fetchHealth(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/health`, { signal });
  if (!response.ok) {
    throw new Error(`后端返回异常状态码：${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}

export async function fetchWorkspaceOverview(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/workspace/overview`, { signal });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as WorkspaceOverviewResponse;
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

export async function createLessonPlanVariantTask(sourceLessonPlanId: string, form: LessonPlanVariantForm) {
  const response = await fetch(`${apiBaseUrl}/api/lesson-plans/${sourceLessonPlanId}/variants/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as { task_id: string; lesson_plan_id: string; status: string; message: string };
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

export async function fetchLessonPlanVariants(sourceLessonPlanId: string, signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/lesson-plans/${sourceLessonPlanId}/variants`, { signal });
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

export async function createClassInteractionTask(form: ClassInteractionForm) {
  const response = await fetch(`${apiBaseUrl}/api/interactions/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as { task_id: string; class_interaction_id: string; status: string };
}

export async function fetchClassInteractions(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/interactions`, { signal });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as ClassInteractionSummary[];
}

export async function fetchClassInteraction(classInteractionId: string) {
  const response = await fetch(`${apiBaseUrl}/api/interactions/${classInteractionId}`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as ClassInteractionResponse;
}

export async function updateClassInteraction(classInteractionId: string, editedContent: ClassInteractionContent) {
  const response = await fetch(`${apiBaseUrl}/api/interactions/${classInteractionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ edited_content: editedContent }),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as ClassInteractionResponse;
}

export async function deleteClassInteraction(classInteractionId: string) {
  const response = await fetch(`${apiBaseUrl}/api/interactions/${classInteractionId}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
}

export async function fetchClassInteractionMarkdown(classInteractionId: string) {
  const response = await fetch(`${apiBaseUrl}/api/interactions/${classInteractionId}/markdown`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return response.text();
}

export async function fetchLessonInteractionPrefill(lessonPlanId: string, signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/interactions/prefill-from-lesson/${lessonPlanId}`, { signal });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as LessonInteractionPrefill;
}

export async function createMusicalScriptTask(form: MusicalScriptForm) {
  const response = await fetch(`${apiBaseUrl}/api/musical-scripts/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as { task_id: string; musical_script_id: string; status: string };
}

export async function fetchMusicalScripts(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/musical-scripts`, { signal });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as MusicalScriptSummary[];
}

export async function fetchMusicalScript(musicalScriptId: string) {
  const response = await fetch(`${apiBaseUrl}/api/musical-scripts/${musicalScriptId}`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as MusicalScriptResponse;
}

export async function updateMusicalScript(musicalScriptId: string, editedContent: MusicalScriptContent) {
  const response = await fetch(`${apiBaseUrl}/api/musical-scripts/${musicalScriptId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ edited_content: editedContent }),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as MusicalScriptResponse;
}

export async function deleteMusicalScript(musicalScriptId: string) {
  const response = await fetch(`${apiBaseUrl}/api/musical-scripts/${musicalScriptId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
}

export async function fetchMusicalScriptMarkdown(musicalScriptId: string) {
  const response = await fetch(`${apiBaseUrl}/api/musical-scripts/${musicalScriptId}/markdown`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return response.text();
}

export async function createSongAdaptationTask(form: SongAdaptationForm) {
  const response = await fetch(`${apiBaseUrl}/api/song-adaptations/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as { task_id: string; song_adaptation_id: string; status: string };
}

export async function fetchSongAdaptations(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/song-adaptations`, { signal });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as SongAdaptationSummary[];
}

export async function fetchSongAdaptation(songAdaptationId: string) {
  const response = await fetch(`${apiBaseUrl}/api/song-adaptations/${songAdaptationId}`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as SongAdaptationResponse;
}

export async function updateSongAdaptation(songAdaptationId: string, editedContent: SongAdaptationContent) {
  const response = await fetch(`${apiBaseUrl}/api/song-adaptations/${songAdaptationId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ edited_content: editedContent }),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as SongAdaptationResponse;
}

export async function deleteSongAdaptation(songAdaptationId: string) {
  const response = await fetch(`${apiBaseUrl}/api/song-adaptations/${songAdaptationId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
}

export async function fetchSongAdaptationMarkdown(songAdaptationId: string) {
  const response = await fetch(`${apiBaseUrl}/api/song-adaptations/${songAdaptationId}/markdown`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return response.text();
}

export async function createMusicalFusionTask(form: MusicalFusionForm) {
  const response = await fetch(`${apiBaseUrl}/api/musical-fusion-plans/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as { task_id: string; musical_fusion_plan_id: string; status: string };
}

export async function fetchMusicalFusionPlans(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/musical-fusion-plans`, { signal });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as MusicalFusionPlanSummary[];
}

export async function fetchMusicalFusionPlan(musicalFusionPlanId: string) {
  const response = await fetch(`${apiBaseUrl}/api/musical-fusion-plans/${musicalFusionPlanId}`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as MusicalFusionPlanResponse;
}

export async function updateMusicalFusionPlan(musicalFusionPlanId: string, editedContent: MusicalFusionContent) {
  const response = await fetch(`${apiBaseUrl}/api/musical-fusion-plans/${musicalFusionPlanId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ edited_content: editedContent }),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as MusicalFusionPlanResponse;
}

export async function deleteMusicalFusionPlan(musicalFusionPlanId: string) {
  const response = await fetch(`${apiBaseUrl}/api/musical-fusion-plans/${musicalFusionPlanId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
}

export async function fetchMusicalFusionMarkdown(musicalFusionPlanId: string) {
  const response = await fetch(`${apiBaseUrl}/api/musical-fusion-plans/${musicalFusionPlanId}/markdown`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return response.text();
}

export async function createRoleTrainingTask(form: RoleTrainingForm) {
  const response = await fetch(`${apiBaseUrl}/api/role-training/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as { task_id: string; role_training_plan_id: string; status: string };
}

export async function fetchRoleTrainingPlans(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/role-training-plans`, { signal });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as RoleTrainingPlanSummary[];
}

export async function fetchRoleTrainingPlan(roleTrainingPlanId: string) {
  const response = await fetch(`${apiBaseUrl}/api/role-training-plans/${roleTrainingPlanId}`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as RoleTrainingPlanResponse;
}

export async function updateRoleTrainingPlan(roleTrainingPlanId: string, editedContent: RoleTrainingContent) {
  const response = await fetch(`${apiBaseUrl}/api/role-training-plans/${roleTrainingPlanId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ edited_content: editedContent }),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as RoleTrainingPlanResponse;
}

export async function deleteRoleTrainingPlan(roleTrainingPlanId: string) {
  const response = await fetch(`${apiBaseUrl}/api/role-training-plans/${roleTrainingPlanId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
}

export async function fetchRoleTrainingMarkdown(roleTrainingPlanId: string) {
  const response = await fetch(`${apiBaseUrl}/api/role-training-plans/${roleTrainingPlanId}/markdown`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return response.text();
}

export async function fetchRoleTrainingCardMarkdown(roleTrainingPlanId: string, roleIndex: number) {
  const response = await fetch(`${apiBaseUrl}/api/role-training-plans/${roleTrainingPlanId}/roles/${roleIndex}/markdown`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return response.text();
}

export function uploadRehearsalVideo(file: File, onProgress?: (percent: number) => void) {
  // Fetch 暂不提供稳定的上传进度事件，因此 M08 单文件上传使用浏览器原生 XHR。
  // 这只影响前端传输层，不改变后端 multipart 接口和 T06 现有上传实现。
  return new Promise<RehearsalVideoUploadResponse>((resolve, reject) => {
    const formData = new FormData();
    formData.append("file", file);
    const request = new XMLHttpRequest();
    request.open("POST", `${apiBaseUrl}/api/rehearsal-reviews/upload`);
    const accessToken = getAccessToken();
    if (accessToken) request.setRequestHeader("Authorization", `Bearer ${accessToken}`);
    request.withCredentials = true;
    request.responseType = "json";
    request.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) {
        onProgress?.(Math.min(99, Math.round((event.loaded / event.total) * 100)));
      }
    });
    request.addEventListener("load", () => {
      if (request.status >= 200 && request.status < 300) {
        onProgress?.(100);
        resolve(request.response as RehearsalVideoUploadResponse);
        return;
      }
      reject(new Error(readUploadError(request)));
    });
    request.addEventListener("error", () => reject(new Error("无法连接后端，视频附件未能上传到 MinIO。")));
    request.addEventListener("abort", () => reject(new Error("视频上传已取消。")));
    request.send(formData);
  });
}

export async function createRehearsalReviewTask(form: RehearsalReviewForm) {
  const response = await fetch(`${apiBaseUrl}/api/rehearsal-reviews/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as { task_id: string; rehearsal_review_id: string; status: string; message: string };
}

export async function fetchRehearsalReviews(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/rehearsal-reviews`, { signal });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as RehearsalReviewSummary[];
}

export async function fetchRehearsalReview(rehearsalReviewId: string) {
  const response = await fetch(`${apiBaseUrl}/api/rehearsal-reviews/${rehearsalReviewId}`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as RehearsalReviewResponse;
}

export async function updateRehearsalReview(rehearsalReviewId: string, editedContent: RehearsalReviewContent) {
  const response = await fetch(`${apiBaseUrl}/api/rehearsal-reviews/${rehearsalReviewId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ edited_content: editedContent }),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as RehearsalReviewResponse;
}

export async function deleteRehearsalReview(rehearsalReviewId: string) {
  const response = await fetch(`${apiBaseUrl}/api/rehearsal-reviews/${rehearsalReviewId}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
}

export async function fetchRehearsalReviewMarkdown(rehearsalReviewId: string) {
  const response = await fetch(`${apiBaseUrl}/api/rehearsal-reviews/${rehearsalReviewId}/markdown`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return response.text();
}

export function rehearsalReviewVideoUrl(rehearsalReviewId: string) {
  return `${apiBaseUrl}/api/rehearsal-reviews/${rehearsalReviewId}/video`;
}

export async function createMovementGuide(form: MovementGuideForm) {
  const response = await fetch(`${apiBaseUrl}/api/movement-guides`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as MovementGuideResponse;
}

export async function fetchMovementGuides(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/movement-guides`, { signal });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as MovementGuideSummary[];
}

export async function fetchMovementGuide(movementGuideId: string) {
  const response = await fetch(`${apiBaseUrl}/api/movement-guides/${movementGuideId}`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as MovementGuideResponse;
}

export async function updateMovementGuide(movementGuideId: string, editedContent: MovementGuideContent) {
  const response = await fetch(`${apiBaseUrl}/api/movement-guides/${movementGuideId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ edited_content: editedContent }),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as MovementGuideResponse;
}

export async function deleteMovementGuide(movementGuideId: string) {
  const response = await fetch(`${apiBaseUrl}/api/movement-guides/${movementGuideId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
}

export async function fetchMovementGuideMarkdown(movementGuideId: string) {
  const response = await fetch(`${apiBaseUrl}/api/movement-guides/${movementGuideId}/markdown`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return response.text();
}

export async function createMovementCandidatePlaceholder(movementGuideId: string) {
  const response = await fetch(`${apiBaseUrl}/api/movement-guides/${movementGuideId}/generate-candidates`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as { movement_guide_id: string; status: "not_implemented"; message: string };
}

export async function createPracticeSubmission(form: PracticeSubmissionForm) {
  const response = await fetch(`${apiBaseUrl}/api/practice-submissions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as PracticeSubmissionDetail;
}

export async function uploadPracticeVideo(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${apiBaseUrl}/api/practice-submissions/upload`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as PracticeVideoUploadResponse;
}

export async function fetchPracticeSubmissions(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/practice-submissions`, { signal });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as PracticeSubmissionSummary[];
}

export async function fetchPracticeSubmission(submissionId: string) {
  const response = await fetch(`${apiBaseUrl}/api/practice-submissions/${submissionId}`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as PracticeSubmissionDetail;
}

export async function analyzePracticeSubmission(submissionId: string) {
  const response = await fetch(`${apiBaseUrl}/api/practice-submissions/${submissionId}/analyze`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as PracticeAnalyzeResponse;
}

export async function updatePracticeReport(reportId: string, editedContent: PracticeReportContent, teacherFeedback: string) {
  const response = await fetch(`${apiBaseUrl}/api/practice-reports/${reportId}/review`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      edited_content: editedContent,
      teacher_feedback: teacherFeedback,
      reviewed_by: "demo-teacher",
    }),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as PracticeReportResponse;
}

export async function deletePracticeSubmission(submissionId: string) {
  const response = await fetch(`${apiBaseUrl}/api/practice-submissions/${submissionId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
}

export async function fetchPracticeReportMarkdown(reportId: string) {
  const response = await fetch(`${apiBaseUrl}/api/practice-reports/${reportId}/markdown`);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return response.text();
}

/** 查询媒体供应商配置。响应只包含 configured 布尔值，不泄露 API Key。 */
export async function fetchMediaProviderOptions(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/media-providers`, { signal });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as MediaProviderOptions;
}

export async function uploadMediaAsset(file: File) {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${apiBaseUrl}/api/media-assets/upload`, { method: "POST", body });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as { asset: MediaAsset; message: string };
}

export async function createMediaGeneration(payload: {
  title?: string;
  provider: "grsai" | "runninghub";
  capability: "image" | "audio" | "video";
  model?: string;
  workflow_version_id?: string;
  prompt?: string;
  parameters?: Record<string, unknown>;
  input_asset_ids?: Record<string, string>;
  client_request_id?: string;
}) {
  const response = await fetch(`${apiBaseUrl}/api/media-generations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as MediaGeneration;
}

export async function fetchMediaGenerations(signal?: AbortSignal, workbenchSlug?: string) {
  const query = workbenchSlug ? `?workbench_slug=${encodeURIComponent(workbenchSlug)}` : "";
  const response = await fetch(`${apiBaseUrl}/api/media-generations${query}`, { signal });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as MediaGeneration[];
}

export async function fetchMediaWorkbenches(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/media-workbenches`, { signal });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as MediaWorkbenchConfig[];
}

export async function fetchMediaWorkbench(slug: string, signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/media-workbenches/${slug}`, { signal });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as MediaWorkbenchConfig;
}

export async function updateMediaWorkbenchConfiguration(
  slug: string,
  payload: {
    display_name: string;
    description: string;
    workflow_version_id: string | null;
    model: string;
    provider_api_mode: "workflow" | "unified" | "legacy";
    default_parameters: Record<string, unknown>;
    input_config: MediaWorkbenchInputConfig;
    enabled: boolean;
  },
) {
  const response = await fetch(`${apiBaseUrl}/api/media-workbenches/${slug}/configuration`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as MediaWorkbenchConfig;
}

export async function runMediaWorkbench(
  slug: string,
  payload: {
    prompt: string;
    primary_asset_id?: string;
    primary_asset_ids?: string[];
    secondary_asset_id?: string | null;
    parameters?: Record<string, unknown>;
    client_request_id?: string;
  },
) {
  const response = await fetch(`${apiBaseUrl}/api/media-workbenches/${slug}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as MediaGeneration;
}

export async function refreshMediaGeneration(generationId: string) {
  const response = await fetch(`${apiBaseUrl}/api/media-generations/${generationId}/refresh`, { method: "POST" });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as MediaGeneration;
}

export async function cancelMediaGeneration(generationId: string) {
  const response = await fetch(`${apiBaseUrl}/api/media-generations/${generationId}/cancel`, { method: "POST" });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as MediaGeneration;
}

export async function importRunningHubWorkflow(payload: {
  file: File;
  name: string;
  description: string;
  mediaType: "image" | "audio" | "video";
  workflowId: string;
  templateId?: string;
}) {
  const body = new FormData();
  body.append("file", payload.file);
  body.append("name", payload.name);
  body.append("description", payload.description);
  body.append("media_type", payload.mediaType);
  body.append("runninghub_workflow_id", payload.workflowId);
  if (payload.templateId) body.append("template_id", payload.templateId);
  const response = await fetch(`${apiBaseUrl}/api/runninghub/workflows/import`, { method: "POST", body });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as WorkflowTemplate;
}

export async function fetchRunningHubWorkflows(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/runninghub/workflows`, { signal });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as WorkflowTemplate[];
}

export async function updateRunningHubWorkflow(
  templateId: string,
  payload: { name: string; description: string; external_workflow_id: string; media_type: "image" | "audio" | "video" },
) {
  const response = await fetch(`${apiBaseUrl}/api/runninghub/workflows/${templateId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as WorkflowTemplate;
}

export async function configureRunningHubWorkflowVersion(
  versionId: string,
  parameters: WorkflowParameterConfig[],
  outputs: WorkflowOutputConfig[],
) {
  const response = await fetch(`${apiBaseUrl}/api/runninghub/workflow-versions/${versionId}/configuration`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parameters, outputs }),
  });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as WorkflowVersion;
}

export async function publishRunningHubWorkflowVersion(versionId: string) {
  const response = await fetch(`${apiBaseUrl}/api/runninghub/workflow-versions/${versionId}/publish`, { method: "POST" });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as WorkflowVersion;
}

export type CreateVeoTaskInput = {
  prompt: string;
  model: VeoModelCode;
  resolution: VeoResolution;
  durationSeconds: number;
  firstFrameFile: File | null;
  firstFrameUrl: string;
  lastFrameFile: File | null;
  lastFrameUrl: string;
};

export async function fetchVeoOptions(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/media-studio/veo/options`, { signal });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as VeoOptionsResponse;
}

export async function fetchVeoTasks(signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/media-studio/veo/tasks`, { signal });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as VeoTaskResponse[];
}

export async function createVeoTask(input: CreateVeoTaskInput) {
  const formData = new FormData();
  formData.append("prompt", input.prompt);
  formData.append("model", input.model);
  // Wan 2.7 的输出比例跟随首帧；分辨率和时长才是供应商实际支持的输出参数。
  formData.append("aspect_ratio", "auto");
  formData.append("resolution", input.resolution);
  formData.append("duration_seconds", String(input.durationSeconds));
  if (input.firstFrameFile) formData.append("first_frame", input.firstFrameFile);
  if (input.firstFrameUrl.trim()) formData.append("first_frame_url", input.firstFrameUrl.trim());
  if (input.lastFrameFile) formData.append("last_frame", input.lastFrameFile);
  if (input.lastFrameUrl.trim()) formData.append("last_frame_url", input.lastFrameUrl.trim());

  const response = await fetch(`${apiBaseUrl}/api/media-studio/veo/tasks`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as VeoTaskResponse;
}

export async function fetchVeoTask(taskId: string, signal?: AbortSignal) {
  const response = await fetch(`${apiBaseUrl}/api/media-studio/veo/tasks/${taskId}`, { signal });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as VeoTaskResponse;
}

async function readApiError(response: Response) {
  try {
    const data = (await response.json()) as { detail?: string; message?: string };
    return data.detail ?? data.message ?? `请求失败：${response.status}`;
  } catch {
    return `请求失败：${response.status}`;
  }
}

function readUploadError(request: XMLHttpRequest) {
  const response = request.response as { detail?: string; message?: string } | null;
  if (response && typeof response === "object") {
    return response.detail ?? response.message ?? `请求失败：${request.status}`;
  }
  return `请求失败：${request.status}`;
}
