import { ArrowLeft, Image as ImageIcon, LoaderCircle, Play, Plus, Settings2, Upload } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { MediaTaskCreateDialog } from "../components/media/MediaTaskCreateDialog";
import { MediaTaskHistory, isActiveMediaTask } from "../components/media/MediaTaskHistory";
import { useAuth } from "../contexts/AuthContext";
import { fetchMediaGenerations, fetchMediaWorkbench, runMediaWorkbench, uploadMediaAsset } from "../lib/api";
import type { MediaGeneration, MediaWorkbenchConfig } from "../types";
import "./media-workbenches.css";


export function ImageToImageWorkbenchPage() {
  const { user } = useAuth();
  const [config, setConfig] = useState<MediaWorkbenchConfig | null>(null);
  const [tasks, setTasks] = useState<MediaGeneration[]>([]);
  const [prompt, setPrompt] = useState("");
  const [assetId, setAssetId] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [fileName, setFileName] = useState("");
  const [aspectRatio, setAspectRatio] = useState("auto");
  const [imageSize, setImageSize] = useState("1K");
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [pageError, setPageError] = useState("");
  const [formError, setFormError] = useState("");
  const [historyError, setHistoryError] = useState("");

  async function loadHistory() {
    try {
      setTasks(await fetchMediaGenerations(undefined, "image-to-image"));
      setHistoryError("");
    } catch (reason) {
      setHistoryError(reason instanceof Error ? reason.message : "生成记录加载失败");
    }
  }

  async function load() {
    const configData = await fetchMediaWorkbench("image-to-image");
    setConfig(configData);
    await loadHistory();
    setAspectRatio((current) => current === "auto" ? String(configData.default_parameters.aspectRatio ?? "auto") : current);
    setImageSize((current) => current === "1K" ? String(configData.default_parameters.imageSize ?? "1K") : current);
  }

  useEffect(() => {
    void load().catch((reason: unknown) => setPageError(reason instanceof Error ? reason.message : "加载失败"));
  }, []);

  const hasActiveTasks = tasks.some(isActiveMediaTask);
  useEffect(() => {
    if (!hasActiveTasks) return undefined;
    const timer = window.setInterval(() => {
      void loadHistory();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [hasActiveTasks]);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  async function upload(file: File) {
    if (file.size > 12 * 1024 * 1024) { setFormError("参考图片不能超过 12MB"); return; }
    setUploading(true);
    setFormError("");
    try {
      const result = await uploadMediaAsset(file);
      if (result.asset.media_type !== "image") throw new Error("请选择图片文件");
      setPreviewUrl(URL.createObjectURL(file));
      setFileName(file.name);
      setAssetId(result.asset.id);
    } catch (reason) {
      setFormError(reason instanceof Error ? reason.message : "图片上传失败");
    } finally {
      setUploading(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!config || !assetId) return;
    setSubmitting(true);
    setFormError("");
    void runMediaWorkbench("image-to-image", {
      prompt,
      primary_asset_id: assetId,
      parameters: { aspectRatio, imageSize },
      client_request_id: crypto.randomUUID(),
    }).then(async () => {
      setPrompt("");
      await loadHistory();
      setIsCreateOpen(false);
    }).catch((reason: unknown) => setFormError(reason instanceof Error ? reason.message : "任务创建失败"))
      .finally(() => setSubmitting(false));
  }

  return (
    <main className="focused-workbench focused-workbench--image">
      <header className="focused-workbench-header">
        <Link to="/media-studio"><ArrowLeft aria-hidden />返回工作台</Link>
        <div><span><ImageIcon aria-hidden /></span><div><p className="eyebrow">GRS AI · {config?.model}</p><h1>{config?.display_name ?? "图生图"}</h1><p>{config?.description}</p></div></div>
        <div className="focused-workbench-actions">
          <button type="button" className="focused-create-button" disabled={!config?.configured} onClick={() => { setFormError(""); setIsCreateOpen(true); }}><Plus aria-hidden />创建任务</button>
          {user?.role === "teacher" ? <Link className="focused-config-link" to="/media-studio/configuration"><Settings2 aria-hidden />配置</Link> : null}
        </div>
      </header>
      {pageError ? <div className="workbench-error" role="alert">{pageError}</div> : null}
      {config && !config.configured ? <div className="workbench-blocked"><strong>工作台尚未配置完成</strong>{config.configuration_issues.map((issue) => <span key={issue}>{issue}</span>)}</div> : null}

      <section className="focused-task-section" aria-labelledby="image-task-list-title">
        <header className="focused-task-section-header">
          <div><p>任务概览</p><h2 id="image-task-list-title">全部图生图任务</h2><span>每次创作都是一张独立卡片，生成结果可以直接预览与下载。</span></div>
          <strong>{tasks.length}<small>个任务</small></strong>
        </header>
        {historyError ? <div className="workbench-error" role="alert">任务记录暂时无法读取：{historyError}</div> : null}
        <MediaTaskHistory tasks={tasks} onReload={loadHistory} />
      </section>

      <MediaTaskCreateDialog
        open={isCreateOpen}
        title="创建图生图任务"
        description="上传参考图片、描述修改要求并选择输出规格，创建后可在任务网格中查看进度。"
        busy={submitting || uploading}
        onClose={() => setIsCreateOpen(false)}
      >
        {formError ? <div className="workbench-error" role="alert">{formError}</div> : null}
        <form className="media-create-form" onSubmit={submit}>
          <label className={`focused-image-upload ${assetId ? "is-ready" : ""}`}>
            <input type="file" accept="image/png,image/jpeg,image/webp,.jpg,.jpeg,.png,.webp" required={!assetId} onChange={(event) => { const file = event.target.files?.[0]; if (file) void upload(file); }} />
            {previewUrl ? <img src={previewUrl} alt="参考图片预览" /> : uploading ? <LoaderCircle className="is-spinning" aria-hidden /> : <Upload aria-hidden />}
            <div><strong>{fileName || config?.input_config.primary_asset.label || "上传参考图片"}</strong><span>{config?.input_config.primary_asset.help_text || "不超过 12MB"}</span></div>
          </label>
          <label className="focused-field"><span>{config?.input_config.prompt.label ?? "修改要求"}<small>{config?.input_config.prompt.help_text}</small></span><textarea data-dialog-initial-focus rows={6} required value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="例如：保留人物和服装，将背景改成暖色舞台灯光……" /></label>
          <div className="focused-setting-row">
            <label className="focused-field"><span>画幅比例</span><select value={aspectRatio} onChange={(event) => setAspectRatio(event.target.value)}><option value="auto">自动</option><option value="1:1">1:1</option><option value="16:9">16:9</option><option value="9:16">9:16</option><option value="4:3">4:3</option><option value="3:4">3:4</option></select></label>
            <label className="focused-field"><span>输出尺寸</span><select value={imageSize} onChange={(event) => setImageSize(event.target.value)}><option value="1K">1K</option><option value="2K">2K</option><option value="4K">4K</option></select></label>
          </div>
          <button className="focused-run-button" type="submit" disabled={submitting || !config?.configured || !prompt.trim() || !assetId}>{submitting ? <LoaderCircle className="is-spinning" aria-hidden /> : <Play aria-hidden />}{submitting ? "正在创建任务" : "开始生成图片"}</button>
        </form>
      </MediaTaskCreateDialog>
    </main>
  );
}
