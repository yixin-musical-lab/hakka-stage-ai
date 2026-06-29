import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { MovementGuideEditor } from "../components/movement-guides/MovementGuideEditor";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { createMovementCandidatePlaceholder, fetchMovementGuide, updateMovementGuide } from "../lib/api";
import { downloadMovementGuideMarkdown } from "../lib/download";
import type { MovementGuideContent, MovementGuideResponse } from "../types";

export function MovementGuideDetailPage() {
  const { movementGuideId } = useParams();
  const navigate = useNavigate();
  const [movementGuide, setMovementGuide] = useState<MovementGuideResponse | null>(null);
  const [editedContent, setEditedContent] = useState<MovementGuideContent | null>(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    if (!movementGuideId) {
      return;
    }
    void fetchMovementGuide(movementGuideId)
      .then((detail) => {
        setMovementGuide(detail);
        setEditedContent(detail.edited_content ?? detail.content);
        setNotice("");
      })
      .catch((caughtError) => setNotice(caughtError instanceof Error ? caughtError.message : "读取动作图解失败。"))
      .finally(() => setLoading(false));
  }, [movementGuideId]);

  async function saveMovementGuide() {
    if (!movementGuide || !editedContent) {
      return;
    }
    setSaving(true);
    setNotice("");
    try {
      const updated = await updateMovementGuide(movementGuide.id, editedContent);
      setMovementGuide(updated);
      setEditedContent(updated.edited_content ?? updated.content);
      setNotice("老师编辑稿已保存。");
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "保存失败。");
    } finally {
      setSaving(false);
    }
  }

  async function handleDownloadMarkdown() {
    if (!movementGuide) {
      return;
    }
    try {
      setNotice("");
      await downloadMovementGuideMarkdown(movementGuide.id, movementGuide.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  async function handleGenerateCandidates() {
    if (!movementGuide) {
      return;
    }
    setGenerating(true);
    setNotice("");
    try {
      const result = await createMovementCandidatePlaceholder(movementGuide.id);
      setNotice(result.message);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "骨骼动画候选生成暂不可用。");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="动作图解详情"
        title={movementGuide?.title ?? "读取动作图解"}
        description="查看、继续修改并导出老师确认稿；真实视频生成后续由 Worker 和云端 GPU 接入。"
        action={
          <div className="button-row">
            <button className="secondary-button" type="button" onClick={() => navigate("/movement-guides")}>
              返回列表
            </button>
            {movementGuide ? (
              <button className="secondary-button" type="button" onClick={() => void handleDownloadMarkdown()}>
                导出 Markdown
              </button>
            ) : null}
            {movementGuide ? (
              <button className="secondary-button" type="button" disabled={generating} onClick={() => void handleGenerateCandidates()}>
                {generating ? "提交中..." : "生成骨骼候选"}
              </button>
            ) : null}
            <button className="primary-button compact" type="button" disabled={!editedContent || saving} onClick={() => void saveMovementGuide()}>
              {saving ? "保存中..." : "保存编辑稿"}
            </button>
          </div>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取动作图解" text="请稍候，系统正在读取动作图解详情。" /> : null}

      {editedContent ? (
        <section className="surface-panel">
          <MovementGuideEditor content={editedContent} onChange={setEditedContent} modelInfo={movementGuide?.raw_pipeline_info ?? null} />
        </section>
      ) : !loading ? (
        <EmptyState title="动作图解内容不可用" text="这份动作图解可能尚未创建成功，暂时无法编辑或导出。" />
      ) : null}
    </main>
  );
}
