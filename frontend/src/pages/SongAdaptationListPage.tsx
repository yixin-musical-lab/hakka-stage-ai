import { useEffect, useState } from "react";
import { Link } from "react-router";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { deleteSongAdaptation, fetchSongAdaptations } from "../lib/api";
import { downloadSongAdaptationMarkdown } from "../lib/download";
import { formatDateTime } from "../lib/format";
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
      .catch((caughtError) => setNotice(caughtError instanceof Error ? caughtError.message : "读取唱段适配列表失败。"))
      .finally(() => setLoading(false));
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

      <section className="lesson-list" aria-label="唱段适配列表">
        {songAdaptations.map((songAdaptation) => (
          <Card asChild className="lesson-list-item" key={songAdaptation.id}>
            <article>
              <div>
                <Badge variant="secondary">{songAdaptation.status}</Badge>
                <h2>{songAdaptation.title}</h2>
                <p>
                  段落：{songAdaptation.related_scene}
                  {songAdaptation.source_song ? ` · ${songAdaptation.source_song}` : ""}
                </p>
                <p>
                  更新时间：{formatDateTime(songAdaptation.updated_at)}
                  {songAdaptation.model ? ` · ${songAdaptation.provider ?? "model"} / ${songAdaptation.model}` : ""}
                  {songAdaptation.reasoning_level ? ` / ${songAdaptation.reasoning_level}` : ""}
                </p>
              </div>
              <div className="button-row">
                <Button asChild variant="secondary">
                  <Link to={`/song-adaptations/${songAdaptation.id}`}>查看</Link>
                </Button>
                <Button variant="secondary" type="button" onClick={() => void handleDownload(songAdaptation)}>
                  导出 Markdown
                </Button>
                <Button
                  variant="destructive"
                  type="button"
                  disabled={deletingId === songAdaptation.id}
                  onClick={() => void handleDelete(songAdaptation)}
                >
                  {deletingId === songAdaptation.id ? "删除中" : "删除"}
                </Button>
              </div>
            </article>
          </Card>
        ))}
      </section>
    </main>
  );
}
