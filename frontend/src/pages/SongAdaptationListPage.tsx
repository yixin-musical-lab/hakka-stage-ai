import { useEffect, useState } from "react";
import { Link } from "react-router";
import { LibraryRecordCard } from "../components/library/LibraryRecordCard";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { deleteSongAdaptation, fetchSongAdaptations, isAbortError } from "../lib/api";
import { downloadSongAdaptationMarkdown } from "../lib/download";
import type { SongAdaptationSummary } from "../types";

export function SongAdaptationListPage() {
  const [songAdaptations, setSongAdaptations] = useState<SongAdaptationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchSongAdaptations(controller.signal)
      .then((data) => {
        setSongAdaptations(data);
        setNotice("");
      })
      .catch((caughtError) => {
        if (isAbortError(caughtError)) {
          return;
        }
        setNotice(caughtError instanceof Error ? caughtError.message : "读取唱段适配列表失败。");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  async function handleDownload(songAdaptation: SongAdaptationSummary) {
    try {
      setNotice("");
      await downloadSongAdaptationMarkdown(songAdaptation.id, songAdaptation.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  async function handleDelete(songAdaptation: SongAdaptationSummary) {
    const confirmed = window.confirm(`确认删除“${songAdaptation.title}”吗？删除后无法在列表中恢复。`);
    if (!confirmed) {
      return;
    }
    try {
      setDeletingId(songAdaptation.id);
      setNotice("");
      await deleteSongAdaptation(songAdaptation.id);
      setSongAdaptations((current) => current.filter((item) => item.id !== songAdaptation.id));
      setNotice(`已删除唱段适配：${songAdaptation.title}`);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "删除唱段适配失败。");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="唱段资料库"
        title="唱段适配"
        description="查看、继续编辑并导出已生成的唱段结构和歌词改写建议。"
        action={
          <Button asChild>
            <Link to="/song-adaptations/generate">新建唱段适配</Link>
          </Button>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取唱段适配" text="请稍候，系统正在从后端加载已保存内容。" /> : null}
      {!loading && songAdaptations.length === 0 ? (
        <EmptyState title="还没有保存的唱段适配" text="进入独立生成页选择一份剧本，再创建唱段结构和歌词改写建议。" />
      ) : null}

      <section className="library-card-grid" aria-label="唱段适配列表">
        {songAdaptations.map((songAdaptation) => (
          <LibraryRecordCard
            key={songAdaptation.id}
            kind="song"
            title={songAdaptation.title}
            badges={<Badge variant="secondary">{songAdaptation.status}</Badge>}
            summaryLabel="适配段落"
            summary={`${songAdaptation.related_scene}${songAdaptation.source_song ? ` · 原曲：${songAdaptation.source_song}` : ""}`}
            updatedAt={songAdaptation.updated_at}
            provider={songAdaptation.provider}
            model={songAdaptation.model}
            reasoningLevel={songAdaptation.reasoning_level}
            viewTo={`/song-adaptations/${songAdaptation.id}`}
            viewLabel="查看唱段"
            deleting={deletingId === songAdaptation.id}
            onDownload={() => void handleDownload(songAdaptation)}
            onDelete={() => void handleDelete(songAdaptation)}
          />
        ))}
      </section>
    </main>
  );
}
