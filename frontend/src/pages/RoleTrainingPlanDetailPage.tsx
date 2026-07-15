import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { RoleTrainingEditor } from "../components/musical/RoleTrainingEditor";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { fetchRoleTrainingPlan, updateRoleTrainingPlan } from "../lib/api";
import { downloadRoleTrainingCardMarkdown, downloadRoleTrainingMarkdown } from "../lib/download";
import type { RoleTrainingContent, RoleTrainingPlanResponse } from "../types";

export function RoleTrainingPlanDetailPage() {
  const { roleTrainingPlanId } = useParams();
  const navigate = useNavigate();
  const [plan, setPlan] = useState<RoleTrainingPlanResponse | null>(null);
  const [editedContent, setEditedContent] = useState<RoleTrainingContent | null>(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [exportingRoleIndex, setExportingRoleIndex] = useState<number | null>(null);

  useEffect(() => {
    if (!roleTrainingPlanId) {
      return;
    }
    void fetchRoleTrainingPlan(roleTrainingPlanId)
      .then((detail) => {
        setPlan(detail);
        setEditedContent(detail.edited_content ?? detail.content);
        setNotice("");
      })
      .catch((caughtError) => setNotice(caughtError instanceof Error ? caughtError.message : "读取训练计划失败。"))
      .finally(() => setLoading(false));
  }, [roleTrainingPlanId]);

  async function savePlan() {
    if (!plan || !editedContent) {
      return;
    }
    setSaving(true);
    setNotice("");
    try {
      const updated = await updateRoleTrainingPlan(plan.id, editedContent);
      setPlan(updated);
      setEditedContent(updated.edited_content ?? updated.content);
      setNotice("老师编辑稿已保存。");
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "保存失败。");
    } finally {
      setSaving(false);
    }
  }

  async function handleDownloadMarkdown() {
    if (!plan) {
      return;
    }
    try {
      setNotice("");
      await downloadRoleTrainingMarkdown(plan.id, plan.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  async function handleDownloadRoleCard(roleIndex: number) {
    if (!plan || !editedContent || saving || exportingRoleIndex !== null) {
      return;
    }

    setExportingRoleIndex(roleIndex);
    setNotice("");

    let updatedPlan: RoleTrainingPlanResponse;
    try {
      // 先保存页面上的全部编辑内容，确保后端按同一份确认稿索引导出。
      updatedPlan = await updateRoleTrainingPlan(plan.id, editedContent);
      setPlan(updatedPlan);
      setEditedContent(updatedPlan.edited_content ?? updatedPlan.content);
    } catch (caughtError) {
      const message = caughtError instanceof Error ? caughtError.message : "未知错误";
      setNotice(`保存失败，未导出训练卡：${message}`);
      setExportingRoleIndex(null);
      return;
    }

    try {
      const savedContent = updatedPlan.edited_content ?? updatedPlan.content;
      const roleName = savedContent?.role_tasks[roleIndex]?.role_name ?? "";
      await downloadRoleTrainingCardMarkdown(updatedPlan.id, roleIndex, updatedPlan.title, roleName);
      setNotice(`已保存并导出「${roleName.trim() || `角色${roleIndex + 1}`}」训练卡。`);
    } catch (caughtError) {
      const message = caughtError instanceof Error ? caughtError.message : "未知错误";
      setNotice(`训练计划已保存，但角色训练卡导出失败：${message}`);
    } finally {
      setExportingRoleIndex(null);
    }
  }

  async function openRehearsalReview() {
    if (!plan || !editedContent) {
      return;
    }
    try {
      // 进入 M08 前保存当前训练确认稿，确保复盘任务读取到老师刚修改的角色任务。
      await updateRoleTrainingPlan(plan.id, editedContent);
      navigate(`/rehearsal-reviews/generate?script_id=${plan.script_id}&role_training_plan_id=${plan.id}`);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "保存并打开排练复盘失败。");
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="训练计划详情"
        title={plan?.title ?? "读取训练计划"}
        description="查看、继续修改并导出老师确认稿。"
        action={
          <div className="button-row">
            <Button variant="secondary" type="button" onClick={() => navigate("/role-training-plans")}>
              返回列表
            </Button>
            {plan ? (
              <Button
                variant="secondary"
                type="button"
                disabled={exportingRoleIndex !== null}
                onClick={() => void handleDownloadMarkdown()}
              >
                导出完整计划
              </Button>
            ) : null}
            <Button type="button" disabled={!editedContent || saving || exportingRoleIndex !== null} onClick={() => void savePlan()}>
              {saving ? "保存中..." : "保存全部修改"}
            </Button>
          </div>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取训练计划" text="请稍候，系统正在读取训练计划详情。" /> : null}

      {editedContent ? (
        <>
          <Card asChild className="surface-panel">
            <section>
              <RoleTrainingEditor
                content={editedContent}
                onChange={setEditedContent}
                modelInfo={plan?.raw_model_info ?? null}
                onExportRole={(roleIndex) => void handleDownloadRoleCard(roleIndex)}
                exportingRoleIndex={exportingRoleIndex}
                actionsDisabled={saving || exportingRoleIndex !== null}
              />
            </section>
          </Card>
          <Card asChild className="surface-panel next-step-panel">
            <section>
              <div className="section-heading">
                <div>
                  <p className="section-kicker">下一步 · M08</p>
                  <h2>排练后记录问题并形成下一次计划</h2>
                  <p>复盘报告会读取本训练计划的角色任务和检查点，也可以上传一个仅供人工回看的视频附件。</p>
                </div>
                <Button type="button" disabled={saving || exportingRoleIndex !== null} onClick={() => void openRehearsalReview()}>
                  基于本计划创建复盘
                </Button>
              </div>
            </section>
          </Card>
        </>
      ) : !loading ? (
        <EmptyState title="训练计划内容不可用" text="这份训练计划可能尚未生成成功，暂时无法编辑或导出。" />
      ) : null}
    </main>
  );
}
