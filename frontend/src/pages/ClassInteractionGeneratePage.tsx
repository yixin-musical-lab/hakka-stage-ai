import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { ClassInteractionEditor, PhaseField } from "../components/class-interactions/ClassInteractionEditor";
import { TaskProgress } from "../components/lesson-plans/TaskProgress";
import { Badge } from "../components/ui/badge";
import { StudioLayout } from "../components/studio/StudioLayout";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { NumberField, TextareaField, TextField } from "../components/ui/FormFields";
import { LlmSettings } from "../components/ui/LlmSettings";
import { PageTitle } from "../components/ui/PageTitle";
import {
  createClassInteractionTask,
  fetchAiTask,
  fetchClassInteraction,
  fetchLessonInteractionPrefill,
  fetchLlmOptions,
  isAbortError,
  updateClassInteraction,
} from "../lib/api";
import { initialClassInteractionForm } from "../lib/lessonPlanDefaults";
import { lessonPlanVariantLabel } from "../lib/lessonPlanVariants";
import type {
  AiTaskResponse,
  ClassInteractionContent,
  ClassInteractionForm,
  ClassInteractionResponse,
  LessonInteractionPrefill,
  LlmOptionsResponse,
} from "../types";

export function ClassInteractionGeneratePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const sourceLessonPlanId = searchParams.get("lessonPlanId");
  const [form, setForm] = useState<ClassInteractionForm>(() => ({ ...initialClassInteractionForm }));
  const [task, setTask] = useState<AiTaskResponse | null>(null);
  const [interaction, setInteraction] = useState<ClassInteractionResponse | null>(null);
  const [editedContent, setEditedContent] = useState<ClassInteractionContent | null>(null);
  const [llmOptions, setLlmOptions] = useState<LlmOptionsResponse | null>(null);
  const [sourcePrefill, setSourcePrefill] = useState<LessonInteractionPrefill | null>(null);
  const [notice, setNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [saving, setSaving] = useState(false);
  const pollingTaskId = useRef<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchLlmOptions(controller.signal)
      .then((options) => {
        setLlmOptions(options);
        setForm((current) => ({ ...current, llm_provider: options.default_provider, llm_model: options.default_model, reasoning_level: options.default_reasoning_level }));
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
    if (!sourceLessonPlanId) {
      return;
    }
    const controller = new AbortController();
    void fetchLessonInteractionPrefill(sourceLessonPlanId, controller.signal)
      .then((prefill) => {
        setSourcePrefill(prefill);
        setForm((current) => ({
          ...current,
          source_lesson_plan_id: prefill.source_lesson_plan_id,
          course_theme: prefill.course_theme,
          age_group: prefill.age_group,
          student_count: prefill.student_count,
          class_style: prefill.class_style,
          space_materials: prefill.space_materials,
          lesson_context: prefill.lesson_context,
        }));
        setNotice(`已带入“${prefill.source_lesson_plan_title}”的课程条件和老师确认内容。`);
      })
      .catch((caughtError) => {
        if (isAbortError(caughtError)) {
          return;
        }
        setNotice(caughtError instanceof Error ? caughtError.message : "读取教案预填信息失败。");
      });
    return () => controller.abort();
  }, [sourceLessonPlanId]);

  useEffect(() => {
    if (!task || ["SUCCESS", "FAILED", "CANCELLED"].includes(task.status)) {
      return;
    }
    pollingTaskId.current = task.id;
    const timer = window.setInterval(() => void refreshTask(task.id), 1800);
    return () => window.clearInterval(timer);
  }, [task]);

  const taskInProgress = task?.status === "PENDING" || task?.status === "RUNNING";
  const selectedProvider = llmOptions?.providers.find((provider) => provider.id === form.llm_provider);
  const selectedModelOptions = selectedProvider?.models ?? [];
  const canSave = useMemo(() => Boolean(interaction && editedContent), [interaction, editedContent]);

  async function submitInteraction(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || taskInProgress) {
      return;
    }
    setSubmitting(true);
    setNotice("");
    setTask(null);
    setInteraction(null);
    setEditedContent(null);
    pollingTaskId.current = null;
    try {
      const created = await createClassInteractionTask(form);
      pollingTaskId.current = created.task_id;
      setNotice("课堂互动任务已提交，Worker 正在生成现场执行方案。");
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
        const detail = await fetchClassInteraction(nextTask.result_id);
        setInteraction(detail);
        setEditedContent(detail.edited_content ?? detail.content);
        setNotice("课堂互动初稿已生成，可以逐段编辑并保存。");
      } else if (nextTask.status === "FAILED") {
        setNotice(nextTask.error_message ?? "课堂互动生成失败，请检查 Worker、Redis 或 LLM 配置。");
      }
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "查询任务失败。");
    }
  }

  async function saveInteraction() {
    if (!interaction || !editedContent) {
      return;
    }
    setSaving(true);
    setNotice("");
    try {
      const updated = await updateClassInteraction(interaction.id, editedContent);
      setInteraction(updated);
      setEditedContent(updated.edited_content ?? updated.content);
      setNotice("老师编辑稿已保存，可从课堂互动列表再次打开。");
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "保存失败。");
    } finally {
      setSaving(false);
    }
  }

  function updateForm<Key extends keyof ClassInteractionForm>(key: Key, value: ClassInteractionForm[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function changeProvider(providerId: ClassInteractionForm["llm_provider"]) {
    const provider = llmOptions?.providers.find((item) => item.id === providerId);
    setForm((current) => ({ ...current, llm_provider: providerId, llm_model: provider?.models[0]?.id ?? current.llm_model }));
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="课堂现场"
        title="AI 课堂互动方案"
        description="生成老师可直接照着执行的规则、口令、学生动作、安全提醒和备用方案。"
        action={<Button variant="secondary" type="button" onClick={() => navigate("/interactions")}>已保存的方案</Button>}
      />

      <StudioLayout
        currentStep={interaction ? 3 : task ? 2 : 1}
        libraryTo="/interactions"
        libraryLabel="查看已保存互动方案"
      >
        <section className="lesson-layout">
        <Card asChild className="surface-panel input-panel">
          <form onSubmit={submitInteraction}>
            <div className="section-heading"><div><p className="section-kicker">课堂条件</p><h2>生成现场执行方案</h2></div></div>
            {sourcePrefill ? (
              <div className="interaction-source-banner">
                <div className="readable-chip-row">
                  <Badge>{lessonPlanVariantLabel(sourcePrefill.source_variant_type)}</Badge>
                  <Badge variant="outline">已锁定来源</Badge>
                </div>
                <strong>{sourcePrefill.source_lesson_plan_title}</strong>
                <span>下方预填内容来自此版本；生成后的课堂互动仍可独立编辑和删除。</span>
              </div>
            ) : null}
            <div className="field-grid">
              <TextField label="课程主题" value={form.course_theme} onChange={(value) => updateForm("course_theme", value)} />
              <TextField label="年龄段" value={form.age_group} onChange={(value) => updateForm("age_group", value)} />
              <PhaseField value={form.teaching_phase} onChange={(value) => updateForm("teaching_phase", value)} />
              <NumberField label="可用分钟" value={form.duration_minutes} onChange={(value) => updateForm("duration_minutes", value)} />
              <NumberField label="学生人数" value={form.student_count} onChange={(value) => updateForm("student_count", value)} />
              <TextField label="课堂风格" value={form.class_style} onChange={(value) => updateForm("class_style", value)} />
            </div>
            <LlmSettings
              provider={form.llm_provider}
              model={form.llm_model}
              reasoningLevel={form.reasoning_level}
              llmOptions={llmOptions}
              selectedModelOptions={selectedModelOptions}
              onProviderChange={(providerId) => changeProvider(providerId)}
              onModelChange={(modelId) => updateForm("llm_model", modelId)}
              onReasoningLevelChange={(level) => updateForm("reasoning_level", level)}
            />
            <TextareaField label="互动目标" value={form.interaction_goal} onChange={(value) => updateForm("interaction_goal", value)} />
            <TextareaField label="场地、材料与限制" value={form.space_materials} onChange={(value) => updateForm("space_materials", value)} />
            <TextareaField label="教案上下文" value={form.lesson_context} required={false} rows={6} onChange={(value) => updateForm("lesson_context", value)} />
            <Button className="w-full" type="submit" data-busy={submitting || taskInProgress ? "true" : undefined} disabled={submitting || taskInProgress || !llmOptions || selectedProvider?.configured === false}>
              {submitting ? "正在提交任务..." : taskInProgress ? "方案生成中..." : "生成课堂互动方案"}
            </Button>
          </form>
        </Card>

        <Card asChild className="surface-panel result-panel">
          <section aria-live="polite">
            <div className="section-heading">
              <div><p className="section-kicker">生成结果</p><h2>{editedContent?.title ?? "等待生成方案"}</h2></div>
              <div className="button-row">
                {interaction ? <Button variant="secondary" type="button" onClick={() => navigate(`/interactions/${interaction.id}`)}>打开详情</Button> : null}
                <Button variant="secondary" type="button" disabled={!canSave || saving} onClick={() => void saveInteraction()}>{saving ? "保存中..." : "保存编辑稿"}</Button>
              </div>
            </div>
            <TaskProgress task={task} />
            {notice ? <p className="notice">{notice}</p> : null}
            {editedContent ? <ClassInteractionEditor content={editedContent} onChange={setEditedContent} modelInfo={interaction?.raw_model_info ?? null} /> : <EmptyState title="还没有课堂互动初稿" text="提交任务后，生成结果会显示在这里。" />}
          </section>
        </Card>
        </section>
      </StudioLayout>
    </main>
  );
}
