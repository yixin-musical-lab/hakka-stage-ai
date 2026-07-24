import {
  Activity,
  AlertTriangle,
  ArrowDownToLine,
  CheckCircle2,
  Clock3,
  ExternalLink,
  FileVideo2,
  Footprints,
  Gauge,
  ImagePlus,
  LoaderCircle,
  Move3d,
  PersonStanding,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { PageTitle } from "../components/ui/PageTitle";
import { Progress } from "../components/ui/progress";
import {
  createMotionTransferTask,
  fetchMotionTransferOptions,
  fetchMotionTransferTask,
  fetchMotionTransferTasks,
  isAbortError,
  motionTransferResultUrl,
} from "../lib/api";
import { formatDateTime } from "../lib/format";
import type {
  MotionTransferMode,
  MotionTransferOptionsResponse,
  MotionTransferTaskResponse,
} from "../types";
import "./veo-video-workbench.css";
import "./motion-transfer-workbench.css";


type Notice = { type: "status" | "error"; text: string } | null;
type MediaDimensions = { width: number; height: number };

const TERMINAL_STATUSES = new Set(["succeeded", "failed"]);


export function MotionTransferWorkbenchPage() {
  const [options, setOptions] = useState<MotionTransferOptionsResponse | null>(null);
  const [tasks, setTasks] = useState<MotionTransferTaskResponse[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [personImage, setPersonImage] = useState<File | null>(null);
  const [motionVideo, setMotionVideo] = useState<File | null>(null);
  const [personPreviewUrl, setPersonPreviewUrl] = useState("");
  const [motionPreviewUrl, setMotionPreviewUrl] = useState("");
  const [personDimensions, setPersonDimensions] = useState<MediaDimensions | null>(null);
  const [motionDimensions, setMotionDimensions] = useState<MediaDimensions | null>(null);
  const [motionDuration, setMotionDuration] = useState<number | null>(null);
  const [mode, setMode] = useState<MotionTransferMode>("wan-std");
  const [watermark, setWatermark] = useState(true);
  const [rightsConfirmed, setRightsConfirmed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      fetchMotionTransferOptions(controller.signal),
      fetchMotionTransferTasks(controller.signal),
    ])
      .then(([loadedOptions, loadedTasks]) => {
        setOptions(loadedOptions);
        setTasks(loadedTasks);
        setSelectedTaskId(loadedTasks[0]?.id ?? "");
        if (loadedOptions.modes[0]) setMode(loadedOptions.modes[0].code);
      })
      .catch((caughtError) => {
        if (!isAbortError(caughtError)) {
          setNotice({
            type: "error",
            text: caughtError instanceof Error ? caughtError.message : "动作模仿工作台加载失败。",
          });
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    return () => {
      if (personPreviewUrl) URL.revokeObjectURL(personPreviewUrl);
      if (motionPreviewUrl) URL.revokeObjectURL(motionPreviewUrl);
    };
  }, [personPreviewUrl, motionPreviewUrl]);

  const pendingTaskIds = useMemo(
    () => tasks.filter((task) => !TERMINAL_STATUSES.has(task.status)).map((task) => task.id).join(","),
    [tasks],
  );

  useEffect(() => {
    if (!pendingTaskIds) return;
    const ids = pendingTaskIds.split(",");
    const refreshPendingTasks = async () => {
      const results = await Promise.allSettled(ids.map((taskId) => fetchMotionTransferTask(taskId)));
      setTasks((current) => current.map((task) => {
        const resultIndex = ids.indexOf(task.id);
        const result = resultIndex >= 0 ? results[resultIndex] : null;
        return result?.status === "fulfilled" ? result.value : task;
      }));
    };
    void refreshPendingTasks();
    const timer = window.setInterval(() => void refreshPendingTasks(), 15_000);
    return () => window.clearInterval(timer);
  }, [pendingTaskIds]);

  const selectedTask = tasks.find((task) => task.id === selectedTaskId) ?? tasks[0] ?? null;
  const selectedMode = options?.modes.find((item) => item.code === mode);
  const estimatedPrice = motionDuration && selectedMode
    ? motionDuration * selectedMode.price_cny_per_second
    : null;

  function selectPersonImage(file: File | null) {
    if (personPreviewUrl) URL.revokeObjectURL(personPreviewUrl);
    setPersonImage(file);
    setPersonDimensions(null);
    setPersonPreviewUrl(file ? URL.createObjectURL(file) : "");
  }

  function selectMotionVideo(file: File | null) {
    if (motionPreviewUrl) URL.revokeObjectURL(motionPreviewUrl);
    setMotionVideo(file);
    setMotionDimensions(null);
    setMotionDuration(null);
    setMotionPreviewUrl(file ? URL.createObjectURL(file) : "");
  }

  function readPersonMetadata(event: React.SyntheticEvent<HTMLImageElement>) {
    setPersonDimensions({
      width: event.currentTarget.naturalWidth,
      height: event.currentTarget.naturalHeight,
    });
  }

  function readMotionMetadata(event: React.SyntheticEvent<HTMLVideoElement>) {
    const duration = event.currentTarget.duration;
    setMotionDuration(Number.isFinite(duration) ? Math.round(duration * 10) / 10 : null);
    setMotionDimensions({
      width: event.currentTarget.videoWidth,
      height: event.currentTarget.videoHeight,
    });
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || !options) return;
    if (!personImage) {
      setNotice({ type: "error", text: "请上传一张已获授权的单人人物图片。" });
      return;
    }
    if (!motionVideo) {
      setNotice({ type: "error", text: "请上传一段参考动作视频。" });
      return;
    }
    if (personImage.size > options.image_max_upload_mb * 1024 * 1024) {
      setNotice({ type: "error", text: `人物图片超过 ${options.image_max_upload_mb}MB，请压缩后重试。` });
      return;
    }
    if (motionVideo.size > options.video_max_upload_mb * 1024 * 1024) {
      setNotice({ type: "error", text: `参考视频超过 ${options.video_max_upload_mb}MB，请截取或压缩后重试。` });
      return;
    }
    const imageDimensionError = validateMediaDimensions(
      "人物图片",
      personDimensions,
      options.image_dimension_min_pixels,
      options.image_dimension_max_pixels,
      options.aspect_ratio_min,
      options.aspect_ratio_max,
    );
    if (imageDimensionError) {
      setNotice({ type: "error", text: imageDimensionError });
      return;
    }
    const videoDimensionError = validateMediaDimensions(
      "参考视频",
      motionDimensions,
      options.video_dimension_min_pixels,
      options.video_dimension_max_pixels,
      options.aspect_ratio_min,
      options.aspect_ratio_max,
    );
    if (videoDimensionError) {
      setNotice({ type: "error", text: videoDimensionError });
      return;
    }
    if (motionDuration === null) {
      setNotice({ type: "error", text: "暂时无法读取参考视频时长，请重新选择 MP4、AVI 或 MOV 文件。" });
      return;
    }
    if (motionDuration < options.duration_min_seconds || motionDuration > options.duration_max_seconds) {
      setNotice({
        type: "error",
        text: `参考视频当前为 ${formatDuration(motionDuration)}，百炼要求 ${options.duration_min_seconds}～${options.duration_max_seconds} 秒。`,
      });
      return;
    }
    if (!rightsConfirmed) {
      setNotice({ type: "error", text: "请确认人物肖像和参考动作视频已经取得使用授权。" });
      return;
    }

    setSubmitting(true);
    setUploadProgress(0);
    setNotice({ type: "status", text: "正在上传人物图片与动作视频，并创建百炼异步任务……" });
    try {
      const created = await createMotionTransferTask(
        {
          personImage,
          motionVideo,
          mode,
          watermark,
          motionDurationSeconds: motionDuration,
          rightsConfirmed,
        },
        setUploadProgress,
      );
      setTasks((current) => [created, ...current.filter((task) => task.id !== created.id)]);
      setSelectedTaskId(created.id);
      setNotice({ type: "status", text: "任务已提交。页面会每 15 秒刷新一次，生成完成后自动尝试转存结果。" });
    } catch (caughtError) {
      setNotice({ type: "error", text: caughtError instanceof Error ? caughtError.message : "创建动作模仿任务失败。" });
    } finally {
      setSubmitting(false);
    }
  }

  async function refreshSelectedTask() {
    if (!selectedTask || refreshing) return;
    setRefreshing(true);
    try {
      const updated = await fetchMotionTransferTask(selectedTask.id);
      setTasks((current) => current.map((task) => (task.id === updated.id ? updated : task)));
      setNotice({ type: "status", text: "已刷新动作模仿任务状态。" });
    } catch (caughtError) {
      setNotice({ type: "error", text: caughtError instanceof Error ? caughtError.message : "刷新任务失败。" });
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <main className="page-frame media-studio-page motion-transfer-page">
      <PageTitle
        eyebrow="媒体工作台 · 动作模仿"
        title="让定妆照跟随排练动作"
        description="上传一张人物图片和一段单人动作视频，由百炼 Wan 2.2 迁移动作与表情，并保留图片中的人物与背景。"
        action={
          <Button asChild variant="secondary">
            <a href="https://help.aliyun.com/zh/model-studio/wan-animate-move-api" target="_blank" rel="noreferrer">
              官方接口文档<ExternalLink aria-hidden />
            </a>
          </Button>
        }
      />

      <section className="media-studio-summary motion-summary" aria-label="动作模仿能力摘要">
        <article><PersonStanding aria-hidden /><span><strong>单人定妆图片</strong><small>人物清晰完整，建议肩部到脚踝可见</small></span></article>
        <article><Footprints aria-hidden /><span><strong>2～30 秒动作样本</strong><small>动作和表情跟随参考视频迁移</small></span></article>
        <article><Gauge aria-hidden /><span><strong>720P · 双质量模式</strong><small>标准 15fps，专业 25fps</small></span></article>
        <article className={options?.configured ? "is-ready" : "is-warning"}>
          {options?.configured ? <CheckCircle2 aria-hidden /> : <AlertTriangle aria-hidden />}
          <span><strong>{options?.configured ? "动作通道已就绪" : "等待服务端配置"}</strong><small>{options?.mock_mode ? "当前为 Mock 联调模式" : "密钥与素材地址不会返回浏览器"}</small></span>
        </article>
      </section>

      <div className="media-studio-grid motion-studio-grid">
        <form className="media-generator-panel motion-generator-panel" onSubmit={submit}>
          <div className="media-panel-heading">
            <div><p className="section-kicker">角色 × 动作</p><h2>准备两份排练素材</h2></div>
            {options?.mock_mode ? <Badge variant="secondary">Mock</Badge> : <Badge>Wan Animate</Badge>}
          </div>

          <div className="motion-source-flow">
            <article className={`motion-source-card motion-source-card--person${personPreviewUrl ? " has-preview" : ""}${loading || submitting ? " is-disabled" : ""}`}>
              <span className="motion-source-index">01</span>
              <span className="motion-source-copy"><strong>人物定妆照</strong><small>决定人物形象与最终背景</small></span>
              {personPreviewUrl ? (
                <div className="motion-source-preview">
                  <img src={personPreviewUrl} alt="人物定妆照预览" onLoad={readPersonMetadata} />
                </div>
              ) : (
                <label className="motion-source-preview motion-source-picker" htmlFor="motion-person-input">
                  <ImagePlus aria-hidden /><span>选择人物图片</span><small>JPG / PNG / BMP / WEBP · ≤ {options?.image_max_upload_mb ?? 5}MB</small>
                </label>
              )}
              <input id="motion-person-input" className="motion-source-file-input" type="file" accept=".jpg,.jpeg,.png,.bmp,.webp,image/*" disabled={loading || submitting} onChange={(event) => selectPersonImage(event.target.files?.[0] ?? null)} />
              <div className="motion-source-footer">
                <span className="motion-source-meta">{personDimensions ? `${personDimensions.width} × ${personDimensions.height}px` : "等待图片"}</span>
                <label className="motion-source-replace" htmlFor="motion-person-input"><RefreshCw aria-hidden />{personPreviewUrl ? "更换图片" : "选择图片"}</label>
              </div>
            </article>

            <div className="motion-flow-mark" aria-hidden><Move3d /><span>动作轨迹</span></div>

            <article className={`motion-source-card motion-source-card--video${motionPreviewUrl ? " has-preview" : ""}${loading || submitting ? " is-disabled" : ""}`}>
              <span className="motion-source-index">02</span>
              <span className="motion-source-copy"><strong>参考动作视频</strong><small>决定动作、表情与节奏</small></span>
              {motionPreviewUrl ? (
                <div className="motion-source-preview">
                  <video src={motionPreviewUrl} muted controls playsInline preload="metadata" onLoadedMetadata={readMotionMetadata} />
                </div>
              ) : (
                <label className="motion-source-preview motion-source-picker" htmlFor="motion-video-input">
                  <FileVideo2 aria-hidden /><span>选择动作视频</span><small>MP4 / AVI / MOV · ≤ {options?.video_max_upload_mb ?? 200}MB</small>
                </label>
              )}
              <input id="motion-video-input" className="motion-source-file-input" type="file" accept=".mp4,.avi,.mov,video/mp4,video/quicktime,video/x-msvideo" disabled={loading || submitting} onChange={(event) => selectMotionVideo(event.target.files?.[0] ?? null)} />
              <div className="motion-source-footer">
                <span className="motion-source-meta">{motionDuration !== null && motionDimensions ? `${formatDuration(motionDuration)} · ${motionDimensions.width} × ${motionDimensions.height}px` : "等待视频"}</span>
                <label className="motion-source-replace" htmlFor="motion-video-input"><RefreshCw aria-hidden />{motionPreviewUrl ? "更换视频" : "选择视频"}</label>
              </div>
            </article>
          </div>

          <fieldset className="motion-quality-fieldset" disabled={loading || submitting}>
            <legend>生成质量</legend>
            <div className="motion-quality-grid">
              {options?.modes.map((item) => (
                <label key={item.code} className={mode === item.code ? "is-selected" : ""}>
                  <input type="radio" name="motion-mode" value={item.code} checked={mode === item.code} onChange={() => setMode(item.code)} />
                  <span><strong>{item.name}</strong><small>{item.frames_per_second}fps · ¥{item.price_cny_per_second.toFixed(1)}/秒</small></span>
                  <p>{item.description}</p>
                </label>
              ))}
            </div>
            <p className="motion-cost-estimate">
              {estimatedPrice === null ? "读取视频时长后显示费用估算" : `按当前 ${formatDuration(motionDuration ?? 0)} 估算约 ¥${estimatedPrice.toFixed(2)}，最终以百炼账单为准。`}
            </p>
          </fieldset>

          <div className="motion-safety-panel">
            <ShieldCheck aria-hidden />
            <div>
              <strong>素材授权与生成标识</strong>
              <label>
                <input type="checkbox" checked={rightsConfirmed} onChange={(event) => setRightsConfirmed(event.target.checked)} />
                <span>我确认人物肖像和参考动作视频已经取得使用授权</span>
              </label>
              <label>
                <input type="checkbox" checked={watermark} onChange={(event) => setWatermark(event.target.checked)} />
                <span>在结果右下角添加“千问 AI 生成”标识</span>
              </label>
            </div>
          </div>

          {submitting ? <div className="motion-upload-progress"><span><Upload aria-hidden />素材上传 {uploadProgress}%</span><Progress value={uploadProgress} /></div> : null}
          {notice ? <p className={`media-notice media-notice--${notice.type}`}>{notice.type === "error" ? <AlertTriangle aria-hidden /> : <Sparkles aria-hidden />}{notice.text}</p> : null}
          {!loading && !options?.configured ? <p className="media-config-hint">请配置 `DASHSCOPE_API_KEY` 和外网可访问的 `VIDEO_PUBLIC_BASE_URL`，或使用 `VIDEO_MOCK_MODE=true` 做无计费联调。</p> : null}
          <Button className="media-submit-button" type="submit" size="lg" disabled={loading || submitting || !options?.configured}>
            {submitting ? <><LoaderCircle aria-hidden className="media-spin" />正在上传并创建任务</> : <><Activity aria-hidden />开始动作模仿</>}
          </Button>
        </form>

        <section className="media-result-panel motion-result-panel" aria-live="polite">
          <div className="media-panel-heading">
            <div><p className="section-kicker">生成结果</p><h2>{selectedTask ? statusLabel(selectedTask.status) : "等待动作任务"}</h2></div>
            <Button variant="ghost" size="sm" type="button" disabled={!selectedTask || refreshing} onClick={() => void refreshSelectedTask()}><RefreshCw aria-hidden className={refreshing ? "media-spin" : ""} />刷新</Button>
          </div>

          {selectedTask ? (
            <>
              <div className={`media-result-preview motion-result-preview is-${selectedTask.status}`}>
                {selectedTask.result_available ? (
                  <video key={`${selectedTask.id}-${selectedTask.updated_at}`} src={motionTransferResultUrl(selectedTask.id)} controls playsInline preload="metadata" />
                ) : (
                  <div>{selectedTask.status === "failed" ? <AlertTriangle aria-hidden /> : selectedTask.status === "succeeded" ? <CheckCircle2 aria-hidden /> : <LoaderCircle aria-hidden className="media-spin" />}<strong>{resultMessage(selectedTask)}</strong><small>{selectedTask.status === "running" ? "动作迁移通常需要数分钟，复杂或较长素材可能等待更久。" : selectedTask.error_message || selectedTask.failure_reason}</small></div>
                )}
              </div>
              <div className="media-progress-row"><span><strong>{selectedTask.progress}%</strong><small>{statusLabel(selectedTask.status)}</small></span><Progress value={selectedTask.progress} /></div>
              <dl className="media-task-meta motion-task-meta"><div><dt>模型</dt><dd>{selectedTask.model}</dd></div><div><dt>模式</dt><dd>{modeLabel(selectedTask.mode)}</dd></div><div><dt>人物图片</dt><dd title={selectedTask.person_file_name}>{selectedTask.person_file_name}</dd></div><div><dt>动作视频</dt><dd title={selectedTask.motion_file_name}>{selectedTask.motion_file_name}</dd></div><div><dt>视频时长</dt><dd>{selectedTask.motion_duration_seconds ? formatDuration(selectedTask.motion_duration_seconds) : "未记录"}</dd></div><div><dt>结果存储</dt><dd>{resultStorageLabel(selectedTask, options?.mock_mode ?? false)}</dd></div></dl>
              {selectedTask.storage_warning ? <p className="media-notice media-notice--error"><AlertTriangle aria-hidden />{selectedTask.storage_warning}</p> : null}
              {selectedTask.result_available ? <Button asChild className="w-full"><a href={motionTransferResultUrl(selectedTask.id, true)}><ArrowDownToLine aria-hidden />下载动作模仿视频</a></Button> : null}
              <p className="media-expiry-note">任务记录保留约 {options?.result_url_ttl_hours ?? 24} 小时；生成成功后系统会优先转存结果，但仍建议及时下载归档。</p>
            </>
          ) : (
            <div className="media-empty-result motion-empty-result"><Footprints aria-hidden /><h3>动作轨迹将在这里合成</h3><p>人物形象来自定妆照，动作和表情来自参考视频；当前只支持单人动作模仿。</p></div>
          )}
        </section>
      </div>

      <section className="media-history-section">
        <div className="media-panel-heading"><div><p className="section-kicker">最近任务</p><h2>当前账号的动作模仿记录</h2></div><span>最多展示 12 条 · 本地任务保留 24 小时</span></div>
        {tasks.length ? <div className="media-task-list">{tasks.map((task) => <button key={task.id} type="button" className={selectedTask?.id === task.id ? "is-active" : ""} onClick={() => setSelectedTaskId(task.id)}><span className={`media-task-status is-${task.status}`}>{task.status === "succeeded" ? <CheckCircle2 aria-hidden /> : task.status === "failed" ? <AlertTriangle aria-hidden /> : <LoaderCircle aria-hidden className="media-spin" />}</span><span><strong>{task.person_file_name} × {task.motion_file_name}</strong><small>{modeLabel(task.mode)} · {task.motion_duration_seconds ? formatDuration(task.motion_duration_seconds) : "时长未知"} · {formatDateTime(task.created_at)}</small></span><em>{statusLabel(task.status)}</em></button>)}</div> : <div className="media-history-empty">还没有动作模仿任务。</div>}
      </section>

      <section className="media-capability-boundary motion-capability-boundary">
        <div><p className="section-kicker">素材成功率提示</p><h2>先把动作样本拍清楚，再让模型模仿</h2></div>
        <ul>{(options?.input_guidance ?? ["人物图片只保留一位主体。", "参考视频使用固定镜头。", "减少遮挡与快速出画。"]).map((item) => <li key={item}><strong>输入建议</strong><span>{item}</span></li>)}<li><strong>当前边界</strong><span>首版只接入保留图片背景的 wan2.2-animate-move；多人迁移、视频换人和长视频分段暂不开放。</span></li></ul>
      </section>
    </main>
  );
}


function statusLabel(status: MotionTransferTaskResponse["status"]) {
  return { submitting: "正在提交", running: "动作生成中", succeeded: "生成完成", failed: "生成失败" }[status];
}


function modeLabel(mode: MotionTransferMode) {
  return mode === "wan-pro" ? "专业模式 · 25fps" : "标准模式 · 15fps";
}


function resultMessage(task: MotionTransferTaskResponse) {
  if (task.status === "failed") return "任务未能完成";
  if (task.status === "succeeded") return task.result_available ? "动作视频已生成" : "Mock 任务已完成";
  if (task.status === "submitting") return "正在提交素材到阿里云百炼";
  return "Wan Animate 正在迁移动作与表情";
}


function resultStorageLabel(task: MotionTransferTaskResponse, mockMode: boolean) {
  if (task.result_persisted) return "已转存 MinIO";
  if (task.result_available) return "百炼临时地址";
  if (mockMode && task.status === "succeeded") return "Mock 不生成视频";
  return "等待生成";
}


function formatDuration(seconds: number) {
  if (seconds < 60) return `${seconds.toFixed(seconds % 1 ? 1 : 0)} 秒`;
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.round(seconds % 60);
  return `${minutes} 分 ${remaining} 秒`;
}


function validateMediaDimensions(
  label: string,
  dimensions: MediaDimensions | null,
  minPixels: number,
  maxPixels: number,
  minAspectRatio: number,
  maxAspectRatio: number,
) {
  if (!dimensions || dimensions.width <= 0 || dimensions.height <= 0) {
    return `暂时无法读取${label}尺寸，请重新导出后再上传。`;
  }
  const { width, height } = dimensions;
  if (width < minPixels || height < minPixels || width > maxPixels || height > maxPixels) {
    return `${label}当前为 ${width}×${height}px，宽高都必须在 ${minPixels}～${maxPixels}px 之间。`;
  }
  const aspectRatio = width / height;
  if (aspectRatio < minAspectRatio || aspectRatio > maxAspectRatio) {
    return `${label}当前宽高比不在百炼要求的 1:3～3:1 范围内。`;
  }
  return "";
}
