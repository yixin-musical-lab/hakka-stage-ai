import { Download, LoaderCircle, RefreshCw, XCircle } from "lucide-react";
import { useState } from "react";
import { cancelMediaGeneration, refreshMediaGeneration } from "../../lib/api";
import { apiBaseUrl } from "../../lib/config";
import { formatFullDateTime, formatTime, normalizeApiDateTime } from "../../lib/format";
import type { MediaAsset, MediaGeneration } from "../../types";


const ACTIVE_STATUSES = new Set(["PENDING", "SUBMITTING", "SUBMITTED", "RUNNING", "CANCEL_REQUESTED"]);


export function isActiveMediaTask(task: MediaGeneration) {
  return ACTIVE_STATUSES.has(task.status);
}


function assetUrl(asset: MediaAsset) {
  return asset.url.startsWith("/") ? `${apiBaseUrl}${asset.url}` : asset.url;
}


function statusLabel(status: string) {
  return ({
    PENDING: "等待提交",
    SUBMITTING: "正在提交",
    SUBMITTED: "已提交",
    RUNNING: "正在生成",
    SUCCEEDED: "已完成",
    FAILED: "生成失败",
    CANCEL_REQUESTED: "正在取消",
    CANCELLED: "已取消",
  } as Record<string, string>)[status] ?? status;
}


function OutputPreview({ asset }: { asset: MediaAsset }) {
  const url = assetUrl(asset);
  if (asset.media_type === "audio") return <audio controls preload="metadata" src={url} />;
  if (asset.media_type === "image") return <img src={url} alt="生成结果" />;
  if (asset.media_type === "video") return <video controls preload="metadata" src={url} />;
  return <div className="workbench-file-result">文件结果已生成</div>;
}


function MediaTaskCard({ task, onReload }: { task: MediaGeneration; onReload: () => Promise<void> }) {
  const [activeAction, setActiveAction] = useState<"refresh" | "cancel" | "">("");
  const [actionError, setActionError] = useState("");
  const run = task.runs[task.runs.length - 1];
  const outputs = task.assets.filter((asset) => asset.role === "output");
  const previewAsset = outputs[0];
  const displayText = task.prompt.trim() || task.title;

  async function act(action: "refresh" | "cancel") {
    if (activeAction) return;
    setActiveAction(action);
    setActionError("");
    try {
      if (action === "refresh") await refreshMediaGeneration(task.id);
      else await cancelMediaGeneration(task.id);
      await onReload();
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "任务操作失败，请稍后重试");
    } finally {
      setActiveAction("");
    }
  }

  return (
    <article className={`workbench-task workbench-task--${task.capability}`} aria-label={task.title}>
      <div className="workbench-task-copy">
        <h3 title={displayText}>{displayText || "此任务没有文本输入"}</h3>
      </div>
      {previewAsset ? (
        <div className="workbench-output-preview">
          <OutputPreview asset={previewAsset} />
        </div>
      ) : run?.error_message ? (
        <div className="workbench-task-error" title={run.error_message}>{run.error_message}</div>
      ) : isActiveMediaTask(task) ? (
        <div className="workbench-progress" role="status" aria-live="polite">
          <span /><small>{run?.provider_status ?? "准备中"}</small>
        </div>
      ) : (
        <div className="workbench-no-result">暂无可播放结果</div>
      )}
      {actionError ? <div className="workbench-error" role="alert">{actionError}</div> : null}
      <footer className="workbench-task-footer">
        <span className={`workbench-status workbench-status--${task.status.toLowerCase()}`}>{statusLabel(task.status)}</span>
        <time
          dateTime={normalizeApiDateTime(task.created_at)}
          title={`创建于 ${formatFullDateTime(task.created_at)}`}
          aria-label={`创建于 ${formatFullDateTime(task.created_at)}`}
        >
          <span className="workbench-task-time-full">{formatFullDateTime(task.created_at)}</span>
          <span className="workbench-task-time-compact">{formatTime(task.created_at)}</span>
        </time>
        {outputs.length ? (
          <div className="workbench-downloads">
            {outputs.map((asset, index) => (
              <a
                href={assetUrl(asset)}
                download={asset.original_file_name || true}
                target="_blank"
                rel="noreferrer"
                aria-label={outputs.length > 1 ? `下载结果 ${index + 1}` : "下载结果"}
                title={outputs.length > 1 ? `下载结果 ${index + 1}` : "下载结果"}
                key={asset.id}
              >
                <Download aria-hidden />{outputs.length > 1 ? index + 1 : "下载"}
              </a>
            ))}
          </div>
        ) : isActiveMediaTask(task) ? (
          <div className="workbench-task-actions">
            <button type="button" disabled={Boolean(activeAction)} onClick={() => void act("refresh")}>
              {activeAction === "refresh" ? <LoaderCircle className="is-spinning" aria-hidden /> : <RefreshCw aria-hidden />}<span>刷新</span>
            </button>
            <button type="button" disabled={Boolean(activeAction)} onClick={() => void act("cancel")}>
              {activeAction === "cancel" ? <LoaderCircle className="is-spinning" aria-hidden /> : <XCircle aria-hidden />}<span>取消</span>
            </button>
          </div>
        ) : (
          <span className="workbench-download-empty">暂无结果</span>
        )}
      </footer>
    </article>
  );
}


export function MediaTaskHistory({
  tasks,
  onReload,
  emptyText = "还没有生成记录。点击“创建任务”开始第一次创作。",
}: {
  tasks: MediaGeneration[];
  onReload: () => Promise<void>;
  emptyText?: string;
}) {
  if (!tasks.length) return <div className="workbench-empty-result">{emptyText}</div>;
  return (
    <div className="workbench-task-list">
      {tasks.map((task) => <MediaTaskCard task={task} onReload={onReload} key={task.id} />)}
    </div>
  );
}
