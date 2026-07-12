import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { TaskProgress } from "../components/lesson-plans/TaskProgress";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { Field, FieldDescription, FieldGroup, FieldLabel, FieldLegend, FieldSet } from "../components/ui/field";
import { TextareaField } from "../components/ui/FormFields";
import { Input } from "../components/ui/input";
import { LlmSettings } from "../components/ui/LlmSettings";
import { PageTitle } from "../components/ui/PageTitle";
import { Progress } from "../components/ui/progress";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "../components/ui/toggle-group";
import {
  createRehearsalReviewTask,
  fetchAiTask,
  fetchLlmOptions,
  fetchMusicalFusionPlans,
  fetchMusicalScripts,
  fetchRehearsalReview,
  fetchRoleTrainingPlans,
  uploadRehearsalVideo,
} from "../lib/api";
import { initialRehearsalReviewForm } from "../lib/lessonPlanDefaults";
import type {
  AiTaskResponse,
  LlmOptionsResponse,
  MusicalFusionPlanSummary,
  MusicalScriptSummary,
  RehearsalReviewForm,
  RehearsalReviewResponse,
  RoleTrainingPlanSummary,
} from "../types";


type MessageType = "status" | "error";
const NO_FUSION_PLAN = "none";
const NO_TRAINING_PLAN = "none";
const REVIEW_FOCUS_OPTIONS = ["唱段与节奏", "舞蹈与队形", "剧情与表演", "角色协作", "舞台调度", "教学组织"];


export function RehearsalReviewGeneratePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const scriptSelectId = useId();
  const fusionSelectId = useId();
  const trainingSelectId = useId();
  const eventTypeLabelId = useId();
  const eventDateId = useId();
  const reviewFocusLabelId = useId();
  const videoInputId = useId();
  const [scripts, setScripts] = useState<MusicalScriptSummary[]>([]);
  const [fusionPlans, setFusionPlans] = useState<MusicalFusionPlanSummary[]>([]);
  const [trainingPlans, setTrainingPlans] = useState<RoleTrainingPlanSummary[]>([]);
  const [form, setForm] = useState<RehearsalReviewForm>(() => initialRehearsalReviewForm(""));
  const [templatePrompts, setTemplatePrompts] = useState<string[]>([]);
  const [templateSourceTitle, setTemplateSourceTitle] = useState("");
  const [selectedVideoFile, setSelectedVideoFile] = useState<File | null>(null);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [llmOptions, setLlmOptions] = useState<LlmOptionsResponse | null>(null);
  const [task, setTask] = useState<AiTaskResponse | null>(null);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState<MessageType>("status");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const pollingTaskId = useRef<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadPage() {
      try {
        const templateId = searchParams.get("template_from");
        const [scriptRows, fusionRows, trainingRows, options, templateSource] = await Promise.all([
          fetchMusicalScripts(controller.signal),
          fetchMusicalFusionPlans(controller.signal),
          fetchRoleTrainingPlans(controller.signal),
          fetchLlmOptions(controller.signal),
          templateId ? fetchRehearsalReview(templateId).catch(() => null) : Promise.resolve<RehearsalReviewResponse | null>(null),
        ]);
        if (controller.signal.aborted) {
          return;
        }

        setScripts(scriptRows);
        setFusionPlans(fusionRows);
        setTrainingPlans(trainingRows);
        setLlmOptions(options);
        if (scriptRows.length === 0) {
          return;
        }

        const requestedScriptId = templateSource?.script_id ?? searchParams.get("script_id");
        const requestedScript = scriptRows.find((item) => item.id === requestedScriptId);
        const selectedScript = requestedScript ?? scriptRows[0];
        const matchingFusionRows = fusionRows.filter((item) => item.script_id === selectedScript.id);
        const matchingTrainingRows = trainingRows.filter((item) => item.script_id === selectedScript.id);
        const requestedFusionId = templateSource?.fusion_plan_id ?? searchParams.get("fusion_plan_id");
        const requestedTrainingId = templateSource?.role_training_plan_id ?? searchParams.get("role_training_plan_id");
        // 从模板进入时严格复用原关联；普通新建页才推荐当前剧本下最新的 M04/M05。
        const selectedFusion = templateSource
          ? (requestedFusionId ? matchingFusionRows.find((item) => item.id === requestedFusionId) ?? null : null)
          : matchingFusionRows.find((item) => item.id === requestedFusionId) ?? matchingFusionRows[0] ?? null;
        const selectedTraining = templateSource
          ? (requestedTrainingId ? matchingTrainingRows.find((item) => item.id === requestedTrainingId) ?? null : null)
          : matchingTrainingRows.find((item) => item.id === requestedTrainingId) ?? matchingTrainingRows[0] ?? null;
        const nextForm = initialRehearsalReviewForm(selectedScript.id);
        nextForm.fusion_plan_id = selectedFusion?.id ?? null;
        nextForm.role_training_plan_id = selectedTraining?.id ?? null;
        nextForm.llm_provider = options.default_provider;
        nextForm.llm_model = options.default_model;
        nextForm.reasoning_level = options.default_reasoning_level;

        const templateContent = templateSource?.edited_content ?? templateSource?.content;
        if (templateContent) {
          // 模板只复用观察框架；本次事实、日期、结论、目标和视频都保持为空或新默认值。
          nextForm.review_focus = templateContent.reusable_template.review_focus;
          nextForm.rehearsal_content = "";
          nextForm.event_date = "";
          nextForm.observation_notes = "";
          nextForm.strengths = "";
          nextForm.issues = "";
          nextForm.next_goal = "";
          setTemplatePrompts(templateContent.reusable_template.observation_prompts);
          setTemplateSourceTitle(templateContent.reusable_template.template_title);
          showStatus("已载入报告内复盘模板；旧日期、观察结论、目标和视频均未复制。\n");
        }
        setForm(nextForm);
      } catch (caughtError) {
        if (caughtError instanceof DOMException && caughtError.name === "AbortError") {
          return;
        }
        showError(caughtError instanceof Error ? caughtError.message : "读取剧本、排练资料和模型配置失败。");
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadPage();
    return () => controller.abort();
  }, [searchParams]);

  useEffect(() => {
    return () => {
      if (videoPreviewUrl) {
        URL.revokeObjectURL(videoPreviewUrl);
      }
    };
  }, [videoPreviewUrl]);

  useEffect(() => {
    if (!task || task.status === "SUCCESS" || task.status === "FAILED" || task.status === "CANCELLED") {
      return;
    }
    pollingTaskId.current = task.id;
    const timer = window.setInterval(() => void refreshTask(task.id), 1800);
    return () => window.clearInterval(timer);
  }, [task]);

  const matchingFusionPlans = useMemo(
    () => fusionPlans.filter((item) => item.script_id === form.script_id),
    [form.script_id, fusionPlans],
  );
  const matchingTrainingPlans = useMemo(
    () => trainingPlans.filter((item) => item.script_id === form.script_id),
    [form.script_id, trainingPlans],
  );
  const selectedFusionPlan = matchingFusionPlans.find((item) => item.id === form.fusion_plan_id) ?? null;
  const selectedTrainingPlan = matchingTrainingPlans.find((item) => item.id === form.role_training_plan_id) ?? null;
  const selectedProvider = llmOptions?.providers.find((provider) => provider.id === form.llm_provider);
  const selectedModelOptions = selectedProvider?.models ?? [];
  const taskInProgress = task?.status === "PENDING" || task?.status === "RUNNING";
  const reviewFocusOptions = useMemo(
    // 兼容旧报告或模型沉淀的自定义复盘重点，模板复用时不能把未列入固定选项的值悄悄隐藏。
    () => Array.from(new Set([...REVIEW_FOCUS_OPTIONS, ...form.review_focus])),
    [form.review_focus],
  );

  function changeScript(scriptId: string) {
    const latestFusion = fusionPlans.find((item) => item.script_id === scriptId) ?? null;
    const latestTraining = trainingPlans.find((item) => item.script_id === scriptId) ?? null;
    clearSelectedVideo();
    setTemplatePrompts([]);
    setTemplateSourceTitle("");
    setTask(null);
    setForm((current) => ({
      ...initialRehearsalReviewForm(scriptId),
      fusion_plan_id: latestFusion?.id ?? null,
      role_training_plan_id: latestTraining?.id ?? null,
      llm_provider: current.llm_provider,
      llm_model: current.llm_model,
      reasoning_level: current.reasoning_level,
    }));
    showStatus("已切换剧本，并重新选择该剧本最新的 M04/M05 上下文。\n");
  }

  function selectVideo(file: File | null) {
    setSelectedVideoFile(file);
    updateVideoMetadata(null);
    if (videoPreviewUrl) {
      URL.revokeObjectURL(videoPreviewUrl);
    }
    setVideoPreviewUrl(file ? URL.createObjectURL(file) : "");
    if (file) {
      showStatus("已选择视频；请先上传到 MinIO，再提交复盘任务。\n");
    }
  }

  async function uploadSelectedVideo() {
    if (!selectedVideoFile || uploading) {
      return;
    }
    setUploading(true);
    setUploadProgress(0);
    showStatus("正在把视频附件上传到 MinIO……");
    try {
      const uploaded = await uploadRehearsalVideo(selectedVideoFile, setUploadProgress);
      updateVideoMetadata(uploaded);
      showStatus(`视频已保存到 MinIO：${uploaded.original_file_name}。AI 不会读取或分析该视频。`);
    } catch (caughtError) {
      setUploadProgress(null);
      showError(caughtError instanceof Error ? caughtError.message : "视频上传失败。");
    } finally {
      setUploading(false);
    }
  }

  function clearSelectedVideo() {
    setSelectedVideoFile(null);
    setUploadProgress(null);
    updateVideoMetadata(null);
    if (videoPreviewUrl) {
      URL.revokeObjectURL(videoPreviewUrl);
    }
    setVideoPreviewUrl("");
  }

  async function submitRehearsalReview(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || taskInProgress || !form.script_id) {
      return;
    }
    if (selectedVideoFile && !form.video_object_key) {
      showError("已选择视频但尚未上传，请先上传到 MinIO或移除该视频。\n");
      return;
    }
    if (form.review_focus.length === 0) {
      showError("请至少选择一个复盘重点。\n");
      return;
    }

    setSubmitting(true);
    setTask(null);
    pollingTaskId.current = null;
    showStatus("正在提交排练复盘任务……");
    try {
      const created = await createRehearsalReviewTask(form);
      pollingTaskId.current = created.task_id;
      showStatus("排练复盘任务已提交，生成完成后会自动打开详情页。\n");
      await refreshTask(created.task_id);
    } catch (caughtError) {
      showError(caughtError instanceof Error ? caughtError.message : "提交排练复盘任务失败。");
    } finally {
      setSubmitting(false);
    }
  }

  async function refreshTask(taskId: string) {
    try {
      const nextTask = await fetchAiTask(taskId);
      if (pollingTaskId.current && pollingTaskId.current !== nextTask.id) {
        return;
      }
      setTask(nextTask);
      if (nextTask.status === "SUCCESS" && nextTask.result_id) {
        showStatus("复盘报告已生成，正在打开详情页。\n");
        navigate(`/rehearsal-reviews/${nextTask.result_id}`);
      } else if (nextTask.status === "FAILED") {
        showError(nextTask.error_message ?? "复盘报告生成失败，请检查 Worker、Redis 或 LLM 配置。");
      }
    } catch (caughtError) {
      showError(caughtError instanceof Error ? caughtError.message : "查询排练复盘任务失败。");
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="M08 排练 / 演出复盘"
        title="把现场观察整理成下一次行动"
        description="关联剧本与排演资料，上传可选视频附件，并把老师的观察记录整理成可编辑、可复用的复盘报告。"
        action={
          <div className="button-row">
            {form.script_id ? (
              <Button variant="secondary" type="button" onClick={() => navigate(`/musical-scripts/${form.script_id}`)}>
                返回剧本
              </Button>
            ) : null}
            <Button variant="secondary" type="button" onClick={() => navigate("/rehearsal-reviews")}>
              已保存的复盘
            </Button>
          </div>
        }
      />

      <div className="review-boundary-banner" role="note">
        <strong>人工观察优先</strong>
        <span>AI 仅整理老师填写的观察记录；上传视频仅供人工查看，系统不会分析视频内容。</span>
      </div>
      {message ? (
        <p className="notice" role={messageType === "error" ? "alert" : "status"} aria-live={messageType === "error" ? "assertive" : "polite"}>
          {message}
        </p>
      ) : null}
      {loading ? <EmptyState title="正在读取排演资料" text="请稍候，系统正在加载剧本、M04、M05 和模型配置。" /> : null}
      {!loading && scripts.length === 0 ? (
        <EmptyState title="还没有可用剧本" text="请先生成并保存一份歌舞剧剧本，再创建排练复盘报告。" />
      ) : null}

      {!loading && scripts.length > 0 ? (
        <form className="review-generation-layout" onSubmit={submitRehearsalReview}>
          <div className="review-generation-main">
            <Card className="surface-panel">
              <CardHeader>
                <CardTitle>关联本次排演上下文</CardTitle>
                <CardDescription>剧本必选；M04 和 M05 可选，并且只能选择同一剧本下的已生成内容。</CardDescription>
              </CardHeader>
              <CardContent>
                <FieldGroup>
                  <Field data-disabled={taskInProgress || undefined}>
                    <FieldLabel htmlFor={scriptSelectId}>歌舞剧剧本</FieldLabel>
                    <Select value={form.script_id} onValueChange={changeScript} disabled={taskInProgress}>
                      <SelectTrigger id={scriptSelectId} className="w-full bg-card">
                        <SelectValue placeholder="选择剧本" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          {scripts.map((script) => (
                            <SelectItem key={script.id} value={script.id}>{script.title}</SelectItem>
                          ))}
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </Field>
                  <div className="field-grid">
                    <Field>
                      <FieldLabel htmlFor={fusionSelectId}>M04 歌舞融合</FieldLabel>
                      <Select value={form.fusion_plan_id ?? NO_FUSION_PLAN} onValueChange={(value) => updateForm("fusion_plan_id", value === NO_FUSION_PLAN ? null : value)}>
                        <SelectTrigger id={fusionSelectId} className="w-full bg-card"><SelectValue placeholder="选择 M04" /></SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            <SelectItem value={NO_FUSION_PLAN}>不引用 M04</SelectItem>
                            {matchingFusionPlans.map((plan) => <SelectItem key={plan.id} value={plan.id}>{plan.title}</SelectItem>)}
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                    </Field>
                    <Field>
                      <FieldLabel htmlFor={trainingSelectId}>M05 分角色训练</FieldLabel>
                      <Select value={form.role_training_plan_id ?? NO_TRAINING_PLAN} onValueChange={(value) => updateForm("role_training_plan_id", value === NO_TRAINING_PLAN ? null : value)}>
                        <SelectTrigger id={trainingSelectId} className="w-full bg-card"><SelectValue placeholder="选择 M05" /></SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            <SelectItem value={NO_TRAINING_PLAN}>不引用 M05</SelectItem>
                            {matchingTrainingPlans.map((plan) => <SelectItem key={plan.id} value={plan.id}>{plan.title}</SelectItem>)}
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                    </Field>
                  </div>
                  <div className="source-summary" aria-label="当前复盘上下文">
                    <div className="readable-chip-row">
                      <Badge variant="secondary">剧本必选</Badge>
                      <Badge variant="outline">{selectedFusionPlan ? "已引用 M04" : "未引用 M04"}</Badge>
                      <Badge variant="outline">{selectedTrainingPlan ? "已引用 M05" : "未引用 M05"}</Badge>
                    </div>
                    <strong>{scripts.find((item) => item.id === form.script_id)?.title}</strong>
                    <p>生成时会保存上游确认稿快照，后续删除 M04/M05 不影响已经生成的复盘正文。</p>
                  </div>
                </FieldGroup>
              </CardContent>
            </Card>

            {templatePrompts.length > 0 ? (
              <Card className="surface-panel review-template-source">
                <CardHeader>
                  <CardTitle>{templateSourceTitle || "已载入复盘模板"}</CardTitle>
                  <CardDescription>以下提示用于本次现场记录，旧报告事实和视频没有复制。</CardDescription>
                </CardHeader>
                <CardContent>
                  <ol>{templatePrompts.map((prompt, index) => <li key={`${prompt}-${index}`}>{prompt}</li>)}</ol>
                </CardContent>
              </Card>
            ) : null}

            <Card className="surface-panel">
              <CardHeader>
                <CardTitle>填写人工观察记录</CardTitle>
                <CardDescription>尽量写清楚“发生了什么、影响了什么、下一次想改善什么”，不要只写抽象评价。</CardDescription>
              </CardHeader>
              <CardContent>
                <FieldGroup>
                  <div className="field-grid">
                    <Field>
                      <FieldLabel id={eventTypeLabelId}>记录类型</FieldLabel>
                      <ToggleGroup aria-labelledby={eventTypeLabelId} type="single" value={form.event_type} variant="outline" onValueChange={(value) => value && updateForm("event_type", value as RehearsalReviewForm["event_type"])}>
                        <ToggleGroupItem value="rehearsal">排练复盘</ToggleGroupItem>
                        <ToggleGroupItem value="performance">演出复盘</ToggleGroupItem>
                      </ToggleGroup>
                    </Field>
                    <Field>
                      <FieldLabel htmlFor={eventDateId}>日期</FieldLabel>
                      <Input id={eventDateId} type="date" value={form.event_date} onChange={(event) => updateForm("event_date", event.target.value)} required />
                    </Field>
                  </div>
                  <TextareaField label="本次排练 / 演出内容" rows={3} value={form.rehearsal_content} onChange={(value) => updateForm("rehearsal_content", value)} />
                  <TextareaField label="原始观察记录" rows={7} value={form.observation_notes} onChange={(value) => updateForm("observation_notes", value)} />
                  <div className="field-grid">
                    <TextareaField label="完成较好的部分" rows={4} value={form.strengths} required={false} onChange={(value) => updateForm("strengths", value)} />
                    <TextareaField label="已经明确的问题" rows={4} value={form.issues} required={false} onChange={(value) => updateForm("issues", value)} />
                  </div>
                  <FieldSet>
                    <FieldLegend id={reviewFocusLabelId} variant="label">复盘重点</FieldLegend>
                    <ToggleGroup aria-labelledby={reviewFocusLabelId} type="multiple" value={form.review_focus} variant="outline" onValueChange={(value) => updateForm("review_focus", value)}>
                      {reviewFocusOptions.map((option) => <ToggleGroupItem key={option} value={option}>{option}</ToggleGroupItem>)}
                    </ToggleGroup>
                    <FieldDescription>至少选择一项；模板复用时会自动带入上一次沉淀的观察框架。</FieldDescription>
                  </FieldSet>
                  <TextareaField label="下一次目标" rows={4} value={form.next_goal} onChange={(value) => updateForm("next_goal", value)} />
                </FieldGroup>
              </CardContent>
            </Card>

            <Card className="surface-panel">
              <CardHeader>
                <CardTitle>可选视频附件</CardTitle>
                <CardDescription>视频保存到 MinIO 私有桶，仅供老师在报告详情中人工查看，不进入 AI 输入。</CardDescription>
              </CardHeader>
              <CardContent>
                <FieldGroup>
                  <Field>
                    <FieldLabel htmlFor={videoInputId}>选择短视频</FieldLabel>
                    <Input id={videoInputId} accept="video/*,.mp4,.mov,.m4v,.webm,.avi,.mkv" type="file" onChange={(event) => selectVideo(event.target.files?.[0] ?? null)} />
                    <FieldDescription>建议 15–60 秒，单文件不超过 200MB。当前每份报告只保存一个附件。</FieldDescription>
                  </Field>
                  {selectedVideoFile ? (
                    <div className="review-video-upload">
                      <div className="review-video-meta">
                        <div className="readable-chip-row">
                          <Badge variant={form.video_object_key ? "secondary" : "outline"}>{form.video_object_key ? "已上传 MinIO" : "等待上传"}</Badge>
                          <Badge variant="outline">{formatFileSize(selectedVideoFile.size)}</Badge>
                        </div>
                        <strong>{selectedVideoFile.name}</strong>
                        <div className="button-row">
                          <Button type="button" variant="secondary" disabled={uploading || Boolean(form.video_object_key)} onClick={() => void uploadSelectedVideo()}>
                            {uploading ? "上传中……" : form.video_object_key ? "已上传" : "上传到 MinIO"}
                          </Button>
                          <Button type="button" variant="secondary" disabled={uploading} onClick={clearSelectedVideo}>移除附件</Button>
                        </div>
                        {uploadProgress !== null ? (
                          <div className="review-upload-progress" aria-live="polite">
                            <Progress value={uploadProgress} aria-label="视频上传进度" />
                            <span>{uploadProgress < 100 ? `上传 ${uploadProgress}%` : "MinIO 上传完成"}</span>
                          </div>
                        ) : null}
                      </div>
                      {videoPreviewUrl ? <video className="review-video-preview" controls preload="metadata" src={videoPreviewUrl} /> : null}
                    </div>
                  ) : null}
                  <TextareaField label="视频人工备注" rows={3} required={false} value={form.video_notes} onChange={(value) => updateForm("video_notes", value)} />
                </FieldGroup>
              </CardContent>
            </Card>
          </div>

          <aside className="review-generation-sidebar">
            <Card className="surface-panel review-submit-card">
              <CardHeader>
                <CardTitle>生成结构化复盘</CardTitle>
                <CardDescription>输出问题原因、改进措施、角色任务、下一次计划、教学反思和复用模板。</CardDescription>
              </CardHeader>
              <CardContent>
                <LlmSettings
                  provider={form.llm_provider}
                  model={form.llm_model}
                  reasoningLevel={form.reasoning_level}
                  llmOptions={llmOptions}
                  selectedModelOptions={selectedModelOptions}
                  onProviderChange={(providerId) => changeProvider(providerId as RehearsalReviewForm["llm_provider"])}
                  onModelChange={(modelId) => updateForm("llm_model", modelId)}
                  onReasoningLevelChange={(level) => updateForm("reasoning_level", level as RehearsalReviewForm["reasoning_level"])}
                />
                <TaskProgress task={task} />
              </CardContent>
              <CardFooter>
                <Button className="w-full" type="submit" disabled={submitting || taskInProgress || uploading || !llmOptions || selectedProvider?.configured === false}>
                  {submitting ? "正在提交任务……" : taskInProgress ? "复盘报告生成中……" : "生成 M08 复盘报告"}
                </Button>
              </CardFooter>
            </Card>
          </aside>
        </form>
      ) : null}
    </main>
  );

  function updateForm<Key extends keyof RehearsalReviewForm>(key: Key, value: RehearsalReviewForm[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function updateVideoMetadata(uploaded: Awaited<ReturnType<typeof uploadRehearsalVideo>> | null) {
    setForm((current) => ({
      ...current,
      video_object_key: uploaded?.object_key ?? "",
      video_original_file_name: uploaded?.original_file_name ?? "",
      video_content_type: uploaded?.content_type ?? "",
      video_size_bytes: uploaded?.size_bytes ?? null,
    }));
  }

  function changeProvider(providerId: RehearsalReviewForm["llm_provider"]) {
    const provider = llmOptions?.providers.find((item) => item.id === providerId);
    const defaultModel = provider?.models[0]?.id ?? form.llm_model;
    setForm((current) => ({ ...current, llm_provider: providerId, llm_model: defaultModel }));
  }

  function showStatus(nextMessage: string) {
    setMessageType("status");
    setMessage(nextMessage.trim());
  }

  function showError(nextMessage: string) {
    setMessageType("error");
    setMessage(nextMessage.trim());
  }
}


function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(sizeBytes / 1024))} KB`;
  }
  return `${(sizeBytes / 1024 / 1024).toFixed(1)} MB`;
}
