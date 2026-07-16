import { useEffect, useState } from "react";
import { Link } from "react-router";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { downloadMarkdown } from "../lib/download";
import { deleteLessonPlan, fetchLessonPlans } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { LessonPlanSummary } from "../types";

export function LessonPlanListPage() {
  const [lessonPlans, setLessonPlans] = useState<LessonPlanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchLessonPlans(controller.signal)
      .then((data) => {
        setLessonPlans(data);
        setNotice("");
      })
      .catch((caughtError) => setNotice(caughtError instanceof Error ? caughtError.message : "读取教案列表失败。"))
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  async function handleDownload(lessonPlan: LessonPlanSummary) {
    try {
      setNotice("");
      await downloadMarkdown(lessonPlan.id, lessonPlan.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  async function handleDelete(lessonPlan: LessonPlanSummary) {
    const confirmed = window.confirm(`确认删除“${lessonPlan.title}”吗？删除后无法在列表中恢复。`);
    if (!confirmed) {
      return;
    }

    try {
      setDeletingId(lessonPlan.id);
      setNotice("");
      await deleteLessonPlan(lessonPlan.id);

      // 删除成功后只更新本地列表，避免重新请求时造成页面闪动。
      setLessonPlans((currentLessonPlans) =>
        currentLessonPlans.filter((currentLessonPlan) => currentLessonPlan.id !== lessonPlan.id),
      );
      setNotice(`已删除教案：${lessonPlan.title}`);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "删除教案失败。");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="资料库"
        title="已保存教案"
        description="重新打开老师确认稿，继续编辑或导出 Markdown。"
        action={
          <Button asChild>
            <Link to="/lesson-plans/generate">新建教案</Link>
          </Button>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取教案" text="请稍候，系统正在从后端加载已保存内容。" /> : null}

      {!loading && lessonPlans.length === 0 ? (
        <EmptyState title="还没有保存的教案" text="先生成一份教案，保存后就会出现在这里。" />
      ) : null}

      <section className="library-card-grid" aria-label="已保存教案列表">
        {lessonPlans.map((lessonPlan) => (
          <Card asChild className="library-card" key={lessonPlan.id}>
            <article>
              <CardHeader>
                <div className="readable-chip-row">
                  <Badge variant="secondary">{lessonPlan.status}</Badge>
                </div>
                <CardTitle>
                  <h2>{lessonPlan.title}</h2>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p>
                  更新时间：{formatDateTime(lessonPlan.updated_at)}
                  {lessonPlan.model ? ` · ${lessonPlan.provider ?? "model"} / ${lessonPlan.model}` : ""}
                  {lessonPlan.reasoning_level ? ` / ${lessonPlan.reasoning_level}` : ""}
                </p>
              </CardContent>
              <CardFooter className="library-card-actions">
                <Button asChild variant="secondary">
                  <Link to={`/lesson-plans/${lessonPlan.id}`}>查看</Link>
                </Button>
                <Button variant="secondary" type="button" onClick={() => void handleDownload(lessonPlan)}>
                  导出 Markdown
                </Button>
                <Button
                  variant="destructive"
                  type="button"
                  disabled={deletingId === lessonPlan.id}
                  onClick={() => void handleDelete(lessonPlan)}
                >
                  {deletingId === lessonPlan.id ? "删除中" : "删除"}
                </Button>
              </CardFooter>
            </article>
          </Card>
        ))}
      </section>
    </main>
  );
}
