import { useEffect, useState } from "react";
import { Link } from "react-router";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { deleteMovementGuide, fetchMovementGuides } from "../lib/api";
import { downloadMovementGuideMarkdown } from "../lib/download";
import { formatDateTime } from "../lib/format";
import type { MovementGuideSummary } from "../types";

export function MovementGuideListPage() {
  const [movementGuides, setMovementGuides] = useState<MovementGuideSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchMovementGuides(controller.signal)
      .then((data) => {
        setMovementGuides(data);
        setNotice("");
      })
      .catch((caughtError) => setNotice(caughtError instanceof Error ? caughtError.message : "读取示范材料列表失败。"))
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  async function handleDownload(movementGuide: MovementGuideSummary) {
    try {
      setNotice("");
      await downloadMovementGuideMarkdown(movementGuide.id, movementGuide.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  async function handleDelete(movementGuide: MovementGuideSummary) {
    const confirmed = window.confirm(`确认删除“${movementGuide.title}”吗？删除后无法在列表中恢复。`);
    if (!confirmed) {
      return;
    }

    try {
      setDeletingId(movementGuide.id);
      setNotice("");
      await deleteMovementGuide(movementGuide.id);
      setMovementGuides((current) => current.filter((item) => item.id !== movementGuide.id));
      setNotice(`已删除示范材料：${movementGuide.title}`);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "删除示范材料失败。");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="示范材料库"
        title="动作图解 / 示范材料"
        description="管理老师确认后的动作拆解、关键姿态说明和示范材料链接。"
        action={
          <Link className="primary-button link-button" to="/movement-guides/new">
            新建动作图解
          </Link>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取示范材料" text="请稍候，系统正在从后端加载已保存内容。" /> : null}
      {!loading && movementGuides.length === 0 ? (
        <EmptyState title="还没有保存的示范材料" text="先创建一个动作图解，保存后就会出现在这里。" />
      ) : null}

      <section className="lesson-list" aria-label="动作图解 / 示范材料列表">
        {movementGuides.map((movementGuide) => (
          <article className="lesson-list-item" key={movementGuide.id}>
            <div>
              <span className="status-badge">{movementGuide.status}</span>
              <h2>{movementGuide.title}</h2>
              <p>
                动作：{movementGuide.action_name}
                {movementGuide.course_context ? ` · ${movementGuide.course_context}` : ""}
                {` · 材料 ${movementGuide.confirmed_asset_count}/${movementGuide.asset_count}`}
              </p>
              <p>更新时间：{formatDateTime(movementGuide.updated_at)}</p>
            </div>
            <div className="button-row">
              <Link className="secondary-button link-button" to={`/movement-guides/${movementGuide.id}`}>
                查看
              </Link>
              <button className="secondary-button" type="button" onClick={() => void handleDownload(movementGuide)}>
                导出 Markdown
              </button>
              <button
                className="danger-button"
                type="button"
                disabled={deletingId === movementGuide.id}
                onClick={() => void handleDelete(movementGuide)}
              >
                {deletingId === movementGuide.id ? "删除中" : "删除"}
              </button>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}
