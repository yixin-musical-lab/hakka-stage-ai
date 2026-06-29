import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { MusicalScriptEditor } from "../components/musical/MusicalScriptEditor";
import { TaskProgress } from "../components/lesson-plans/TaskProgress";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { NumberField, TextareaField } from "../components/ui/FormFields";
import { LlmSettings } from "../components/ui/LlmSettings";
import { PageTitle } from "../components/ui/PageTitle";
import {
  createRoleTrainingTask,
  fetchAiTask,
  fetchLlmOptions,
  fetchMusicalScript,
  updateMusicalScript,
} from "../lib/api";
import { downloadMusicalScriptMarkdown } from "../lib/download";
import { initialRoleTrainingForm } from "../lib/lessonPlanDefaults";
import type {
  AiTaskResponse,
  LlmOptionsResponse,
  MusicalScriptContent,
  MusicalScriptResponse,
  RoleTrainingForm,
} from "../types";

export function MusicalScriptDetailPage() {
  const { musicalScriptId } = useParams();
  const navigate = useNavigate();
  const [musicalScript, setMusicalScript] = useState<MusicalScriptResponse | null>(null);
  const [editedContent, setEditedContent] = useState<MusicalScriptContent | null>(null);
  const [roleForm, setRoleForm] = useState<RoleTrainingForm | null>(null);
  const [llmOptions, setLlmOptions] = useState<LlmOptionsResponse | null>(null);
  const [task, setTask] = useState<AiTaskResponse | null>(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submittingRoleTraining, setSubmittingRoleTraining] = useState(false);
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
        setEditedContent(detail.edited_content ?? detail.content);
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
        setOpeningTrainingPlan(true);
        setNotice("训练计划已生成，正在打开详情页。");
        redirectTimer.current = window.setTimeout(() => {
          navigate(`/role-training-plans/${nextTask.result_id}`);
        }, 1100);
      }
      if (nextTask.status === "FAILED") {
        setNotice(nextTask.error_message ?? "分角色训练计划生成失败，请检查 Worker、Redis 或 LLM 配置。");
      }
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "查询任务失败。");
    }
  }

  const selectedProvider = roleForm ? llmOptions?.providers.find((provider) => provider.id === roleForm.llm_provider) : undefined;
  const selectedModelOptions = selectedProvider?.models ?? [];
  const taskInProgress = task?.status === "PENDING" || task?.status === "RUNNING";

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="剧本详情"
        title={musicalScript?.title ?? "读取剧本"}
        description="查看、继续修改并导出编导确认稿，也可以基于当前剧本生成分角色训练计划。"
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
              {saving ? "保存中..." : "保存编辑稿"}
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
                  selectedModelOptions={selectedModelOptions}
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
                  disabled={submittingRoleTraining || taskInProgress || openingTrainingPlan || !llmOptions || selectedProvider?.configured === false}
                >
                  {submittingRoleTraining
                    ? "正在提交任务..."
                    : taskInProgress
                      ? "训练计划生成中..."
                      : openingTrainingPlan
                        ? "正在打开训练计划..."
                        : "生成训练计划"}
                </Button>
                {openingTrainingPlan ? <p className="redirect-hint">训练计划已生成，正在打开详情页...</p> : null}
                <TaskProgress task={task} />
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

  function changeRoleProvider(providerId: RoleTrainingForm["llm_provider"]) {
    const provider = llmOptions?.providers.find((item) => item.id === providerId);
    const defaultModel = provider?.models[0]?.id ?? roleForm?.llm_model ?? "";
    setRoleForm((current) => (current ? { ...current, llm_provider: providerId, llm_model: defaultModel } : current));
  }
}
