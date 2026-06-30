import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { MusicalScriptEditor } from "../components/musical/MusicalScriptEditor";
import { TaskProgress } from "../components/lesson-plans/TaskProgress";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { Field, FieldLabel } from "../components/ui/field";
import { NumberField, TextareaField } from "../components/ui/FormFields";
import { LlmSettings } from "../components/ui/LlmSettings";
import { PageTitle } from "../components/ui/PageTitle";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import {
  createSongAdaptationTask,
  createRoleTrainingTask,
  fetchAiTask,
  fetchLlmOptions,
  fetchMusicalScript,
  updateMusicalScript,
} from "../lib/api";
import { downloadMusicalScriptMarkdown } from "../lib/download";
import { initialRoleTrainingForm, initialSongAdaptationForm } from "../lib/lessonPlanDefaults";
import type {
  AiTaskResponse,
  LlmOptionsResponse,
  MusicalScriptContent,
  MusicalScriptResponse,
  RoleTrainingForm,
  SongAdaptationForm,
  SongAdaptationRewriteIntensity,
} from "../types";

export function MusicalScriptDetailPage() {
  const { musicalScriptId } = useParams();
  const navigate = useNavigate();
  const [musicalScript, setMusicalScript] = useState<MusicalScriptResponse | null>(null);
  const [editedContent, setEditedContent] = useState<MusicalScriptContent | null>(null);
  const [songForm, setSongForm] = useState<SongAdaptationForm | null>(null);
  const [roleForm, setRoleForm] = useState<RoleTrainingForm | null>(null);
  const [llmOptions, setLlmOptions] = useState<LlmOptionsResponse | null>(null);
  const [task, setTask] = useState<AiTaskResponse | null>(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submittingSongAdaptation, setSubmittingSongAdaptation] = useState(false);
  const [submittingRoleTraining, setSubmittingRoleTraining] = useState(false);
  const [openingSongAdaptation, setOpeningSongAdaptation] = useState(false);
  const [openingTrainingPlan, setOpeningTrainingPlan] = useState(false);
  const pollingTaskId = useRef<string | null>(null);
  const redirectResultId = useRef<string | null>(null);
  const redirectTimer = useRef<number | null>(null);

  useEffect(() => {
    if (!musicalScriptId) {
      return;
    }
    void fetchMusicalScript(musicalScriptId)
      .then((detail) => {
        setMusicalScript(detail);
        const content = detail.edited_content ?? detail.content;
        setEditedContent(content);
        setSongForm(buildInitialSongAdaptationForm(detail.id, content));
        setRoleForm(initialRoleTrainingForm(detail.id));
        setNotice("");
      })
      .catch((caughtError) => setNotice(caughtError instanceof Error ? caughtError.message : "读取剧本失败。"))
      .finally(() => setLoading(false));
  }, [musicalScriptId]);

  useEffect(() => {
    const controller = new AbortController();
    void fetchLlmOptions(controller.signal)
      .then((options) => {
        setLlmOptions(options);
        setRoleForm((current) =>
          current
            ? {
                ...current,
                llm_provider: options.default_provider,
                llm_model: options.default_model,
                reasoning_level: options.default_reasoning_level,
              }
            : current,
        );
        setSongForm((current) =>
          current
            ? {
                ...current,
                llm_provider: options.default_provider,
                llm_model: options.default_model,
                reasoning_level: options.default_reasoning_level,
              }
            : current,
        );
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!task || task.status === "SUCCESS" || task.status === "FAILED" || task.status === "CANCELLED") {
      return;
    }
    pollingTaskId.current = task.id;
    const timer = window.setInterval(() => {
      void refreshTask(task.id);
    }, 1800);
    return () => window.clearInterval(timer);
  }, [task]);

  useEffect(() => {
    return () => {
      if (redirectTimer.current !== null) {
        window.clearTimeout(redirectTimer.current);
      }
    };
  }, []);

  async function saveMusicalScript() {
    if (!musicalScript || !editedContent) {
      return;
    }
    setSaving(true);
    setNotice("");
    try {
      const updated = await updateMusicalScript(musicalScript.id, editedContent);
      setMusicalScript(updated);
      setEditedContent(updated.edited_content ?? updated.content);
      setNotice("编导编辑稿已保存。");
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "保存失败。");
    } finally {
      setSaving(false);
    }
  }

  async function handleDownloadMarkdown() {
    if (!musicalScript) {
      return;
    }
    try {
      setNotice("");
      await downloadMusicalScriptMarkdown(musicalScript.id, musicalScript.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  async function submitRoleTraining(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submittingRoleTraining || taskInProgress || openingTrainingPlan) {
      return;
    }
    if (!roleForm) {
      return;
    }
    setSubmittingRoleTraining(true);
    setNotice("");
    setTask(null);
    setOpeningTrainingPlan(false);
    redirectResultId.current = null;
    if (redirectTimer.current !== null) {
      window.clearTimeout(redirectTimer.current);
      redirectTimer.current = null;
    }
    pollingTaskId.current = null;
    try {
      if (musicalScript && editedContent) {
        await updateMusicalScript(musicalScript.id, editedContent);
      }
      const created = await createRoleTrainingTask(roleForm);
      pollingTaskId.current = created.task_id;
      setNotice("分角色训练计划任务已提交，生成完成后会自动打开详情。");
      await refreshTask(created.task_id);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "提交训练计划任务失败。");
    } finally {
      setSubmittingRoleTraining(false);
    }
  }

  async function submitSongAdaptation(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submittingSongAdaptation || taskInProgress || openingSongAdaptation || openingTrainingPlan) {
      return;
    }
    if (!songForm) {
      return;
    }
    setSubmittingSongAdaptation(true);
    setNotice("");
    setTask(null);
    setOpeningSongAdaptation(false);
    setOpeningTrainingPlan(false);
    redirectResultId.current = null;
    if (redirectTimer.current !== null) {
      window.clearTimeout(redirectTimer.current);
      redirectTimer.current = null;
    }
    pollingTaskId.current = null;
    try {
      if (musicalScript && editedContent) {
        await updateMusicalScript(musicalScript.id, editedContent);
      }
      const created = await createSongAdaptationTask(songForm);
      pollingTaskId.current = created.task_id;
      setNotice("唱段适配任务已提交，生成完成后会自动打开详情。");
      await refreshTask(created.task_id);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "提交唱段适配任务失败。");
    } finally {
      setSubmittingSongAdaptation(false);
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
        if (redirectResultId.current === nextTask.result_id) {
          return;
        }
        redirectResultId.current = nextTask.result_id;
        const isSongAdaptationTask = nextTask.task_type === "song_adaptation.generate";
        setOpeningSongAdaptation(isSongAdaptationTask);
        setOpeningTrainingPlan(!isSongAdaptationTask);
        setNotice(isSongAdaptationTask ? "唱段适配已生成，正在打开详情页。" : "训练计划已生成，正在打开详情页。");
        redirectTimer.current = window.setTimeout(() => {
          navigate(isSongAdaptationTask ? `/song-adaptations/${nextTask.result_id}` : `/role-training-plans/${nextTask.result_id}`);
        }, 1100);
      }
      if (nextTask.status === "FAILED") {
        setNotice(nextTask.error_message ?? "AI 任务生成失败，请检查 Worker、Redis 或 LLM 配置。");
      }
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "查询任务失败。");
    }
  }

  const selectedSongProvider = songForm ? llmOptions?.providers.find((provider) => provider.id === songForm.llm_provider) : undefined;
  const selectedSongModelOptions = selectedSongProvider?.models ?? [];
  const selectedRoleProvider = roleForm ? llmOptions?.providers.find((provider) => provider.id === roleForm.llm_provider) : undefined;
  const selectedRoleModelOptions = selectedRoleProvider?.models ?? [];
  const taskInProgress = task?.status === "PENDING" || task?.status === "RUNNING";
  const songTaskActive = task?.task_type === "song_adaptation.generate";
  const roleTaskActive = task?.task_type === "role_training.generate";

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="剧本详情"
        title={musicalScript?.title ?? "读取剧本"}
        description="查看、继续修改并导出编导确认稿，也可以基于当前剧本生成唱段适配和分角色训练计划。"
        action={
          <div className="button-row">
            <Button variant="secondary" type="button" onClick={() => navigate("/musical-scripts")}>
              返回列表
            </Button>
            {musicalScript ? (
              <Button variant="secondary" type="button" onClick={() => void handleDownloadMarkdown()}>
                导出 Markdown
              </Button>
            ) : null}
            <Button type="button" disabled={!editedContent || saving} onClick={() => void saveMusicalScript()}>
              {saving ? "保存中..." : "保存全部修改"}
            </Button>
          </div>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取剧本" text="请稍候，系统正在读取剧本详情。" /> : null}

      <section className="script-detail-layout">
        <Card asChild className="surface-panel">
          <aside>
            <div className="section-heading">
              <div>
                <p className="section-kicker">唱段适配</p>
                <h2>生成歌词与唱段建议</h2>
              </div>
            </div>
            {songForm ? (
              <form onSubmit={submitSongAdaptation}>
                <TextareaField label="关联剧情段落" rows={2} value={songForm.related_scene} onChange={(value) => updateSongForm("related_scene", value)} />
                <TextareaField label="原曲 / 音乐来源" rows={2} required={false} value={songForm.source_song} onChange={(value) => updateSongForm("source_song", value)} />
                <TextareaField label="原歌词" rows={5} value={songForm.lyrics_text} onChange={(value) => updateSongForm("lyrics_text", value)} />
                <TextareaField label="音乐段落表" rows={5} value={songForm.music_structure} onChange={(value) => updateSongForm("music_structure", value)} />
                <TextareaField label="改写目标" value={songForm.adaptation_goal} onChange={(value) => updateSongForm("adaptation_goal", value)} />
                <TextareaField label="演唱角色" rows={2} value={songForm.singing_roles} onChange={(value) => updateSongForm("singing_roles", value)} />
                <Field className="field">
                  <FieldLabel>改写强度</FieldLabel>
                  <Select value={songForm.rewrite_intensity} onValueChange={(value) => updateSongForm("rewrite_intensity", value as SongAdaptationRewriteIntensity)}>
                    <SelectTrigger className="w-full bg-card">
                      <SelectValue placeholder="选择改写强度" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectItem value="structure_only">只做结构标注</SelectItem>
                        <SelectItem value="light_rewrite">轻微改词</SelectItem>
                        <SelectItem value="strong_rewrite">明显改编</SelectItem>
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </Field>
                <LlmSettings
                  provider={songForm.llm_provider}
                  model={songForm.llm_model}
                  reasoningLevel={songForm.reasoning_level}
                  llmOptions={llmOptions}
                  selectedModelOptions={selectedSongModelOptions}
                  onProviderChange={(providerId) => changeSongProvider(providerId as SongAdaptationForm["llm_provider"])}
                  onModelChange={(modelId) => updateSongForm("llm_model", modelId)}
                  onReasoningLevelChange={(level) => updateSongForm("reasoning_level", level as SongAdaptationForm["reasoning_level"])}
                />
                <Button
                  className="w-full"
                  type="submit"
                  data-busy={submittingSongAdaptation || taskInProgress || openingSongAdaptation ? "true" : undefined}
                  disabled={submittingSongAdaptation || taskInProgress || openingSongAdaptation || !llmOptions || selectedSongProvider?.configured === false}
                >
                  {submittingSongAdaptation
                    ? "正在提交任务..."
                    : taskInProgress && songTaskActive
                      ? "唱段适配生成中..."
                      : openingSongAdaptation
                        ? "正在打开唱段适配..."
                        : "生成唱段适配"}
                </Button>
                {openingSongAdaptation ? <p className="redirect-hint">唱段适配已生成，正在打开详情页...</p> : null}
                {songTaskActive ? <TaskProgress task={task} /> : null}
              </form>
            ) : (
              <EmptyState title="等待剧本" text="剧本读取完成后可以生成唱段适配建议。" />
            )}

            <div className="section-heading stacked-heading">
              <div>
                <p className="section-kicker">分角色训练</p>
                <h2>生成训练计划</h2>
              </div>
            </div>
            {roleForm ? (
              <form onSubmit={submitRoleTraining}>
                <div className="field-grid">
                  <NumberField label="排练天数" value={roleForm.rehearsal_days} onChange={(value) => updateRoleForm("rehearsal_days", value)} />
                  <NumberField label="单次分钟" value={roleForm.session_minutes} onChange={(value) => updateRoleForm("session_minutes", value)} />
                </div>
                <LlmSettings
                  provider={roleForm.llm_provider}
                  model={roleForm.llm_model}
                  reasoningLevel={roleForm.reasoning_level}
                  llmOptions={llmOptions}
                  selectedModelOptions={selectedRoleModelOptions}
                  onProviderChange={(providerId) => changeRoleProvider(providerId as RoleTrainingForm["llm_provider"])}
                  onModelChange={(modelId) => updateRoleForm("llm_model", modelId)}
                  onReasoningLevelChange={(level) => updateRoleForm("reasoning_level", level as RoleTrainingForm["reasoning_level"])}
                />
                <TextareaField label="训练重点" value={roleForm.training_focus} onChange={(value) => updateRoleForm("training_focus", value)} />
                <TextareaField label="补充说明" value={roleForm.notes} onChange={(value) => updateRoleForm("notes", value)} />
                <Button
                  className="w-full"
                  type="submit"
                  data-busy={submittingRoleTraining || taskInProgress || openingTrainingPlan ? "true" : undefined}
                  disabled={submittingRoleTraining || taskInProgress || openingTrainingPlan || !llmOptions || selectedRoleProvider?.configured === false}
                >
                  {submittingRoleTraining
                    ? "正在提交任务..."
                    : taskInProgress && roleTaskActive
                      ? "训练计划生成中..."
                      : openingTrainingPlan
                        ? "正在打开训练计划..."
                        : "生成训练计划"}
                </Button>
                {openingTrainingPlan ? <p className="redirect-hint">训练计划已生成，正在打开详情页...</p> : null}
                {roleTaskActive ? <TaskProgress task={task} /> : null}
              </form>
            ) : (
              <EmptyState title="等待剧本" text="剧本读取完成后可以生成分角色训练计划。" />
            )}
          </aside>
        </Card>

        <Card asChild className="surface-panel">
          <section>
            {editedContent ? (
              <MusicalScriptEditor content={editedContent} onChange={setEditedContent} modelInfo={musicalScript?.raw_model_info ?? null} />
            ) : !loading ? (
              <EmptyState title="剧本内容不可用" text="这份剧本可能尚未生成成功，暂时无法编辑或导出。" />
            ) : null}
          </section>
        </Card>
      </section>
    </main>
  );

  function updateRoleForm<Key extends keyof RoleTrainingForm>(key: Key, value: RoleTrainingForm[Key]) {
    setRoleForm((current) => (current ? { ...current, [key]: value } : current));
  }

  function updateSongForm<Key extends keyof SongAdaptationForm>(key: Key, value: SongAdaptationForm[Key]) {
    setSongForm((current) => (current ? { ...current, [key]: value } : current));
  }

  function changeRoleProvider(providerId: RoleTrainingForm["llm_provider"]) {
    const provider = llmOptions?.providers.find((item) => item.id === providerId);
    const defaultModel = provider?.models[0]?.id ?? roleForm?.llm_model ?? "";
    setRoleForm((current) => (current ? { ...current, llm_provider: providerId, llm_model: defaultModel } : current));
  }

  function changeSongProvider(providerId: SongAdaptationForm["llm_provider"]) {
    const provider = llmOptions?.providers.find((item) => item.id === providerId);
    const defaultModel = provider?.models[0]?.id ?? songForm?.llm_model ?? "";
    setSongForm((current) => (current ? { ...current, llm_provider: providerId, llm_model: defaultModel } : current));
  }
}

function buildInitialSongAdaptationForm(scriptId: string, content: MusicalScriptContent | null) {
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
