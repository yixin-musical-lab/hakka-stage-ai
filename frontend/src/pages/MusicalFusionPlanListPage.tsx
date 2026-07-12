import { useEffect, useState } from "react";
import { Link } from "react-router";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { deleteMusicalFusionPlan, fetchMusicalFusionPlans } from "../lib/api";
import { downloadMusicalFusionMarkdown } from "../lib/download";
import { formatDateTime } from "../lib/format";
import type { MusicalFusionPlanSummary } from "../types";

export function MusicalFusionPlanListPage() {
  const [plans, setPlans] = useState<MusicalFusionPlanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchMusicalFusionPlans(controller.signal)
      .then((data) => {
        setPlans(data);
        setNotice("");
      })
      .catch((caughtError) => setNotice(caughtError instanceof Error ? caughtError.message : "读取歌舞融合方案失败。"))
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  async function handleDownload(plan: MusicalFusionPlanSummary) {
    try {
      setNotice("");
      await downloadMusicalFusionMarkdown(plan.id, plan.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  async function handleDelete(plan: MusicalFusionPlanSummary) {
    if (!window.confirm(`确认删除“${plan.title}”吗？删除后无法在列表中恢复。`)) {
      return;
    }
    try {
      setDeletingId(plan.id);
      setNotice("");
      await deleteMusicalFusionPlan(plan.id);
      setPlans((current) => current.filter((item) => item.id !== plan.id));
      setNotice(`已删除歌舞融合方案：${plan.title}`);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "删除歌舞融合方案失败。");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="M04 编导资料库"
        title="歌舞融合方案"
        description="查看、继续编辑并导出已生成的唱跳、队形、衔接和排练结构。"
        action={
          <Button asChild>
            <Link to="/musical-fusion-plans/generate">新建歌舞融合方案</Link>
          </Button>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取歌舞融合方案" text="请稍候，系统正在从后端加载已保存内容。" /> : null}
      {!loading && plans.length === 0 ? (
        <EmptyState title="还没有保存的歌舞融合方案" text="选择一份剧本和唱段适配，生成第一份编导结构建议。" />
      ) : null}

      <section className="lesson-list" aria-label="歌舞融合方案列表">
        {plans.map((plan) => (
          <Card asChild className="lesson-list-item" key={plan.id}>
            <article>
              <div>
                <div className="readable-chip-row">
                  <Badge variant="secondary">{plan.status}</Badge>
                  <Badge variant="outline">{plan.source_mode === "song_adaptation" ? "引用 M03" : "手工段落"}</Badge>
                </div>
                <h2>{plan.title}</h2>
                <p>
                  剧情：{plan.related_scene}
                  {plan.music_title ? ` · 音乐：${plan.music_title}` : ""}
                </p>
                <p>
                  更新时间：{formatDateTime(plan.updated_at)}
                  {plan.model ? ` · ${plan.provider ?? "model"} / ${plan.model}` : ""}
                  {plan.reasoning_level ? ` / ${plan.reasoning_level}` : ""}
                </p>
              </div>
              <div className="button-row">
                <Button asChild variant="secondary">
                  <Link to={`/musical-fusion-plans/${plan.id}`}>查看</Link>
                </Button>
                <Button variant="secondary" type="button" onClick={() => void handleDownload(plan)}>
                  导出 Markdown
                </Button>
                <Button variant="destructive" type="button" disabled={deletingId === plan.id} onClick={() => void handleDelete(plan)}>
                  {deletingId === plan.id ? "删除中" : "删除"}
                </Button>
              </div>
            </article>
          </Card>
        ))}
      </section>
    </main>
  );
}
