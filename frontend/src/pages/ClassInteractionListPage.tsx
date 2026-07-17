import { useEffect, useState } from "react";
import { Link } from "react-router";
import { LibraryRecordCard } from "../components/library/LibraryRecordCard";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { deleteClassInteraction, fetchClassInteractions } from "../lib/api";
import { downloadClassInteractionMarkdown } from "../lib/download";
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
          <LibraryRecordCard
            key={interaction.id}
            kind="interaction"
            title={interaction.title}
            badges={<Badge variant="secondary">{interaction.status}</Badge>}
            summaryLabel="课堂配置"
            summary={`${interaction.course_theme} · ${interaction.teaching_phase} · ${interaction.duration_minutes} 分钟`}
            updatedAt={interaction.updated_at}
            provider={interaction.provider}
            model={interaction.model}
            reasoningLevel={interaction.reasoning_level}
            viewTo={`/interactions/${interaction.id}`}
            viewLabel="查看方案"
            deleting={deletingId === interaction.id}
            onDownload={() => void handleDownload(interaction)}
            onDelete={() => void handleDelete(interaction)}
          />
        ))}
      </section>
    </main>
  );
}
