import { useEffect, useState } from "react";
import { Link } from "react-router";
import { LibraryRecordCard } from "../components/library/LibraryRecordCard";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { deleteRoleTrainingPlan, fetchRoleTrainingPlans } from "../lib/api";
import { downloadRoleTrainingMarkdown } from "../lib/download";
import type { RoleTrainingPlanSummary } from "../types";

export function RoleTrainingPlanListPage() {
  const [plans, setPlans] = useState<RoleTrainingPlanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchRoleTrainingPlans(controller.signal)
      .then((data) => {
        setPlans(data);
        setNotice("");
      })
      .catch((caughtError) => setNotice(caughtError instanceof Error ? caughtError.message : "读取训练计划列表失败。"))
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  async function handleDownload(plan: RoleTrainingPlanSummary) {
    try {
      setNotice("");
      await downloadRoleTrainingMarkdown(plan.id, plan.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  async function handleDelete(plan: RoleTrainingPlanSummary) {
    const confirmed = window.confirm(`确认删除“${plan.title}”吗？删除后无法在列表中恢复。`);
    if (!confirmed) {
      return;
    }
    try {
      setDeletingId(plan.id);
      setNotice("");
      await deleteRoleTrainingPlan(plan.id);
      setPlans((current) => current.filter((item) => item.id !== plan.id));
      setNotice(`已删除训练计划：${plan.title}`);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "删除训练计划失败。");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="训练资料库"
        title="分角色训练计划"
        description="查看、继续编辑并导出已生成的角色训练计划。"
        action={
          <Button asChild>
            <Link to="/role-training-plans/generate">新建训练计划</Link>
          </Button>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取训练计划" text="请稍候，系统正在从后端加载已保存内容。" /> : null}
      {!loading && plans.length === 0 ? (
        <EmptyState title="还没有保存的训练计划" text="进入独立生成页选择剧本，并按需带入 M04 歌舞融合方案。" />
      ) : null}

      <section className="library-card-grid" aria-label="分角色训练计划列表">
        {plans.map((plan) => (
          <LibraryRecordCard
            key={plan.id}
            kind="role"
            title={plan.title}
            badges={<Badge variant="secondary">{plan.status}</Badge>}
            summaryLabel="训练用途"
            summary="分角色训练资料 · 可继续编辑、导出并生成训练卡片"
            updatedAt={plan.updated_at}
            provider={plan.provider}
            model={plan.model}
            reasoningLevel={plan.reasoning_level}
            viewTo={`/role-training-plans/${plan.id}`}
            viewLabel="查看计划"
            deleting={deletingId === plan.id}
            onDownload={() => void handleDownload(plan)}
            onDelete={() => void handleDelete(plan)}
          />
        ))}
      </section>
    </main>
  );
}
