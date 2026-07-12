import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { TaskProgress } from "../components/lesson-plans/TaskProgress";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "../components/ui/field";
import { NumberField, TextareaField } from "../components/ui/FormFields";
import { LlmSettings } from "../components/ui/LlmSettings";
import { PageTitle } from "../components/ui/PageTitle";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import {
  createRoleTrainingTask,
  fetchAiTask,
  fetchLlmOptions,
  fetchMusicalFusionPlans,
  fetchMusicalScripts,
} from "../lib/api";
import { initialRoleTrainingForm } from "../lib/lessonPlanDefaults";
import type {
  AiTaskResponse,
  LlmOptionsResponse,
  MusicalFusionPlanSummary,
  MusicalScriptSummary,
  RoleTrainingForm,
} from "../types";

type MessageType = "status" | "error";
const NO_FUSION_PLAN = "none";

export function RoleTrainingGeneratePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const scriptSelectId = useId();
  const fusionSelectId = useId();
  const [scripts, setScripts] = useState<MusicalScriptSummary[]>([]);
  const [fusionPlans, setFusionPlans] = useState<MusicalFusionPlanSummary[]>([]);
  const [form, setForm] = useState<RoleTrainingForm>(() => initialRoleTrainingForm(""));
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
        const [scriptRows, fusionRows, options] = await Promise.all([
          fetchMusicalScripts(controller.signal),
          fetchMusicalFusionPlans(controller.signal),
          fetchLlmOptions(controller.signal),
        ]);
        if (controller.signal.aborted) {
          return;
        }

        setScripts(scriptRows);
        setFusionPlans(fusionRows);
        setLlmOptions(options);
        if (scriptRows.length === 0) {
          return;
        }

        const requestedScriptId = searchParams.get("script_id");
        const requestedScript = scriptRows.find((item) => item.id === requestedScriptId);
        const selectedScript = requestedScript ?? scriptRows[0];
        const matchingPlans = fusionRows.filter((item) => item.script_id === selectedScript.id);
        const requestedFusionPlanId = searchParams.get("fusion_plan_id");
        const requestedFusionPlan = matchingPlans.find((item) => item.id === requestedFusionPlanId);
        const selectedFusionPlan = requestedFusionPlan ?? matchingPlans[0] ?? null;

        setForm({
          ...initialRoleTrainingForm(selectedScript.id),
          fusion_plan_id: selectedFusionPlan?.id ?? null,
          llm_provider: options.default_provider,
          llm_model: options.default_model,
          reasoning_level: options.default_reasoning_level,
        });

        const warnings: string[] = [];
        if (requestedScriptId && !requestedScript) {
          warnings.push("原链接中的剧本不可用，已选择第一份可用剧本");
        }
        if (requestedFusionPlanId && !requestedFusionPlan) {
          warnings.push(selectedFusionPlan ? "原链接中的 M04 不可用，已选择当前剧本的最新方案" : "原链接中的 M04 不可用，已改为仅使用剧本");
        }
        if (warnings.length > 0) {
          showStatus(`${warnings.join("；")}。`);
        }
      } catch (caughtError) {
        if (caughtError instanceof DOMException && caughtError.name === "AbortError") {
          return;
        }
        showError(caughtError instanceof Error ? caughtError.message : "读取剧本、歌舞融合方案和模型配置失败。");
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

  const matchingFusionPlans = useMemo(
    () => fusionPlans.filter((item) => item.script_id === form.script_id),
    [form.script_id, fusionPlans],
  );
  const selectedFusionPlan = matchingFusionPlans.find((item) => item.id === form.fusion_plan_id) ?? null;
  const selectedProvider = llmOptions?.providers.find((provider) => provider.id === form.llm_provider);
  const selectedModelOptions = selectedProvider?.models ?? [];
  const taskInProgress = task?.status === "PENDING" || task?.status === "RUNNING";

  function changeScript(scriptId: string) {
    const latestFusionPlan = fusionPlans.find((item) => item.script_id === scriptId) ?? null;
    setTask(null);
    setForm((current) => ({
      ...initialRoleTrainingForm(scriptId),
      fusion_plan_id: latestFusionPlan?.id ?? null,
      llm_provider: current.llm_provider,
      llm_model: current.llm_model,
      reasoning_level: current.reasoning_level,
    }));
    showStatus(latestFusionPlan ? "已自动选择该剧本最新的 M04 歌舞融合方案。" : "该剧本暂无 M04，将仅使用剧本生成基础训练计划。");
  }

  async function submitRoleTraining(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || taskInProgress || !form.script_id) {
      return;
    }
    setSubmitting(true);
    setTask(null);
    pollingTaskId.current = null;
    showStatus("正在提交分角色训练任务……");
    try {
      const created = await createRoleTrainingTask(form);
      pollingTaskId.current = created.task_id;
      showStatus("分角色训练任务已提交，生成完成后会自动打开详情页。");
      await refreshTask(created.task_id);
    } catch (caughtError) {
      showError(caughtError instanceof Error ? caughtError.message : "提交分角色训练任务失败。");
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
        showStatus("分角色训练计划已生成，正在打开详情页。");
        navigate(`/role-training-plans/${nextTask.result_id}`);
      } else if (nextTask.status === "FAILED") {
        showError(nextTask.error_message ?? "分角色训练生成失败，请检查 Worker、Redis 或 LLM 配置。");
      }
    } catch (caughtError) {
      showError(caughtError instanceof Error ? caughtError.message : "查询分角色训练任务失败。");
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="M05 分角色训练"
        title="生成分角色训练计划"
        description="把剧本角色和可选的 M04 歌舞融合上下文拆成按天、按角色可执行的排练任务。"
        action={
          <div className="button-row">
            {form.script_id ? (
              <Button variant="secondary" type="button" onClick={() => navigate(`/musical-scripts/${form.script_id}`)}>
                返回剧本
              </Button>
            ) : null}
            <Button variant="secondary" type="button" onClick={() => navigate("/role-training-plans")}>
              已保存的计划
            </Button>
          </div>
        }
      />

      {message ? (
        <p className="notice" role={messageType === "error" ? "alert" : "status"} aria-live={messageType === "error" ? "assertive" : "polite"}>
          {message}
        </p>
      ) : null}
      {loading ? <EmptyState title="正在读取排练资料" text="请稍候，系统正在加载剧本、歌舞融合方案和模型配置。" /> : null}
      {!loading && scripts.length === 0 ? (
        <EmptyState title="还没有可用剧本" text="请先生成并保存一份歌舞剧剧本，再创建分角色训练计划。" />
      ) : null}

      {!loading && scripts.length > 0 ? (
        <form className="lesson-layout" onSubmit={submitRoleTraining}>
          <Card className="surface-panel input-panel">
            <CardHeader>
              <CardTitle>选择剧本与排演上下文</CardTitle>
              <CardDescription>优先使用 M04 的演唱角色、舞蹈形式、队形和高潮信息，也可以只读取剧本。</CardDescription>
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
                          <SelectItem key={script.id} value={script.id}>
                            {script.title}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </Field>

                <Field data-disabled={taskInProgress || undefined}>
                  <FieldLabel htmlFor={fusionSelectId}>M04 歌舞融合上下文</FieldLabel>
                  <Select
                    value={form.fusion_plan_id ?? NO_FUSION_PLAN}
                    onValueChange={(value) => updateForm("fusion_plan_id", value === NO_FUSION_PLAN ? null : value)}
                    disabled={taskInProgress}
                  >
                    <SelectTrigger id={fusionSelectId} className="w-full bg-card">
                      <SelectValue placeholder="选择歌舞融合方案" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectItem value={NO_FUSION_PLAN}>仅使用剧本</SelectItem>
                        {matchingFusionPlans.map((plan) => (
                          <SelectItem key={plan.id} value={plan.id}>
                            {plan.title}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                  <FieldDescription>
                    {matchingFusionPlans.length > 0
                      ? `当前剧本有 ${matchingFusionPlans.length} 份歌舞融合方案可选。`
                      : "当前剧本暂无 M04，仍可生成基础训练计划。"}
                  </FieldDescription>
                </Field>

                {selectedFusionPlan ? (
                  <div className="source-summary" aria-label="已选择的歌舞融合方案">
                    <div className="readable-chip-row">
                      <Badge variant="secondary">引用 M04</Badge>
                      <Badge variant="outline">{selectedFusionPlan.music_title || "未标注音乐"}</Badge>
                    </div>
                    <strong>{selectedFusionPlan.title}</strong>
                    <p>{selectedFusionPlan.related_scene || "未标注关联剧情段落"}</p>
                  </div>
                ) : (
                  <div className="source-summary" aria-label="基础训练计划模式">
                    <Badge variant="outline">仅使用剧本</Badge>
                    <strong>生成基础训练计划</strong>
                    <p>计划会读取角色、台词和剧本结构，不使用 M04 队形与舞蹈上下文。</p>
                  </div>
                )}
              </FieldGroup>
            </CardContent>
          </Card>

          <Card className="surface-panel result-panel">
            <CardHeader>
              <CardTitle>设置排练节奏并生成</CardTitle>
              <CardDescription>训练任务会按角色区分台词、演唱、舞蹈、走位和老师检查点。</CardDescription>
            </CardHeader>
            <CardContent>
              <FieldGroup>
                <div className="field-grid">
                  <NumberField label="排练天数" value={form.rehearsal_days} onChange={(value) => updateForm("rehearsal_days", value)} />
                  <NumberField label="单次分钟" value={form.session_minutes} onChange={(value) => updateForm("session_minutes", value)} />
                </div>
                <TextareaField label="训练重点" rows={4} value={form.training_focus} onChange={(value) => updateForm("training_focus", value)} />
                <TextareaField label="补充说明" rows={4} value={form.notes} onChange={(value) => updateForm("notes", value)} />
                <LlmSettings
                  provider={form.llm_provider}
                  model={form.llm_model}
                  reasoningLevel={form.reasoning_level}
                  llmOptions={llmOptions}
                  selectedModelOptions={selectedModelOptions}
                  onProviderChange={(providerId) => changeProvider(providerId as RoleTrainingForm["llm_provider"])}
                  onModelChange={(modelId) => updateForm("llm_model", modelId)}
                  onReasoningLevelChange={(level) => updateForm("reasoning_level", level as RoleTrainingForm["reasoning_level"])}
                />
                <TaskProgress task={task} />
              </FieldGroup>
            </CardContent>
            <CardFooter>
              <Button
                className="w-full"
                type="submit"
                data-busy={submitting || taskInProgress ? "true" : undefined}
                disabled={submitting || taskInProgress || !llmOptions || selectedProvider?.configured === false}
              >
                {submitting ? "正在提交任务……" : taskInProgress ? "训练计划生成中……" : selectedFusionPlan ? "基于 M04 生成训练计划" : "生成基础训练计划"}
              </Button>
            </CardFooter>
          </Card>
        </form>
      ) : null}
    </main>
  );

  function updateForm<Key extends keyof RoleTrainingForm>(key: Key, value: RoleTrainingForm[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function changeProvider(providerId: RoleTrainingForm["llm_provider"]) {
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
