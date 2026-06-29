import { useEffect, useState } from "react";
import { Link } from "react-router";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { deleteMusicalScript, fetchMusicalScripts } from "../lib/api";
import { downloadMusicalScriptMarkdown } from "../lib/download";
import { formatDateTime } from "../lib/format";
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
          <Link className="primary-button link-button" to="/musical-scripts/generate">
            新建剧本
          </Link>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取剧本" text="请稍候，系统正在从后端加载已保存内容。" /> : null}
      {!loading && scripts.length === 0 ? <EmptyState title="还没有保存的剧本" text="先生成一份剧本，保存后就会出现在这里。" /> : null}

      <section className="lesson-list" aria-label="已保存剧本列表">
        {scripts.map((script) => (
          <article className="lesson-list-item" key={script.id}>
            <div>
              <span className="status-badge">{script.status}</span>
              <h2>{script.title}</h2>
              <p>
                更新时间：{formatDateTime(script.updated_at)}
                {script.model ? ` · ${script.provider ?? "model"} / ${script.model}` : ""}
                {script.reasoning_level ? ` / ${script.reasoning_level}` : ""}
              </p>
            </div>
            <div className="button-row">
              <Link className="secondary-button link-button" to={`/musical-scripts/${script.id}`}>
                查看
              </Link>
              <button className="secondary-button" type="button" onClick={() => void handleDownload(script)}>
                导出 Markdown
              </button>
              <button className="danger-button" type="button" disabled={deletingId === script.id} onClick={() => void handleDelete(script)}>
                {deletingId === script.id ? "删除中" : "删除"}
              </button>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}
