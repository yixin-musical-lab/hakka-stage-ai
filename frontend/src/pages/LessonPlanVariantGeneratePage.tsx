import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { LessonEditor } from "../components/lesson-plans/LessonEditor";
import { TaskProgress } from "../components/lesson-plans/TaskProgress";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "../components/ui/field";
import { TextareaField } from "../components/ui/FormFields";
import { LlmSettings } from "../components/ui/LlmSettings";
import { PageTitle } from "../components/ui/PageTitle";
import { ToggleGroup, ToggleGroupItem } from "../components/ui/toggle-group";
import {
  createLessonPlanVariantTask,
  fetchAiTask,
  fetchLessonPlan,
  fetchLlmOptions,
} from "../lib/api";
import {
  initialLessonPlanVariantForm,
  lessonPlanVariantOptions,
} from "../lib/lessonPlanVariants";
import type {
  AiTaskResponse,
  LessonPlanResponse,
  LessonPlanVariantForm,
  LlmOptionsResponse,
} from "../types";

export function LessonPlanVariantGeneratePage() {
  const { lessonPlanId } = useParams();
  const navigate = useNavigate();
  const [sourceLessonPlan, setSourceLessonPlan] = useState<LessonPlanResponse | null>(null);
  const [form, setForm] = useState<LessonPlanVariantForm>(() => initialLessonPlanVariantForm());
  const [llmOptions, setLlmOptions] = useState<LlmOptionsResponse | null>(null);
  const [task, setTask] = useState<AiTaskResponse | null>(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const pollingTaskId = useRef<string | null>(null);

  useEffect(() => {
    if (!lessonPlanId) {
      setNotice("缺少原教案 ID，无法创建变体。");
      setLoading(false);
      return;
    }

    let active = true;
    const controller = new AbortController();
    void Promise.all([fetchLessonPlan(lessonPlanId), fetchLlmOptions(controller.signal)])
      .then(([lessonPlan, options]) => {
        if (!active) return;
        setSourceLessonPlan(lessonPlan);
        setLlmOptions(options);
        setForm((current) => ({
          ...current,
          llm_provider: options.default_provider,
          llm_model: options.default_model,
          reasoning_level: options.default_reasoning_level,
        }));
        setNotice(lessonPlan.variant_info ? "第一版只允许从原教案创建一级变体，不能从变体继续派生。" : "");
      })
      .catch((caughtError) => {
        if (!active || controller.signal.aborted) return;
        setNotice(caughtError instanceof Error ? caughtError.message : "读取原教案或模型配置失败。");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [lessonPlanId]);

  useEffect(() => {
    if (!task || ["SUCCESS", "FAILED", "CANCELLED"].includes(task.status)) return;

    pollingTaskId.current = task.id;
    const timer = window.setInterval(() => void refreshTask(task.id), 1800);
    return () => window.clearInterval(timer);
  }, [task]);

  const sourceContent = sourceLessonPlan?.edited_content ?? sourceLessonPlan?.content ?? null;
  const taskInProgress = task?.status === "PENDING" || task?.status === "RUNNING";
  const selectedProvider = llmOptions?.providers.find((provider) => provider.id === form.llm_provider);
  const selectedModelOptions = selectedProvider?.models ?? [];
  const selectedVariant = useMemo(
    () => lessonPlanVariantOptions.find((option) => option.id === form.variant_type),
    [form.variant_type],
  );
  const canGenerate = Boolean(
    lessonPlanId && sourceContent && !sourceLessonPlan?.variant_info && llmOptions && selectedProvider?.configured !== false,
  );

  async function submitVariant(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!lessonPlanId || !canGenerate || submitting || taskInProgress) return;

    setSubmitting(true);
    setTask(null);
    setNotice("");
    pollingTaskId.current = null;
    try {
      const created = await createLessonPlanVariantTask(lessonPlanId, form);
      pollingTaskId.current = created.task_id;
      setNotice(`${selectedVariant?.label ?? "变体"}任务已提交，生成完成后会自动打开版本对照页。`);
      await refreshTask(created.task_id);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "提交变体生成任务失败。");
    } finally {
      setSubmitting(false);
    }
  }

  async function refreshTask(taskId: string) {
    try {
      const nextTask = await fetchAiTask(taskId);
      if (pollingTaskId.current && pollingTaskId.current !== nextTask.id) return;

      setTask(nextTask);
      if (nextTask.status === "SUCCESS" && nextTask.result_id) {
        navigate(`/lesson-plans/${nextTask.result_id}`, { replace: true });
      } else if (nextTask.status === "FAILED") {
        setNotice(nextTask.error_message ?? "变体生成失败，请检查 Worker、Redis 或 LLM 配置。");
      }
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "查询变体任务失败。");
    }
  }

  function updateForm<Key extends keyof LessonPlanVariantForm>(key: Key, value: LessonPlanVariantForm[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function changeProvider(providerId: LessonPlanVariantForm["llm_provider"]) {
    const provider = llmOptions?.providers.find((item) => item.id === providerId);
    setForm((current) => ({
      ...current,
      llm_provider: providerId,
      llm_model: provider?.models[0]?.id ?? current.llm_model,
    }));
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="T02 · 多版本教案"
        title="从老师确认稿生成适配版本"
        description="保留原教案作为稳定基线，选择一个明确方向生成可独立编辑、导出和用于课堂互动的新版本。"
        action={
          <Button
            variant="secondary"
            type="button"
            onClick={() => navigate(lessonPlanId ? `/lesson-plans/${lessonPlanId}` : "/lesson-plans")}
          >
            返回原教案
          </Button>
        }
      />

      {loading ? <EmptyState title="正在读取原教案" text="请稍候，系统正在准备生成基线和模型配置。" /> : null}
      {!loading && !sourceLessonPlan ? <EmptyState title="原教案不可用" text={notice || "请返回教案列表重新选择。"} /> : null}

      {!loading && sourceLessonPlan ? (
        <section className="lesson-variant-generation-layout">
          <Card asChild className="variant-control-card">
            <form onSubmit={submitVariant}>
              <CardHeader>
                <div className="readable-chip-row">
                  <Badge variant="secondary">原教案</Badge>
                  <Badge variant="outline">只生成一级变体</Badge>
                </div>
                <CardTitle>选择适配方向</CardTitle>
                <CardDescription>
                  每次生成一个独立版本；固定预设控制主要改写策略，自定义说明用于补充本班实际情况。
                </CardDescription>
              </CardHeader>

              <CardContent>
                <FieldGroup>
                  <Field>
                    <FieldLabel>版本预设</FieldLabel>
                    <ToggleGroup
                      type="single"
                      value={form.variant_type}
                      variant="outline"
                      spacing={2}
                      className="variant-preset-group"
                      aria-label="选择教案变体类型"
                      onValueChange={(value) => {
                        if (value) updateForm("variant_type", value as LessonPlanVariantForm["variant_type"]);
                      }}
                    >
                      {lessonPlanVariantOptions.map((option) => (
                        <ToggleGroupItem
                          className="variant-preset-toggle"
                          value={option.id}
                          key={option.id}
                          aria-label={`${option.label}：${option.description}`}
                        >
                          <strong>{option.label}</strong>
                          <span>{option.description}</span>
                        </ToggleGroupItem>
                      ))}
                    </ToggleGroup>
                    <FieldDescription>
                      当前策略：{selectedVariant?.description ?? "请选择一个版本方向"}。
                    </FieldDescription>
                  </Field>

                  <TextareaField
                    label="补充调整方向（可选）"
                    value={form.adjustment_direction}
                    required={false}
                    rows={5}
                    onChange={(value) => updateForm("adjustment_direction", value)}
                  />

                  <LlmSettings
                    provider={form.llm_provider}
                    model={form.llm_model}
                    reasoningLevel={form.reasoning_level}
                    llmOptions={llmOptions}
                    selectedModelOptions={selectedModelOptions}
                    onProviderChange={(providerId) => changeProvider(providerId as LessonPlanVariantForm["llm_provider"])}
                    onModelChange={(modelId) => updateForm("llm_model", modelId)}
                    onReasoningLevelChange={(level) =>
                      updateForm("reasoning_level", level as LessonPlanVariantForm["reasoning_level"])
                    }
                  />
                </FieldGroup>
              </CardContent>

              <CardFooter className="variant-control-footer">
                <Button
                  className="w-full"
                  type="submit"
                  data-busy={submitting || taskInProgress ? "true" : undefined}
                  disabled={!canGenerate || submitting || taskInProgress}
                >
                  {submitting ? "正在提交任务..." : taskInProgress ? "变体生成中..." : `生成${selectedVariant?.label ?? "变体"}`}
                </Button>
                <TaskProgress task={task} />
                {notice ? <p className="notice">{notice}</p> : null}
              </CardFooter>
            </form>
          </Card>

          <Card className="variant-source-card">
            <CardHeader>
              <div className="readable-chip-row">
                <Badge variant="outline">生成基线</Badge>
                <Badge variant="secondary">{sourceLessonPlan.status}</Badge>
              </div>
              <CardTitle>{sourceLessonPlan.title}</CardTitle>
              <CardDescription>
                下方展示当前老师确认稿。任务提交时会冻结这份内容，之后原教案继续编辑也不会改变该变体的对照基线。
              </CardDescription>
            </CardHeader>
            <CardContent className="variant-source-document">
              {sourceContent ? (
                <LessonEditor
                  content={sourceContent}
                  readOnly
                  onChange={() => undefined}
                  modelInfo={sourceLessonPlan.raw_model_info}
                />
              ) : (
                <EmptyState title="原教案正文不可用" text="请先等待原教案生成完成并保存，再创建变体。" />
              )}
            </CardContent>
          </Card>
        </section>
      ) : null}
    </main>
  );
}
