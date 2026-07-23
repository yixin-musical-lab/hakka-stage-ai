import {
  AlertTriangle,
  ArrowDownToLine,
  CheckCircle2,
  Clock3,
  ExternalLink,
  Film,
  ImagePlus,
  LoaderCircle,
  RefreshCw,
  Sparkles,
  Upload,
  WandSparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { PageTitle } from "../components/ui/PageTitle";
import { Progress } from "../components/ui/progress";
import { createVeoTask, fetchVeoOptions, fetchVeoTask, fetchVeoTasks, isAbortError } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { VeoAspectRatio, VeoModelCode, VeoOptionsResponse, VeoTaskResponse } from "../types";
import "./veo-video-workbench.css";


type ImageInputMode = "upload" | "url";
type Notice = { type: "status" | "error"; text: string } | null;

const TERMINAL_STATUSES = new Set(["succeeded", "failed"]);


export function VeoVideoWorkbenchPage() {
  const [options, setOptions] = useState<VeoOptionsResponse | null>(null);
  const [tasks, setTasks] = useState<VeoTaskResponse[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const [inputMode, setInputMode] = useState<ImageInputMode>("upload");
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState<VeoModelCode>("veo3.1-fast");
  const [aspectRatio, setAspectRatio] = useState<VeoAspectRatio>("16:9");
  const [firstFrameFile, setFirstFrameFile] = useState<File | null>(null);
  const [firstFrameUrl, setFirstFrameUrl] = useState("");
  const [lastFrameFile, setLastFrameFile] = useState<File | null>(null);
  const [lastFrameUrl, setLastFrameUrl] = useState("");
  const [useLastFrame, setUseLastFrame] = useState(false);
  const [firstPreviewUrl, setFirstPreviewUrl] = useState("");
  const [lastPreviewUrl, setLastPreviewUrl] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([fetchVeoOptions(controller.signal), fetchVeoTasks(controller.signal)])
      .then(([loadedOptions, loadedTasks]) => {
        setOptions(loadedOptions);
        setTasks(loadedTasks);
        setSelectedTaskId(loadedTasks[0]?.id ?? "");
        if (!loadedOptions.file_upload_available) setInputMode("url");
      })
      .catch((caughtError) => {
        if (!isAbortError(caughtError)) {
          setNotice({ type: "error", text: caughtError instanceof Error ? caughtError.message : "媒体工作台加载失败。" });
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    return () => {
      if (firstPreviewUrl) URL.revokeObjectURL(firstPreviewUrl);
      if (lastPreviewUrl) URL.revokeObjectURL(lastPreviewUrl);
    };
  }, [firstPreviewUrl, lastPreviewUrl]);

  const pendingTaskIds = useMemo(
    () => tasks.filter((task) => !TERMINAL_STATUSES.has(task.status)).map((task) => task.id).join(","),
    [tasks],
  );

  useEffect(() => {
    if (!pendingTaskIds) return;
    const ids = pendingTaskIds.split(",");
    const refreshPendingTasks = async () => {
      const results = await Promise.allSettled(ids.map((taskId) => fetchVeoTask(taskId)));
      setTasks((current) => current.map((task) => {
        const resultIndex = ids.indexOf(task.id);
        const result = resultIndex >= 0 ? results[resultIndex] : null;
        return result?.status === "fulfilled" ? result.value : task;
      }));
    };
    void refreshPendingTasks();
    const timer = window.setInterval(() => void refreshPendingTasks(), 12_000);
    return () => window.clearInterval(timer);
  }, [pendingTaskIds]);

  const selectedTask = tasks.find((task) => task.id === selectedTaskId) ?? tasks[0] ?? null;
  const selectedModel = options?.models.find((item) => item.code === model);

  function selectFirstFrame(file: File | null) {
    if (firstPreviewUrl) URL.revokeObjectURL(firstPreviewUrl);
    setFirstFrameFile(file);
    setFirstPreviewUrl(file ? URL.createObjectURL(file) : "");
  }

  function selectLastFrame(file: File | null) {
    if (lastPreviewUrl) URL.revokeObjectURL(lastPreviewUrl);
    setLastFrameFile(file);
    setLastPreviewUrl(file ? URL.createObjectURL(file) : "");
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || !options) return;
    if (!prompt.trim()) {
      setNotice({ type: "error", text: "请先填写画面动作、镜头运动和氛围提示。" });
      return;
    }
    if (inputMode === "upload" && !firstFrameFile) {
      setNotice({ type: "error", text: "请上传一张首帧图片。" });
      return;
    }
    if (inputMode === "url" && !firstFrameUrl.trim()) {
      setNotice({ type: "error", text: "请填写公开可访问的首帧图片 URL。" });
      return;
    }
    if (useLastFrame && inputMode === "upload" && !lastFrameFile) {
      setNotice({ type: "error", text: "已开启尾帧控制，请选择尾帧图片；不需要时可关闭尾帧控制。" });
      return;
    }
    if (useLastFrame && inputMode === "url" && !lastFrameUrl.trim()) {
      setNotice({ type: "error", text: "已开启尾帧控制，请填写尾帧公网 URL；不需要时可关闭尾帧控制。" });
      return;
    }
    if (firstFrameFile && firstFrameFile.size > options.image_max_upload_mb * 1024 * 1024) {
      setNotice({ type: "error", text: `首帧超过 ${options.image_max_upload_mb}MB，请压缩后重试。` });
      return;
    }
    if (lastFrameFile && lastFrameFile.size > options.image_max_upload_mb * 1024 * 1024) {
      setNotice({ type: "error", text: `尾帧超过 ${options.image_max_upload_mb}MB，请压缩后重试。` });
      return;
    }

    setSubmitting(true);
    setNotice({ type: "status", text: "正在上传首帧并创建 GRS AI Veo 任务……" });
    try {
      const created = await createVeoTask({
        prompt: prompt.trim(),
        model,
        aspectRatio,
        firstFrameFile: inputMode === "upload" ? firstFrameFile : null,
        firstFrameUrl: inputMode === "url" ? firstFrameUrl : "",
        lastFrameFile: useLastFrame && inputMode === "upload" ? lastFrameFile : null,
        lastFrameUrl: useLastFrame && inputMode === "url" ? lastFrameUrl : "",
      });
      setTasks((current) => [created, ...current.filter((task) => task.id !== created.id)]);
      setSelectedTaskId(created.id);
      setNotice({ type: "status", text: "任务已提交。页面会每 12 秒刷新一次，离开后重新打开也能恢复最近任务。" });
    } catch (caughtError) {
      setNotice({ type: "error", text: caughtError instanceof Error ? caughtError.message : "创建视频任务失败。" });
    } finally {
      setSubmitting(false);
    }
  }

  async function refreshSelectedTask() {
    if (!selectedTask || refreshing) return;
    setRefreshing(true);
    try {
      const updated = await fetchVeoTask(selectedTask.id);
      setTasks((current) => current.map((task) => (task.id === updated.id ? updated : task)));
      setNotice({ type: "status", text: "已刷新任务状态。" });
    } catch (caughtError) {
      setNotice({ type: "error", text: caughtError instanceof Error ? caughtError.message : "刷新任务失败。" });
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <main className="page-frame media-studio-page">
      <PageTitle
        eyebrow="媒体工作台"
        title="GRS AI · Veo 图生视频"
        description="用首帧或首尾帧生成舞台分镜、动作示范和创意短片；密钥只保存在服务端。"
        action={
          <Button asChild variant="secondary">
            <a href="https://grsai.com/zh/dashboard/documents/veo" target="_blank" rel="noreferrer">
              官方接口文档<ExternalLink aria-hidden />
            </a>
          </Button>
        }
      />

      <section className="media-studio-summary" aria-label="GRS AI 接入摘要">
        <article><WandSparkles aria-hidden /><span><strong>Veo 3.1 Fast / Pro</strong><small>当前只开放官方参数表明确支持的 3.1 模型</small></span></article>
        <article><ImagePlus aria-hidden /><span><strong>首帧与可选尾帧</strong><small>参考图模式与首尾帧互斥，首版暂不开放</small></span></article>
        <article><Clock3 aria-hidden /><span><strong>异步任务与恢复</strong><small>任务由 Redis 保留 24 小时，结果链接约 2 小时有效</small></span></article>
        <article className={options?.configured ? "is-ready" : "is-warning"}>
          {options?.configured ? <CheckCircle2 aria-hidden /> : <AlertTriangle aria-hidden />}
          <span><strong>{options?.configured ? "服务端已配置" : "等待配置密钥"}</strong><small>{options?.mock_mode ? "当前为 Mock 联调模式" : "GRSAI_API_KEY 不会返回浏览器"}</small></span>
        </article>
      </section>

      <div className="media-studio-grid">
        <form className="media-generator-panel" onSubmit={submit}>
          <div className="media-panel-heading">
            <div><p className="section-kicker">生成设置</p><h2>从一张舞台画面开始</h2></div>
            {options?.mock_mode ? <Badge variant="secondary">Mock</Badge> : <Badge>GRS AI</Badge>}
          </div>

          <fieldset className="media-input-mode" disabled={loading || submitting}>
            <legend>首帧来源</legend>
            <button type="button" className={inputMode === "upload" ? "is-active" : ""} disabled={!options?.file_upload_available} onClick={() => setInputMode("upload")}>
              <Upload aria-hidden />本地上传
            </button>
            <button type="button" className={inputMode === "url" ? "is-active" : ""} onClick={() => setInputMode("url")}>
              <ExternalLink aria-hidden />公网 URL
            </button>
          </fieldset>

          {inputMode === "upload" ? (
            <label className={`media-dropzone${firstPreviewUrl ? " has-preview" : ""}`}>
              {firstPreviewUrl ? <img src={firstPreviewUrl} alt="首帧预览" /> : <><ImagePlus aria-hidden /><strong>选择首帧图片</strong><small>JPG / PNG / WEBP，最大 {options?.image_max_upload_mb ?? 10}MB</small></>}
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => selectFirstFrame(event.target.files?.[0] ?? null)} />
            </label>
          ) : (
            <label className="media-field"><span>首帧公网 URL</span><input type="url" value={firstFrameUrl} placeholder="https://example.com/first-frame.png" onChange={(event) => setFirstFrameUrl(event.target.value)} /></label>
          )}

          <label className="media-field media-prompt-field">
            <span>视频提示词</span>
            <textarea value={prompt} maxLength={2000} rows={6} placeholder="例如：镜头缓慢推近，演员从定格水袖动作自然转身，绸带随动作形成流畅弧线；暖金色舞台追光，背景保持稳定，电影感，动作连贯。" onChange={(event) => setPrompt(event.target.value)} />
            <small>建议写清主体动作、镜头运动、节奏、光线与需要保持不变的内容。{prompt.length} / 2000</small>
          </label>

          <div className="media-setting-grid">
            <label className="media-field"><span>模型</span><select value={model} onChange={(event) => setModel(event.target.value as VeoModelCode)}>{options?.models.map((item) => <option key={item.code} value={item.code}>{item.name}</option>)}</select><small>{selectedModel?.description}</small></label>
            <div className="media-field"><span>输出画幅</span><div className="media-aspect-options">{options?.aspect_ratios.map((ratio) => <button key={ratio} type="button" className={aspectRatio === ratio ? "is-active" : ""} onClick={() => setAspectRatio(ratio)}><i className={ratio === "16:9" ? "is-landscape" : "is-portrait"} />{ratio}</button>)}</div></div>
          </div>

          <label className="media-last-frame-toggle"><input type="checkbox" checked={useLastFrame} onChange={(event) => setUseLastFrame(event.target.checked)} /><span><strong>控制尾帧（可选）</strong><small>适合明确落点、定格或镜头终点；需与首帧使用同一种输入方式。</small></span></label>
          {useLastFrame ? inputMode === "upload" ? (
            <label className={`media-dropzone media-dropzone--compact${lastPreviewUrl ? " has-preview" : ""}`}>
              {lastPreviewUrl ? <img src={lastPreviewUrl} alt="尾帧预览" /> : <><ImagePlus aria-hidden /><strong>选择尾帧图片</strong><small>可不上传，改为关闭尾帧控制</small></>}
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => selectLastFrame(event.target.files?.[0] ?? null)} />
            </label>
          ) : (
            <label className="media-field"><span>尾帧公网 URL</span><input type="url" value={lastFrameUrl} placeholder="https://example.com/last-frame.png" onChange={(event) => setLastFrameUrl(event.target.value)} /></label>
          ) : null}

          {notice ? <p className={`media-notice media-notice--${notice.type}`}>{notice.type === "error" ? <AlertTriangle aria-hidden /> : <Sparkles aria-hidden />}{notice.text}</p> : null}
          {!loading && !options?.configured ? <p className="media-config-hint">请在后端 `.env` 配置 `GRSAI_API_KEY`；如需上传本地图片，还需填写外网可访问的 `GRSAI_PUBLIC_BASE_URL`。</p> : null}
          <Button className="media-submit-button" type="submit" size="lg" disabled={loading || submitting || !options?.configured}>
            {submitting ? <><LoaderCircle aria-hidden className="media-spin" />正在创建任务</> : <><Film aria-hidden />生成 Veo 视频</>}
          </Button>
        </form>

        <section className="media-result-panel" aria-live="polite">
          <div className="media-panel-heading">
            <div><p className="section-kicker">生成结果</p><h2>{selectedTask ? statusLabel(selectedTask.status) : "等待创建任务"}</h2></div>
            <Button variant="ghost" size="sm" type="button" disabled={!selectedTask || refreshing} onClick={() => void refreshSelectedTask()}><RefreshCw aria-hidden className={refreshing ? "media-spin" : ""} />刷新</Button>
          </div>

          {selectedTask ? (
            <>
              <div className={`media-result-preview is-${selectedTask.status}`}>
                {selectedTask.video_url ? <video src={selectedTask.video_url} controls playsInline preload="metadata" /> : <div>{selectedTask.status === "failed" ? <AlertTriangle aria-hidden /> : selectedTask.status === "succeeded" ? <CheckCircle2 aria-hidden /> : <LoaderCircle aria-hidden className="media-spin" />}<strong>{resultMessage(selectedTask)}</strong><small>{selectedTask.status === "running" ? "Veo 视频通常需要数分钟，请保留页面或稍后回来查看。" : selectedTask.error_message || selectedTask.failure_reason}</small></div>}
              </div>
              <div className="media-progress-row"><span><strong>{selectedTask.progress}%</strong><small>{statusLabel(selectedTask.status)}</small></span><Progress value={selectedTask.progress} /></div>
              <dl className="media-task-meta"><div><dt>模型</dt><dd>{selectedTask.model}</dd></div><div><dt>画幅</dt><dd>{selectedTask.aspect_ratio}</dd></div><div><dt>输入</dt><dd>{selectedTask.source_mode === "upload" ? "本地首帧" : "公网 URL"}{selectedTask.has_last_frame ? " + 尾帧" : ""}</dd></div><div><dt>创建时间</dt><dd>{formatDateTime(selectedTask.created_at)}</dd></div></dl>
              {selectedTask.video_url ? <Button asChild className="w-full"><a href={selectedTask.video_url} target="_blank" rel="noreferrer"><ArrowDownToLine aria-hidden />打开并及时下载视频</a></Button> : null}
              <p className="media-expiry-note">GRS AI 结果地址仅保证约 {options?.result_url_ttl_hours ?? 2} 小时有效；成功后请立即下载，不要把临时地址当作长期素材库。</p>
            </>
          ) : (
            <div className="media-empty-result"><Film aria-hidden /><h3>结果将在这里出现</h3><p>提交后平台只保存任务元数据；首尾帧存入 MinIO，GRS AI 密钥不会进入浏览器。</p></div>
          )}
        </section>
      </div>

      <section className="media-history-section">
        <div className="media-panel-heading"><div><p className="section-kicker">最近任务</p><h2>当前账号的 Veo 生成记录</h2></div><span>最多展示 12 条 · 本地保留 24 小时</span></div>
        {tasks.length ? <div className="media-task-list">{tasks.map((task) => <button key={task.id} type="button" className={selectedTask?.id === task.id ? "is-active" : ""} onClick={() => setSelectedTaskId(task.id)}><span className={`media-task-status is-${task.status}`}>{task.status === "succeeded" ? <CheckCircle2 aria-hidden /> : task.status === "failed" ? <AlertTriangle aria-hidden /> : <LoaderCircle aria-hidden className="media-spin" />}</span><span><strong>{task.prompt}</strong><small>{task.model} · {task.aspect_ratio} · {formatDateTime(task.created_at)}</small></span><em>{statusLabel(task.status)}</em></button>)}</div> : <div className="media-history-empty">还没有 Veo 任务。</div>}
      </section>

      <section className="media-capability-boundary">
        <div><p className="section-kicker">调研后的能力边界</p><h2>本次接入与 GRS AI 平台能力的对应关系</h2></div>
        <ul>
          <li><strong>已接入</strong><span>Veo 3.1 Fast / Pro、首帧图生视频、可选尾帧、横竖画幅、异步轮询、任务归属校验。</span></li>
          <li><strong>平台支持但暂未开放</strong><span>Fast 最多三张参考图；官方明确要求不能与首尾帧同时使用，后续应作为独立模式设计。</span></li>
          <li><strong>平台配套能力</strong><span>API Key、调用日志与消耗、充值、模型列表、对象存储转存、公告和在线接口文档。</span></li>
          <li><strong>工程边界</strong><span>本机不执行视频生成，只提交云端任务；当前结果未自动转存 MinIO，需在两小时内手动下载。</span></li>
        </ul>
      </section>
    </main>
  );
}


function statusLabel(status: VeoTaskResponse["status"]) {
  return { submitting: "正在提交", running: "生成中", succeeded: "生成完成", failed: "生成失败" }[status];
}


function resultMessage(task: VeoTaskResponse) {
  if (task.status === "failed") return "任务未能完成";
  if (task.status === "succeeded") return task.video_url ? "视频已生成" : "Mock 任务已完成";
  if (task.status === "submitting") return "正在提交到 GRS AI";
  return "GRS AI 正在生成视频";
}
