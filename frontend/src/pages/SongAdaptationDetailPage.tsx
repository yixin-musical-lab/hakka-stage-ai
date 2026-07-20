import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { SongAdaptationEditor } from "../components/musical/SongAdaptationEditor";
import { StudioLayout } from "../components/studio/StudioLayout";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { fetchSongAdaptation, updateSongAdaptation } from "../lib/api";
import { downloadSongAdaptationMarkdown } from "../lib/download";
import type { SongAdaptationContent, SongAdaptationResponse } from "../types";

export function SongAdaptationDetailPage() {
  const { songAdaptationId } = useParams();
  const navigate = useNavigate();
  const [songAdaptation, setSongAdaptation] = useState<SongAdaptationResponse | null>(null);
  const [editedContent, setEditedContent] = useState<SongAdaptationContent | null>(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!songAdaptationId) {
      return;
    }
    void fetchSongAdaptation(songAdaptationId)
      .then((detail) => {
        setSongAdaptation(detail);
        setEditedContent(detail.edited_content ?? detail.content);
        setNotice("");
      })
      .catch((caughtError) => setNotice(caughtError instanceof Error ? caughtError.message : "读取唱段适配失败。"))
      .finally(() => setLoading(false));
  }, [songAdaptationId]);

  async function saveSongAdaptation() {
    if (!songAdaptation || !editedContent) {
      return;
    }
    setSaving(true);
    setNotice("");
    try {
      const updated = await updateSongAdaptation(songAdaptation.id, editedContent);
      setSongAdaptation(updated);
      setEditedContent(updated.edited_content ?? updated.content);
      setNotice("唱段适配编辑稿已保存。");
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "保存失败。");
    } finally {
      setSaving(false);
    }
  }

  async function handleDownloadMarkdown() {
    if (!songAdaptation) {
      return;
    }
    try {
      setNotice("");
      await downloadSongAdaptationMarkdown(songAdaptation.id, songAdaptation.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  async function openMusicalFusion() {
    if (!songAdaptation || !editedContent) {
      return;
    }
    setSaving(true);
    setNotice("");
    try {
      // M04 读取唱段编辑确认稿，跳转前先保存，避免带入旧版 AI 初稿。
      await updateSongAdaptation(songAdaptation.id, editedContent);
      navigate(
        `/musical-fusion-plans/generate?script_id=${songAdaptation.script_id}&song_adaptation_id=${songAdaptation.id}`,
      );
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "保存并打开歌舞融合失败。");
      setSaving(false);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="唱段适配详情"
        title={songAdaptation?.title ?? "读取唱段适配"}
        description="查看、继续修改并导出音乐负责人确认稿。"
        action={
          <div className="button-row">
            <Button variant="secondary" type="button" onClick={() => navigate("/song-adaptations")}>
              返回列表
            </Button>
            {songAdaptation ? (
              <Button variant="secondary" type="button" onClick={() => void handleDownloadMarkdown()}>
                导出 Markdown
              </Button>
            ) : null}
            <Button variant="secondary" type="button" disabled={!editedContent || saving} onClick={() => void openMusicalFusion()}>
              保存并生成歌舞融合
            </Button>
            <Button type="button" disabled={!editedContent || saving} onClick={() => void saveSongAdaptation()}>
              {saving ? "保存中..." : "保存全部修改"}
            </Button>
          </div>
        }
      />

      <StudioLayout mode="edit" currentStep={songAdaptation?.edited_content ? 3 : 2}>
        {notice ? <p className="notice">{notice}</p> : null}
        {loading ? <EmptyState title="正在读取唱段适配" text="请稍候，系统正在读取唱段适配详情。" /> : null}

        {editedContent ? (
          <Card asChild className="surface-panel">
            <section>
              <SongAdaptationEditor
                content={editedContent}
                onChange={setEditedContent}
                modelInfo={songAdaptation?.raw_model_info ?? null}
              />
            </section>
          </Card>
        ) : !loading ? (
          <EmptyState title="唱段适配内容不可用" text="这份唱段适配可能尚未生成成功，暂时无法编辑或导出。" />
        ) : null}
      </StudioLayout>
    </main>
  );
}
