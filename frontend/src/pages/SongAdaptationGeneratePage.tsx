import { useEffect, useId, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { TaskProgress } from "../components/lesson-plans/TaskProgress";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { Field, FieldGroup, FieldLabel } from "../components/ui/field";
import { TextareaField } from "../components/ui/FormFields";
import { LlmSettings } from "../components/ui/LlmSettings";
import { PageTitle } from "../components/ui/PageTitle";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import {
  createSongAdaptationTask,
  fetchAiTask,
  fetchLlmOptions,
  fetchMusicalScript,
  fetchMusicalScripts,
} from "../lib/api";
import { buildSongAdaptationFormFromScript, initialSongAdaptationForm } from "../lib/lessonPlanDefaults";
import type {
  AiTaskResponse,
  LlmOptionsResponse,
  MusicalScriptSummary,
  SongAdaptationForm,
  SongAdaptationRewriteIntensity,
} from "../types";

type MessageType = "status" | "error";

export function SongAdaptationGeneratePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const scriptSelectId = useId();
  const rewriteIntensityId = useId();
  const [scripts, setScripts] = useState<MusicalScriptSummary[]>([]);
  const [form, setForm] = useState<SongAdaptationForm>(() => initialSongAdaptationForm(""));
  const [llmOptions, setLlmOptions] = useState<LlmOptionsResponse | null>(null);
  const [task, setTask] = useState<AiTaskResponse | null>(null);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState<MessageType>("status");
  const [loading, setLoading] = useState(true);
  const [loadingScript, setLoadingScript] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const pollingTaskId = useRef<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadPage() {
      try {
        const [scriptRows, options] = await Promise.all([
          fetchMusicalScripts(controller.signal),
          fetchLlmOptions(controller.signal),
        ]);
        if (controller.signal.aborted) {
          return;
        }

        setScripts(scriptRows);
        setLlmOptions(options);
        if (scriptRows.length === 0) {
          return;
        }

        const requestedScriptId = searchParams.get("script_id");
        const requestedScript = scriptRows.find((item) => item.id === requestedScriptId);
        const selectedScript = requestedScript ?? scriptRows[0];
        const detail = await fetchMusicalScript(selectedScript.id);
        if (controller.signal.aborted) {
          return;
        }

        setForm({
          ...buildSongAdaptationFormFromScript(detail.id, detail.edited_content ?? detail.content),
          llm_provider: options.default_provider,
          llm_model: options.default_model,
          reasoning_level: options.default_reasoning_level,
        });
        if (requestedScriptId && !requestedScript) {
          showStatus("原链接中的剧本不可用，已为你选择第一份可用剧本。");
        }
      } catch (caughtError) {
        if (caughtError instanceof DOMException && caughtError.name === "AbortError") {
          return;
        }
        showError(caughtError instanceof Error ? caughtError.message : "读取剧本和模型配置失败。");
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
    if (!task || task.status === "SUCCESS" || task.status === "FAILED" || task.status === "CANCELLED") {
      return;
    }
    pollingTaskId.current = task.id;
    const timer = window.setInterval(() => void refreshTask(task.id), 1800);
    return () => window.clearInterval(timer);
  }, [task]);

  const selectedProvider = llmOptions?.providers.find((provider) => provider.id === form.llm_provider);
  const selectedModelOptions = selectedProvider?.models ?? [];
  const taskInProgress = task?.status === "PENDING" || task?.status === "RUNNING";

  async function changeScript(scriptId: string) {
    if (loadingScript || taskInProgress) {
      return;
    }
    setLoadingScript(true);
    setTask(null);
    showStatus("正在读取所选剧本的确认稿……");
    try {
      const detail = await fetchMusicalScript(scriptId);
      const nextForm = buildSongAdaptationFormFromScript(detail.id, detail.edited_content ?? detail.content);
      setForm((current) => ({
        ...nextForm,
        llm_provider: current.llm_provider,
        llm_model: current.llm_model,
        reasoning_level: current.reasoning_level,
      }));
      showStatus("已根据所选剧本重新填充剧情段落和演唱角色。");
    } catch (caughtError) {
      showError(caughtError instanceof Error ? caughtError.message : "读取所选剧本失败。");
    } finally {
      setLoadingScript(false);
    }
  }

  async function submitSongAdaptation(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || taskInProgress || loadingScript || !form.script_id) {
      return;
    }
    setSubmitting(true);
    setTask(null);
    pollingTaskId.current = null;
    showStatus("正在提交唱段适配任务……");
    try {
      const created = await createSongAdaptationTask(form);
      pollingTaskId.current = created.task_id;
      showStatus("唱段适配任务已提交，生成完成后会自动打开详情页。");
      await refreshTask(created.task_id);
    } catch (caughtError) {
      showError(caughtError instanceof Error ? caughtError.message : "提交唱段适配任务失败。");
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
        showStatus("唱段适配已生成，正在打开详情页。");
        navigate(`/song-adaptations/${nextTask.result_id}`);
      } else if (nextTask.status === "FAILED") {
        showError(nextTask.error_message ?? "唱段适配生成失败，请检查 Worker、Redis 或 LLM 配置。");
      }
    } catch (caughtError) {
      showError(caughtError instanceof Error ? caughtError.message : "查询唱段适配任务失败。");
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="M03 唱段适配"
        title="生成歌词与唱段建议"
        description="围绕一份剧本整理歌曲来源、歌词版本、演唱分配和舞蹈留白，生成音乐负责人可继续修改的初稿。"
        action={
          <div className="button-row">
            {form.script_id ? (
              <Button variant="secondary" type="button" onClick={() => navigate(`/musical-scripts/${form.script_id}`)}>
                返回剧本
              </Button>
            ) : null}
            <Button variant="secondary" type="button" onClick={() => navigate("/song-adaptations")}>
              已保存的唱段
            </Button>
          </div>
        }
      />

      {message ? (
        <p className="notice" role={messageType === "error" ? "alert" : "status"} aria-live={messageType === "error" ? "assertive" : "polite"}>
          {message}
        </p>
      ) : null}
      {loading ? <EmptyState title="正在读取歌舞剧资料" text="请稍候，系统正在加载剧本和模型配置。" /> : null}
      {!loading && scripts.length === 0 ? (
        <EmptyState title="还没有可用剧本" text="请先生成并保存一份歌舞剧剧本，再创建唱段适配。" />
      ) : null}

      {!loading && scripts.length > 0 ? (
        <form className="lesson-layout" onSubmit={submitSongAdaptation}>
          <Card className="surface-panel input-panel">
            <CardHeader>
              <CardTitle>选择剧本与唱段素材</CardTitle>
              <CardDescription>系统会读取剧本确认稿，并用第一幕和角色列表填充基础信息。</CardDescription>
            </CardHeader>
            <CardContent>
              <FieldGroup>
                <Field data-disabled={loadingScript || taskInProgress || undefined}>
                  <FieldLabel htmlFor={scriptSelectId}>歌舞剧剧本</FieldLabel>
                  <Select value={form.script_id} onValueChange={(value) => void changeScript(value)} disabled={loadingScript || taskInProgress}>
                    <SelectTrigger id={scriptSelectId} className="w-full bg-card">
                      <SelectValue placeholder="选择剧本" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        {scripts.map((script) => (
                          <SelectItem key={script.id} value={script.id}>
                            {script.title}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </Field>
                <TextareaField label="关联剧情段落" rows={3} value={form.related_scene} onChange={(value) => updateForm("related_scene", value)} />
                <TextareaField label="原曲 / 音乐来源" rows={2} required={false} value={form.source_song} onChange={(value) => updateForm("source_song", value)} />
                <TextareaField label="原歌词" rows={6} value={form.lyrics_text} onChange={(value) => updateForm("lyrics_text", value)} />
                <TextareaField label="音乐段落表" rows={6} value={form.music_structure} onChange={(value) => updateForm("music_structure", value)} />
              </FieldGroup>
            </CardContent>
          </Card>

          <Card className="surface-panel result-panel">
            <CardHeader>
              <CardTitle>设置改编目标并生成</CardTitle>
              <CardDescription>明确剧情表达、演唱分工和改写强度，再交给模型生成结构化唱段建议。</CardDescription>
            </CardHeader>
            <CardContent>
              <FieldGroup>
                <TextareaField label="改写目标" rows={4} value={form.adaptation_goal} onChange={(value) => updateForm("adaptation_goal", value)} />
                <TextareaField label="演唱角色" rows={3} value={form.singing_roles} onChange={(value) => updateForm("singing_roles", value)} />
                <Field>
                  <FieldLabel htmlFor={rewriteIntensityId}>改写强度</FieldLabel>
                  <Select value={form.rewrite_intensity} onValueChange={(value) => updateForm("rewrite_intensity", value as SongAdaptationRewriteIntensity)}>
                    <SelectTrigger id={rewriteIntensityId} className="w-full bg-card">
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
                  provider={form.llm_provider}
                  model={form.llm_model}
                  reasoningLevel={form.reasoning_level}
                  llmOptions={llmOptions}
                  selectedModelOptions={selectedModelOptions}
                  onProviderChange={(providerId) => changeProvider(providerId as SongAdaptationForm["llm_provider"])}
                  onModelChange={(modelId) => updateForm("llm_model", modelId)}
                  onReasoningLevelChange={(level) => updateForm("reasoning_level", level as SongAdaptationForm["reasoning_level"])}
                />
                <TaskProgress task={task} />
              </FieldGroup>
            </CardContent>
            <CardFooter>
              <Button
                className="w-full"
                type="submit"
                data-busy={submitting || taskInProgress ? "true" : undefined}
                disabled={submitting || taskInProgress || loadingScript || !llmOptions || selectedProvider?.configured === false}
              >
                {submitting ? "正在提交任务……" : taskInProgress ? "唱段适配生成中……" : "生成唱段适配"}
              </Button>
            </CardFooter>
          </Card>
        </form>
      ) : null}
    </main>
  );

  function updateForm<Key extends keyof SongAdaptationForm>(key: Key, value: SongAdaptationForm[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function changeProvider(providerId: SongAdaptationForm["llm_provider"]) {
    const provider = llmOptions?.providers.find((item) => item.id === providerId);
    const defaultModel = provider?.models[0]?.id ?? form.llm_model;
    setForm((current) => ({ ...current, llm_provider: providerId, llm_model: defaultModel }));
  }

  function showStatus(nextMessage: string) {
    setMessageType("status");
    setMessage(nextMessage);
  }

  function showError(nextMessage: string) {
    setMessageType("error");
    setMessage(nextMessage);
  }
}
