import { apiBaseUrl } from "./config";
import type {
  AiTaskResponse,
  HealthResponse,
  LessonPlanContent,
  LessonPlanForm,
  LessonPlanResponse,
  LessonPlanSummary,
  LlmOptionsResponse,
  MovementGuideContent,
  MovementGuideForm,
  MovementGuideResponse,
  MovementGuideSummary,
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
  RoleTrainingContent,
  RoleTrainingForm,
  RoleTrainingPlanResponse,
  RoleTrainingPlanSummary,
  SongAdaptationContent,
  SongAdaptationForm,
  SongAdaptationResponse,
  SongAdaptationSummary,
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

async function readApiError(response: Response) {
  try {
    const data = (await response.json()) as { detail?: string; message?: string };
    return data.detail ?? data.message ?? `请求失败：${response.status}`;
  } catch {
    return `请求失败：${response.status}`;
  }
}
