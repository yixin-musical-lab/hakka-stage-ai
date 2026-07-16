import { useEffect, useState } from "react";
import { Link } from "react-router";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { deleteClassInteraction, fetchClassInteractions } from "../lib/api";
import { downloadClassInteractionMarkdown } from "../lib/download";
import { formatDateTime } from "../lib/format";
import type { ClassInteractionSummary } from "../types";

export function ClassInteractionListPage() {
  const [interactions, setInteractions] = useState<ClassInteractionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchClassInteractions(controller.signal)
      .then(setInteractions)
      .catch((caughtError) => {
        if (!controller.signal.aborted) {
          setNotice(caughtError instanceof Error ? caughtError.message : "读取课堂互动列表失败。");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  async function handleDelete(interaction: ClassInteractionSummary) {
    if (!window.confirm(`确认删除“${interaction.title}”吗？来源教案不会受到影响。`)) {
      return;
    }
    try {
      setDeletingId(interaction.id);
      setNotice("");
      await deleteClassInteraction(interaction.id);
      setInteractions((current) => current.filter((item) => item.id !== interaction.id));
      setNotice(`已删除课堂互动方案：${interaction.title}`);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "删除课堂互动方案失败。");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleDownload(interaction: ClassInteractionSummary) {
    try {
      setNotice("");
      await downloadClassInteractionMarkdown(interaction.id, interaction.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  return (
    <main className="page-frame">
      <PageTitle eyebrow="课堂资料库" title="课堂互动方案" description="查看、继续编辑并导出已生成的现场执行方案。" action={<Button asChild><Link to="/interactions/generate">新建方案</Link></Button>} />
      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取课堂互动方案" text="请稍候，系统正在从后端加载已保存内容。" /> : null}
      {!loading && interactions.length === 0 ? <EmptyState title="还没有保存的课堂互动方案" text="新建一份独立方案，或从教案详情带入课程信息后生成。" /> : null}
      <section className="library-card-grid" aria-label="课堂互动方案列表">
        {interactions.map((interaction) => (
          <Card asChild className="library-card" key={interaction.id}>
            <article>
              <CardHeader>
                <div className="readable-chip-row">
                  <Badge variant="secondary">{interaction.status}</Badge>
                </div>
                <CardTitle>
                  <h2>{interaction.title}</h2>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="library-card-primary">{interaction.course_theme} · {interaction.teaching_phase} · {interaction.duration_minutes} 分钟</p>
                <p>更新时间：{formatDateTime(interaction.updated_at)}{interaction.model ? ` · ${interaction.provider ?? "model"} / ${interaction.model}` : ""}{interaction.reasoning_level ? ` / ${interaction.reasoning_level}` : ""}</p>
              </CardContent>
              <CardFooter className="library-card-actions">
                <Button asChild variant="secondary"><Link to={`/interactions/${interaction.id}`}>查看</Link></Button>
                <Button variant="secondary" type="button" onClick={() => void handleDownload(interaction)}>导出 Markdown</Button>
                <Button variant="destructive" type="button" disabled={deletingId === interaction.id} onClick={() => void handleDelete(interaction)}>{deletingId === interaction.id ? "删除中" : "删除"}</Button>
              </CardFooter>
            </article>
          </Card>
        ))}
      </section>
    </main>
  );
}
