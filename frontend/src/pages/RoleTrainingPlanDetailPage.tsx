import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { RoleTrainingEditor } from "../components/musical/RoleTrainingEditor";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { fetchRoleTrainingPlan, updateRoleTrainingPlan } from "../lib/api";
import { downloadRoleTrainingMarkdown } from "../lib/download";
import type { RoleTrainingContent, RoleTrainingPlanResponse } from "../types";

export function RoleTrainingPlanDetailPage() {
  const { roleTrainingPlanId } = useParams();
  const navigate = useNavigate();
  const [plan, setPlan] = useState<RoleTrainingPlanResponse | null>(null);
  const [editedContent, setEditedContent] = useState<RoleTrainingContent | null>(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

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
              <Button variant="secondary" type="button" onClick={() => void handleDownloadMarkdown()}>
                导出 Markdown
              </Button>
            ) : null}
            <Button type="button" disabled={!editedContent || saving} onClick={() => void savePlan()}>
              {saving ? "保存中..." : "保存全部修改"}
            </Button>
          </div>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取训练计划" text="请稍候，系统正在读取训练计划详情。" /> : null}

      {editedContent ? (
        <Card asChild className="surface-panel">
          <section>
            <RoleTrainingEditor content={editedContent} onChange={setEditedContent} modelInfo={plan?.raw_model_info ?? null} />
          </section>
        </Card>
      ) : !loading ? (
        <EmptyState title="训练计划内容不可用" text="这份训练计划可能尚未生成成功，暂时无法编辑或导出。" />
      ) : null}
    </main>
  );
}
