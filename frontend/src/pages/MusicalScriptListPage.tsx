import { useEffect, useState } from "react";
import { Link } from "react-router";
import { LibraryRecordCard } from "../components/library/LibraryRecordCard";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { deleteMusicalScript, fetchMusicalScripts } from "../lib/api";
import { downloadMusicalScriptMarkdown } from "../lib/download";
import type { MusicalScriptSummary } from "../types";

export function MusicalScriptListPage() {
  const [scripts, setScripts] = useState<MusicalScriptSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchMusicalScripts(controller.signal)
      .then((data) => {
        setScripts(data);
        setNotice("");
      })
      .catch((caughtError) => setNotice(caughtError instanceof Error ? caughtError.message : "读取剧本列表失败。"))
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  async function handleDownload(script: MusicalScriptSummary) {
    try {
      setNotice("");
      await downloadMusicalScriptMarkdown(script.id, script.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  async function handleDelete(script: MusicalScriptSummary) {
    const confirmed = window.confirm(`确认删除“${script.title}”吗？删除后无法在列表中恢复。`);
    if (!confirmed) {
      return;
    }
    try {
      setDeletingId(script.id);
      setNotice("");
      await deleteMusicalScript(script.id);
      setScripts((current) => current.filter((item) => item.id !== script.id));
      setNotice(`已删除剧本：${script.title}`);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "删除剧本失败。");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="歌舞剧资料库"
        title="已保存剧本"
        description="重新打开编导确认稿，继续编辑、生成训练计划或导出 Markdown。"
        action={
          <Button asChild>
            <Link to="/musical-scripts/generate">新建剧本</Link>
          </Button>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取剧本" text="请稍候，系统正在从后端加载已保存内容。" /> : null}
      {!loading && scripts.length === 0 ? <EmptyState title="还没有保存的剧本" text="先生成一份剧本，保存后就会出现在这里。" /> : null}

      <section className="library-card-grid" aria-label="已保存剧本列表">
        {scripts.map((script) => (
          <LibraryRecordCard
            key={script.id}
            kind="script"
            title={script.title}
            badges={<Badge variant="secondary">{script.status}</Badge>}
            summaryLabel="创作阶段"
            summary="编导确认稿 · 可继续衔接唱段适配与角色训练"
            updatedAt={script.updated_at}
            provider={script.provider}
            model={script.model}
            reasoningLevel={script.reasoning_level}
            viewTo={`/musical-scripts/${script.id}`}
            viewLabel="查看剧本"
            deleting={deletingId === script.id}
            onDownload={() => void handleDownload(script)}
            onDelete={() => void handleDelete(script)}
          />
        ))}
      </section>
    </main>
  );
}
