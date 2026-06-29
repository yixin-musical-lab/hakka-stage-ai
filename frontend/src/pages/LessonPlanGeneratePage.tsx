import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { LessonEditor } from "../components/lesson-plans/LessonEditor";
import { TaskProgress } from "../components/lesson-plans/TaskProgress";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { NumberField, TextareaField, TextField } from "../components/ui/FormFields";
import { LlmSettings } from "../components/ui/LlmSettings";
import { PageTitle } from "../components/ui/PageTitle";
import { createLessonPlanTask, fetchAiTask, fetchLessonPlan, fetchLlmOptions, updateLessonPlan } from "../lib/api";
import { initialLessonPlanForm } from "../lib/lessonPlanDefaults";
import type { AiTaskResponse, LessonPlanContent, LessonPlanForm, LessonPlanResponse, LlmOptionsResponse } from "../types";

export function LessonPlanGeneratePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<LessonPlanForm>(initialLessonPlanForm);
  const [task, setTask] = useState<AiTaskResponse | null>(null);
  const [lessonPlan, setLessonPlan] = useState<LessonPlanResponse | null>(null);
  const [editedContent, setEditedContent] = useState<LessonPlanContent | null>(null);
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
        if (caughtError instanceof DOMException && caughtError.name === "AbortError") {
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

  const canSave = useMemo(() => Boolean(editedContent && lessonPlan), [editedContent, lessonPlan]);
  const taskInProgress = task?.status === "PENDING" || task?.status === "RUNNING";
  const selectedProvider = llmOptions?.providers.find((provider) => provider.id === form.llm_provider);
  const selectedModelOptions = selectedProvider?.models ?? [];

  async function submitLessonPlan(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || taskInProgress) {
      return;
    }
    setSubmitting(true);
    setNotice("");
    setTask(null);
    setLessonPlan(null);
    setEditedContent(null);
    pollingTaskId.current = null;

    try {
      const created = await createLessonPlanTask(form);
      // 先记录当前任务 ID，再立即刷新任务状态；否则连续生成时可能被上一轮轮询 ID 拦截。
      pollingTaskId.current = created.task_id;
      setNotice("教案任务已提交，Worker 正在调用所选模型生成初稿。");
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
        await loadLessonPlan(nextTask.result_id);
        setNotice("教案初稿已生成，可以编辑、保存或进入详情页继续处理。");
      }
      if (nextTask.status === "FAILED") {
        setNotice(nextTask.error_message ?? "教案生成失败，请检查 Worker、Redis 或 LLM 配置。");
      }
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "查询任务失败。");
    }
  }

  async function loadLessonPlan(lessonPlanId: string) {
    const detail = await fetchLessonPlan(lessonPlanId);
    setLessonPlan(detail);
    setEditedContent(detail.edited_content ?? detail.content);
  }

  async function saveLessonPlan() {
    if (!lessonPlan || !editedContent) {
      return;
    }

    setSaving(true);
    setNotice("");
    try {
      const updated = await updateLessonPlan(lessonPlan.id, editedContent);
      setLessonPlan(updated);
      setEditedContent(updated.edited_content ?? updated.content);
      setNotice("老师编辑稿已保存，可从已保存教案列表再次打开。");
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "保存失败。");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="课前备课"
        title="AI 教案生成"
        description="输入课程条件后创建异步任务，生成完成后可直接编辑保存。"
        action={
          <Button variant="secondary" type="button" onClick={() => navigate("/lesson-plans")}>
            已保存的教案
          </Button>
        }
      />

      <section className="lesson-layout">
        <Card asChild className="surface-panel input-panel">
          <form onSubmit={submitLessonPlan}>
            <div className="section-heading">
              <div>
                <p className="section-kicker">课程条件</p>
                <h2>生成一份课堂初稿</h2>
              </div>
              <Button variant="secondary" type="button" onClick={fillExampleCourse}>
                填入示例
              </Button>
            </div>

            <div className="field-grid">
              <TextField label="舞种 / 方向" value={form.dance_style} onChange={(value) => updateForm("dance_style", value)} />
              <TextField label="课程主题" value={form.theme} onChange={(value) => updateForm("theme", value)} />
              <TextField label="年龄段" value={form.age_group} onChange={(value) => updateForm("age_group", value)} />
              <NumberField label="课时分钟" value={form.duration_minutes} onChange={(value) => updateForm("duration_minutes", value)} />
              <NumberField label="学生人数" value={form.student_count} onChange={(value) => updateForm("student_count", value)} />
              <TextField label="学员基础" value={form.learning_level} onChange={(value) => updateForm("learning_level", value)} />
            </div>

            <LlmSettings
              provider={form.llm_provider}
              model={form.llm_model}
              reasoningLevel={form.reasoning_level}
              llmOptions={llmOptions}
              selectedModelOptions={selectedModelOptions}
              onProviderChange={(providerId) => changeProvider(providerId as LessonPlanForm["llm_provider"])}
              onModelChange={(modelId) => updateForm("llm_model", modelId)}
              onReasoningLevelChange={(level) => updateForm("reasoning_level", level as LessonPlanForm["reasoning_level"])}
            />

            <TextField label="课程风格" value={form.course_style} onChange={(value) => updateForm("course_style", value)} />
            <TextareaField label="教学目标" value={form.teaching_goal} onChange={(value) => updateForm("teaching_goal", value)} />
            <TextareaField label="注意事项" value={form.notes} onChange={(value) => updateForm("notes", value)} />

            <Button
              className="w-full"
              type="submit"
              data-busy={submitting || taskInProgress ? "true" : undefined}
              disabled={submitting || taskInProgress || !llmOptions || selectedProvider?.configured === false}
            >
              {submitting ? "正在提交任务..." : taskInProgress ? "教案生成中..." : "生成教案"}
            </Button>
          </form>
        </Card>

        <Card asChild className="surface-panel result-panel">
          <section aria-live="polite">
            <div className="section-heading">
              <div>
                <p className="section-kicker">生成结果</p>
                <h2>{editedContent?.title ?? "等待生成教案"}</h2>
              </div>
              <div className="button-row">
                {lessonPlan ? (
                  <Button variant="secondary" type="button" onClick={() => navigate(`/lesson-plans/${lessonPlan.id}`)}>
                    打开详情
                  </Button>
                ) : null}
                <Button variant="secondary" type="button" disabled={!canSave || saving} onClick={() => void saveLessonPlan()}>
                  {saving ? "保存中..." : "保存编辑稿"}
                </Button>
              </div>
            </div>

            <TaskProgress task={task} />
            {notice ? <p className="notice">{notice}</p> : null}

            {editedContent ? (
              <LessonEditor content={editedContent} onChange={setEditedContent} modelInfo={lessonPlan?.raw_model_info ?? null} />
            ) : (
              <EmptyState title="还没有教案初稿" text="提交任务后，生成完成的结构化教案会显示在这里。" />
            )}
          </section>
        </Card>
      </section>
    </main>
  );

  function updateForm<Key extends keyof LessonPlanForm>(key: Key, value: LessonPlanForm[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function changeProvider(providerId: LessonPlanForm["llm_provider"]) {
    const provider = llmOptions?.providers.find((item) => item.id === providerId);
    const defaultModel = provider?.models[0]?.id ?? form.llm_model;
    setForm((current) => ({ ...current, llm_provider: providerId, llm_model: defaultModel }));
  }

  function fillExampleCourse() {
    // 示例按钮只重置课程内容，保留老师当前选择的供应商、模型和推理强度。
    setForm((current) => ({
      ...initialLessonPlanForm,
      llm_provider: current.llm_provider,
      llm_model: current.llm_model,
      reasoning_level: current.reasoning_level,
    }));
  }
}
