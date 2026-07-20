import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { MusicalScriptEditor } from "../components/musical/MusicalScriptEditor";
import { TaskProgress } from "../components/lesson-plans/TaskProgress";
import { StudioLayout } from "../components/studio/StudioLayout";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { NumberField, TextareaField, TextField } from "../components/ui/FormFields";
import { LlmSettings } from "../components/ui/LlmSettings";
import { PageTitle } from "../components/ui/PageTitle";
import {
  createMusicalScriptTask,
  fetchAiTask,
  fetchLlmOptions,
  fetchMusicalScript,
  isAbortError,
  updateMusicalScript,
} from "../lib/api";
import { initialMusicalScriptForm } from "../lib/lessonPlanDefaults";
import type { AiTaskResponse, LlmOptionsResponse, MusicalScriptContent, MusicalScriptForm, MusicalScriptResponse } from "../types";

export function MusicalScriptGeneratePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<MusicalScriptForm>(initialMusicalScriptForm);
  const [task, setTask] = useState<AiTaskResponse | null>(null);
  const [musicalScript, setMusicalScript] = useState<MusicalScriptResponse | null>(null);
  const [editedContent, setEditedContent] = useState<MusicalScriptContent | null>(null);
  const [llmOptions, setLlmOptions] = useState<LlmOptionsResponse | null>(null);
  const [notice, setNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [saving, setSaving] = useState(false);
  const pollingTaskId = useRef<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchLlmOptions(controller.signal)
      .then((options) => {
        setLlmOptions(options);
        setForm((current) => ({
          ...current,
          llm_provider: options.default_provider,
          llm_model: options.default_model,
          reasoning_level: options.default_reasoning_level,
        }));
      })
      .catch((caughtError) => {
        if (isAbortError(caughtError)) {
          return;
        }
        setNotice(caughtError instanceof Error ? caughtError.message : "读取模型配置失败。");
      });
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

  const canSave = useMemo(() => Boolean(editedContent && musicalScript), [editedContent, musicalScript]);
  const taskInProgress = task?.status === "PENDING" || task?.status === "RUNNING";
  const selectedProvider = llmOptions?.providers.find((provider) => provider.id === form.llm_provider);
  const selectedModelOptions = selectedProvider?.models ?? [];

  async function submitMusicalScript(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || taskInProgress) {
      return;
    }
    setSubmitting(true);
    setNotice("");
    setTask(null);
    setMusicalScript(null);
    setEditedContent(null);
    pollingTaskId.current = null;

    try {
      const created = await createMusicalScriptTask(form);
      pollingTaskId.current = created.task_id;
      setNotice("剧本任务已提交，Worker 正在调用所选模型生成初稿。");
      await refreshTask(created.task_id);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "提交任务失败。");
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
        await loadMusicalScript(nextTask.result_id);
        setNotice("剧本初稿已生成，可以编辑、保存或进入详情页继续生成分角色训练计划。");
      }
      if (nextTask.status === "FAILED") {
        setNotice(nextTask.error_message ?? "剧本生成失败，请检查 Worker、Redis 或 LLM 配置。");
      }
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "查询任务失败。");
    }
  }

  async function loadMusicalScript(musicalScriptId: string) {
    const detail = await fetchMusicalScript(musicalScriptId);
    setMusicalScript(detail);
    setEditedContent(detail.edited_content ?? detail.content);
  }

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
      setNotice("编导编辑稿已保存，可从已保存剧本列表再次打开。");
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "保存失败。");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="歌舞剧创编"
        title="AI 剧本生成"
        description="输入剧目条件后生成剧情结构、人物、台词、旁白和表演留白段落。"
        action={
          <Button variant="secondary" type="button" onClick={() => navigate("/musical-scripts")}>
            已保存的剧本
          </Button>
        }
      />

      <StudioLayout
        currentStep={musicalScript ? 3 : task ? 2 : 1}
        libraryTo="/musical-scripts"
        libraryLabel="查看已保存剧本"
      >
        <section className="lesson-layout">
        <Card asChild className="surface-panel input-panel">
          <form onSubmit={submitMusicalScript}>
            <div className="section-heading">
              <div>
                <p className="section-kicker">剧目条件</p>
                <h2>生成一份创编初稿</h2>
              </div>
              <Button variant="secondary" type="button" onClick={fillExampleScript}>
                填入示例
              </Button>
            </div>

            <div className="field-grid">
              <TextField label="剧目主题" value={form.theme} onChange={(value) => updateForm("theme", value)} />
              <NumberField label="演出分钟" value={form.duration_minutes} onChange={(value) => updateForm("duration_minutes", value)} />
              <NumberField label="演员人数" value={form.actor_count} onChange={(value) => updateForm("actor_count", value)} />
              <TextField label="年龄段" value={form.age_group} onChange={(value) => updateForm("age_group", value)} />
            </div>

            <LlmSettings
              provider={form.llm_provider}
              model={form.llm_model}
              reasoningLevel={form.reasoning_level}
              llmOptions={llmOptions}
              selectedModelOptions={selectedModelOptions}
              onProviderChange={(providerId) => changeProvider(providerId as MusicalScriptForm["llm_provider"])}
              onModelChange={(modelId) => updateForm("llm_model", modelId)}
              onReasoningLevelChange={(level) => updateForm("reasoning_level", level as MusicalScriptForm["reasoning_level"])}
            />

            <TextareaField label="风格要求" value={form.style_requirements} onChange={(value) => updateForm("style_requirements", value)} />
            <TextareaField label="必须出现的元素" value={form.required_elements} onChange={(value) => updateForm("required_elements", value)} />
            <TextareaField label="禁忌内容" value={form.forbidden_content} onChange={(value) => updateForm("forbidden_content", value)} />

            <Button
              className="w-full"
              type="submit"
              data-busy={submitting || taskInProgress ? "true" : undefined}
              disabled={submitting || taskInProgress || !llmOptions || selectedProvider?.configured === false}
            >
              {submitting ? "正在提交任务..." : taskInProgress ? "剧本生成中..." : "生成剧本"}
            </Button>
          </form>
        </Card>

        <Card asChild className="surface-panel result-panel">
          <section aria-live="polite">
            <div className="section-heading">
              <div>
                <p className="section-kicker">生成结果</p>
                <h2>{editedContent?.title ?? "等待生成剧本"}</h2>
              </div>
              <div className="button-row">
                {musicalScript ? (
                  <Button variant="secondary" type="button" onClick={() => navigate(`/musical-scripts/${musicalScript.id}`)}>
                    打开详情
                  </Button>
                ) : null}
                <Button variant="secondary" type="button" disabled={!canSave || saving} onClick={() => void saveMusicalScript()}>
                  {saving ? "保存中..." : "保存编辑稿"}
                </Button>
              </div>
            </div>

            <TaskProgress task={task} />
            {notice ? <p className="notice">{notice}</p> : null}

            {editedContent ? (
              <MusicalScriptEditor content={editedContent} onChange={setEditedContent} modelInfo={musicalScript?.raw_model_info ?? null} />
            ) : (
              <EmptyState title="还没有剧本初稿" text="提交任务后，生成完成的结构化剧本会显示在这里。" />
            )}
          </section>
        </Card>
        </section>
      </StudioLayout>
    </main>
  );

  function updateForm<Key extends keyof MusicalScriptForm>(key: Key, value: MusicalScriptForm[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function changeProvider(providerId: MusicalScriptForm["llm_provider"]) {
    const provider = llmOptions?.providers.find((item) => item.id === providerId);
    const defaultModel = provider?.models[0]?.id ?? form.llm_model;
    setForm((current) => ({ ...current, llm_provider: providerId, llm_model: defaultModel }));
  }

  function fillExampleScript() {
    setForm((current) => ({
      ...initialMusicalScriptForm,
      llm_provider: current.llm_provider,
      llm_model: current.llm_model,
      reasoning_level: current.reasoning_level,
    }));
  }
}
