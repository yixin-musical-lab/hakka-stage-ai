import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { TaskProgress } from "../components/lesson-plans/TaskProgress";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "../components/ui/field";
import { NumberField, TextareaField, TextField } from "../components/ui/FormFields";
import { LlmSettings } from "../components/ui/LlmSettings";
import { PageTitle } from "../components/ui/PageTitle";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "../components/ui/toggle-group";
import {
  createMusicalFusionTask,
  fetchAiTask,
  fetchLlmOptions,
  fetchMusicalScripts,
  fetchSongAdaptations,
} from "../lib/api";
import { initialMusicalFusionForm } from "../lib/lessonPlanDefaults";
import type {
  AiTaskResponse,
  LlmOptionsResponse,
  MusicalFusionForm,
  MusicalFusionSourceMode,
  MusicalScriptSummary,
  SongAdaptationSummary,
} from "../types";

export function MusicalFusionGeneratePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const scriptSelectId = useId();
  const sourceModeLabelId = useId();
  const adaptationSelectId = useId();
  const [scripts, setScripts] = useState<MusicalScriptSummary[]>([]);
  const [songAdaptations, setSongAdaptations] = useState<SongAdaptationSummary[]>([]);
  const [form, setForm] = useState<MusicalFusionForm>(() => initialMusicalFusionForm(""));
  const [llmOptions, setLlmOptions] = useState<LlmOptionsResponse | null>(null);
  const [task, setTask] = useState<AiTaskResponse | null>(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const pollingTaskId = useRef<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([fetchMusicalScripts(controller.signal), fetchSongAdaptations(controller.signal), fetchLlmOptions(controller.signal)])
      .then(([scriptRows, adaptationRows, options]) => {
        setScripts(scriptRows);
        setSongAdaptations(adaptationRows);
        setLlmOptions(options);

        const requestedScriptId = searchParams.get("script_id");
        const scriptId = scriptRows.some((item) => item.id === requestedScriptId) ? requestedScriptId! : (scriptRows[0]?.id ?? "");
        const matchingAdaptations = adaptationRows.filter((item) => item.script_id === scriptId);
        const requestedAdaptationId = searchParams.get("song_adaptation_id");
        const selectedAdaptation =
          matchingAdaptations.find((item) => item.id === requestedAdaptationId) ?? matchingAdaptations[0] ?? null;
        const nextForm = initialMusicalFusionForm(scriptId, selectedAdaptation?.id ?? null);
        setForm({
          ...nextForm,
          related_scene: selectedAdaptation?.related_scene || nextForm.related_scene,
          llm_provider: options.default_provider,
          llm_model: options.default_model,
          reasoning_level: options.default_reasoning_level,
        });
      })
      .catch((caughtError) => {
        if (caughtError instanceof DOMException && caughtError.name === "AbortError") {
          return;
        }
        setNotice(caughtError instanceof Error ? caughtError.message : "读取剧本和唱段来源失败。");
      })
      .finally(() => setLoading(false));
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

  const matchingAdaptations = useMemo(
    () => songAdaptations.filter((item) => item.script_id === form.script_id),
    [form.script_id, songAdaptations],
  );
  const selectedProvider = llmOptions?.providers.find((provider) => provider.id === form.llm_provider);
  const selectedModelOptions = selectedProvider?.models ?? [];
  const selectedAdaptation = matchingAdaptations.find((item) => item.id === form.song_adaptation_id) ?? null;
  const taskInProgress = task?.status === "PENDING" || task?.status === "RUNNING";
  const sourceReady = form.source_mode === "manual" || Boolean(form.song_adaptation_id);

  async function submitMusicalFusion(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || taskInProgress || !form.script_id || !sourceReady) {
      return;
    }
    setSubmitting(true);
    setNotice("");
    setTask(null);
    pollingTaskId.current = null;
    try {
      const created = await createMusicalFusionTask(form);
      pollingTaskId.current = created.task_id;
      setNotice("歌舞融合任务已提交，生成完成后会自动打开详情页。");
      await refreshTask(created.task_id);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "提交歌舞融合任务失败。");
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
        setNotice("歌舞融合方案已生成，正在打开详情页。");
        navigate(`/musical-fusion-plans/${nextTask.result_id}`);
      }
      if (nextTask.status === "FAILED") {
        setNotice(nextTask.error_message ?? "歌舞融合生成失败，请检查 Worker、Redis 或 LLM 配置。");
      }
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "查询任务失败。");
    }
  }

  function changeScript(scriptId: string) {
    const firstAdaptation = songAdaptations.find((item) => item.script_id === scriptId) ?? null;
    const nextForm = initialMusicalFusionForm(scriptId, firstAdaptation?.id ?? null);
    setForm({
      ...nextForm,
      related_scene: firstAdaptation?.related_scene || nextForm.related_scene,
      llm_provider: form.llm_provider,
      llm_model: form.llm_model,
      reasoning_level: form.reasoning_level,
    });
  }

  function changeSourceMode(sourceMode: MusicalFusionSourceMode) {
    if (sourceMode === "song_adaptation") {
      const firstAdaptation = matchingAdaptations[0];
      if (!firstAdaptation) {
        return;
      }
      setForm((current) => ({
        ...current,
        source_mode: "song_adaptation",
        song_adaptation_id: firstAdaptation.id,
        related_scene: firstAdaptation.related_scene || current.related_scene,
        manual_music_title: "",
        manual_music_structure: "",
        manual_lyrics_summary: "",
      }));
      return;
    }
    const manualDefaults = initialMusicalFusionForm(form.script_id);
    setForm((current) => ({
      ...current,
      source_mode: "manual",
      song_adaptation_id: null,
      manual_music_title: current.manual_music_title || manualDefaults.manual_music_title,
      manual_music_structure: current.manual_music_structure || manualDefaults.manual_music_structure,
      manual_lyrics_summary: current.manual_lyrics_summary || manualDefaults.manual_lyrics_summary,
    }));
  }

  function selectSongAdaptation(songAdaptationId: string) {
    const adaptation = matchingAdaptations.find((item) => item.id === songAdaptationId);
    setForm((current) => ({
      ...current,
      song_adaptation_id: songAdaptationId,
      related_scene: adaptation?.related_scene || current.related_scene,
    }));
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="M04 歌舞融合"
        title="生成歌舞融合结构建议"
        description="把剧情、唱段、舞蹈状态和队形串成编导可修改、可排练的段落结构。"
        action={
          <Button variant="secondary" type="button" onClick={() => navigate("/musical-fusion-plans")}>
            已保存的方案
          </Button>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取歌舞剧资料" text="请稍候，系统正在加载剧本、唱段和模型配置。" /> : null}
      {!loading && scripts.length === 0 ? (
        <EmptyState title="还没有可用剧本" text="请先生成并保存一份歌舞剧剧本，再设计歌舞融合结构。" />
      ) : null}

      {!loading && scripts.length > 0 ? (
        <form className="lesson-layout" onSubmit={submitMusicalFusion}>
          <Card className="surface-panel input-panel">
            <CardHeader>
              <CardTitle>选择剧情与唱段来源</CardTitle>
              <CardDescription>M03 确认稿优先；没有唱段适配时可以使用手工音乐段落表。</CardDescription>
            </CardHeader>
            <CardContent>
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor={scriptSelectId}>歌舞剧剧本</FieldLabel>
                  <Select value={form.script_id} onValueChange={changeScript}>
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

                <Field>
                  <FieldLabel id={sourceModeLabelId}>唱段来源</FieldLabel>
                  <ToggleGroup
                    type="single"
                    variant="outline"
                    value={form.source_mode}
                    onValueChange={(value) => value && changeSourceMode(value as MusicalFusionSourceMode)}
                    aria-labelledby={sourceModeLabelId}
                  >
                    <ToggleGroupItem value="song_adaptation" disabled={matchingAdaptations.length === 0}>
                      引用 M03
                    </ToggleGroupItem>
                    <ToggleGroupItem value="manual">手工音乐段落</ToggleGroupItem>
                  </ToggleGroup>
                  <FieldDescription>
                    {matchingAdaptations.length > 0
                      ? `当前剧本有 ${matchingAdaptations.length} 份唱段适配可引用。`
                      : "当前剧本没有唱段适配，已使用手工输入模式。"}
                  </FieldDescription>
                </Field>

                {form.source_mode === "song_adaptation" ? (
                  <Field>
                    <FieldLabel htmlFor={adaptationSelectId}>唱段适配确认稿</FieldLabel>
                    <Select value={form.song_adaptation_id ?? ""} onValueChange={selectSongAdaptation}>
                      <SelectTrigger id={adaptationSelectId} className="w-full bg-card">
                        <SelectValue placeholder="选择唱段适配" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          {matchingAdaptations.map((adaptation) => (
                            <SelectItem key={adaptation.id} value={adaptation.id}>
                              {adaptation.title}
                            </SelectItem>
                          ))}
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                    {selectedAdaptation ? (
                      <FieldDescription>
                        {selectedAdaptation.source_song || "未标注原曲"} · {selectedAdaptation.related_scene}
                      </FieldDescription>
                    ) : null}
                  </Field>
                ) : (
                  <FieldGroup>
                    <TextField label="音乐名称 / 来源" value={form.manual_music_title} onChange={(value) => updateForm("manual_music_title", value)} />
                    <TextareaField label="音乐段落表" rows={6} value={form.manual_music_structure} onChange={(value) => updateForm("manual_music_structure", value)} />
                    <TextareaField label="歌词或唱段摘要" rows={4} value={form.manual_lyrics_summary} onChange={(value) => updateForm("manual_lyrics_summary", value)} />
                  </FieldGroup>
                )}

                <TextareaField label="关联剧情段落" rows={3} value={form.related_scene} onChange={(value) => updateForm("related_scene", value)} />
              </FieldGroup>
            </CardContent>
          </Card>

          <Card className="surface-panel result-panel">
            <CardHeader>
              <CardTitle>排演条件与生成设置</CardTitle>
              <CardDescription>方案会按实际人数、空间和安全限制控制队形与动作强度。</CardDescription>
            </CardHeader>
            <CardContent>
              <FieldGroup>
                <div className="field-grid">
                  <NumberField label="演员人数" value={form.actor_count} onChange={(value) => updateForm("actor_count", value)} />
                  <TextField label="舞台空间" value={form.stage_space} onChange={(value) => updateForm("stage_space", value)} />
                </div>
                <TextareaField label="歌舞融合目标" rows={4} value={form.fusion_goal} onChange={(value) => updateForm("fusion_goal", value)} />
                <TextareaField label="补充限制" rows={4} value={form.additional_constraints} onChange={(value) => updateForm("additional_constraints", value)} />
                <LlmSettings
                  provider={form.llm_provider}
                  model={form.llm_model}
                  reasoningLevel={form.reasoning_level}
                  llmOptions={llmOptions}
                  selectedModelOptions={selectedModelOptions}
                  onProviderChange={(providerId) => changeProvider(providerId as MusicalFusionForm["llm_provider"])}
                  onModelChange={(modelId) => updateForm("llm_model", modelId)}
                  onReasoningLevelChange={(level) => updateForm("reasoning_level", level as MusicalFusionForm["reasoning_level"])}
                />
                <TaskProgress task={task} />
              </FieldGroup>
            </CardContent>
            <CardFooter>
              <Button
                className="w-full"
                type="submit"
                data-busy={submitting || taskInProgress ? "true" : undefined}
                disabled={submitting || taskInProgress || !sourceReady || !llmOptions || selectedProvider?.configured === false}
              >
                {submitting ? "正在提交任务..." : taskInProgress ? "歌舞融合生成中..." : "生成歌舞融合方案"}
              </Button>
            </CardFooter>
          </Card>
        </form>
      ) : null}
    </main>
  );

  function updateForm<Key extends keyof MusicalFusionForm>(key: Key, value: MusicalFusionForm[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function changeProvider(providerId: MusicalFusionForm["llm_provider"]) {
    const provider = llmOptions?.providers.find((item) => item.id === providerId);
    const defaultModel = provider?.models[0]?.id ?? form.llm_model;
    setForm((current) => ({ ...current, llm_provider: providerId, llm_model: defaultModel }));
  }
}
