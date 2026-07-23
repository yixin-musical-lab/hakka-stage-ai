import { ArrowLeft, AudioLines, FileAudio, LoaderCircle, Play, Plus, Settings2, Upload } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { MediaTaskCreateDialog } from "../components/media/MediaTaskCreateDialog";
import { MediaTaskHistory, isActiveMediaTask } from "../components/media/MediaTaskHistory";
import { useAuth } from "../contexts/AuthContext";
import { fetchMediaGenerations, fetchMediaWorkbench, runMediaWorkbench, uploadMediaAsset } from "../lib/api";
import type { MediaGeneration, MediaWorkbenchConfig, WorkflowParameterConfig } from "../types";
import "./media-workbenches.css";


function ParameterInput({
  parameter,
  value,
  onChange,
}: {
  parameter: WorkflowParameterConfig;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  if (parameter.value_type === "boolean") {
    return <input type="checkbox" checked={Boolean(value)} onChange={(event) => onChange(event.target.checked)} />;
  }
  if (parameter.value_type === "select") {
    return (
      <select value={String(value ?? "")} onChange={(event) => onChange(event.target.value)}>
        {parameter.options.map((option) => <option value={String(option)} key={String(option)}>{String(option)}</option>)}
      </select>
    );
  }
  return (
    <input
      type={parameter.value_type === "number" ? "number" : "text"}
      value={String(value ?? "")}
      min={parameter.minimum ?? undefined}
      max={parameter.maximum ?? undefined}
      onChange={(event) => onChange(parameter.value_type === "number" ? Number(event.target.value) : event.target.value)}
    />
  );
}


export function AudioCloneWorkbenchPage() {
  const { user } = useAuth();
  const [config, setConfig] = useState<MediaWorkbenchConfig | null>(null);
  const [tasks, setTasks] = useState<MediaGeneration[]>([]);
  const [text, setText] = useState("");
  const [voiceAssetId, setVoiceAssetId] = useState("");
  const [emotionAssetId, setEmotionAssetId] = useState("");
  const [voiceName, setVoiceName] = useState("");
  const [emotionName, setEmotionName] = useState("");
  const [parameters, setParameters] = useState<Record<string, unknown>>({});
  const [uploading, setUploading] = useState<"voice" | "emotion" | "">("");
  const [submitting, setSubmitting] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [pageError, setPageError] = useState("");
  const [formError, setFormError] = useState("");
  const [historyError, setHistoryError] = useState("");

  async function loadHistory() {
    try {
      setTasks(await fetchMediaGenerations(undefined, "audio-clone"));
      setHistoryError("");
    } catch (reason) {
      // 历史记录异常不应阻断当前创作表单，单独在输出区域提示。
      setHistoryError(reason instanceof Error ? reason.message : "生成记录加载失败");
    }
  }

  async function load() {
    const configData = await fetchMediaWorkbench("audio-clone");
    setConfig(configData);
    await loadHistory();
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

  const exposedParameters = useMemo(() => {
    if (!config) return [];
    const exposed = new Set(config.input_config.exposed_parameter_keys);
    return config.workflow_parameters.filter((parameter) => exposed.has(parameter.key));
  }, [config]);

  async function upload(kind: "voice" | "emotion", file: File) {
    setUploading(kind);
    setFormError("");
    try {
      const result = await uploadMediaAsset(file);
      if (result.asset.media_type !== "audio") throw new Error("请选择音频文件");
      if (kind === "voice") { setVoiceAssetId(result.asset.id); setVoiceName(file.name); }
      else { setEmotionAssetId(result.asset.id); setEmotionName(file.name); }
    } catch (reason) {
      setFormError(reason instanceof Error ? reason.message : "音频上传失败");
    } finally {
      setUploading("");
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!config || !voiceAssetId) return;
    setSubmitting(true);
    setFormError("");
    void runMediaWorkbench("audio-clone", {
      prompt: text,
      primary_asset_id: voiceAssetId,
      secondary_asset_id: emotionAssetId || null,
      parameters,
      client_request_id: crypto.randomUUID(),
    }).then(async () => {
      setText("");
      await loadHistory();
      setIsCreateOpen(false);
    }).catch((reason: unknown) => setFormError(reason instanceof Error ? reason.message : "任务创建失败"))
      .finally(() => setSubmitting(false));
  }

  return (
    <main className="focused-workbench focused-workbench--audio">
      <header className="focused-workbench-header">
        <Link to="/media-studio"><ArrowLeft aria-hidden />返回工作台</Link>
        <div><span><AudioLines aria-hidden /></span><div><p className="eyebrow">RunningHub 工作流</p><h1>{config?.display_name ?? "克隆音频"}</h1><p>{config?.description}</p></div></div>
        <div className="focused-workbench-actions">
          <button type="button" className="focused-create-button" disabled={!config?.configured} onClick={() => { setFormError(""); setIsCreateOpen(true); }}><Plus aria-hidden />创建任务</button>
          {user?.role === "teacher" ? <Link className="focused-config-link" to="/media-studio/configuration"><Settings2 aria-hidden />配置</Link> : null}
        </div>
      </header>
      {pageError ? <div className="workbench-error" role="alert">{pageError}</div> : null}
      {config && !config.configured ? <div className="workbench-blocked"><strong>工作台尚未配置完成</strong>{config.configuration_issues.map((issue) => <span key={issue}>{issue}</span>)}</div> : null}

      <section className="focused-task-section" aria-labelledby="audio-task-list-title">
        <header className="focused-task-section-header">
          <div><p>任务概览</p><h2 id="audio-task-list-title">全部克隆音频任务</h2><span>创建、等待与已完成结果都会集中显示在这里。</span></div>
          <strong>{tasks.length}<small>个任务</small></strong>
        </header>
        {historyError ? <div className="workbench-error" role="alert">任务记录暂时无法读取：{historyError}</div> : null}
        <MediaTaskHistory tasks={tasks} onReload={loadHistory} />
      </section>

      <MediaTaskCreateDialog
        open={isCreateOpen}
        title="创建克隆音频任务"
        description="上传参考声音并填写合成文本，任务创建后可以关闭弹窗继续浏览历史结果。"
        busy={submitting || Boolean(uploading)}
        onClose={() => setIsCreateOpen(false)}
      >
        {formError ? <div className="workbench-error" role="alert">{formError}</div> : null}
        <form className="media-create-form" onSubmit={submit}>
          <label className="focused-field"><span>{config?.input_config.prompt.label ?? "合成文本"}<small>{config?.input_config.prompt.help_text}</small></span><textarea data-dialog-initial-focus rows={7} required value={text} onChange={(event) => setText(event.target.value)} placeholder="输入希望用克隆音色朗读的文字……" /></label>
          <div className="focused-upload-grid">
            <label className={`focused-upload ${voiceAssetId ? "is-ready" : ""}`}>
              <input type="file" accept="audio/mpeg,audio/wav,audio/x-wav,audio/flac,.mp3,.wav,.flac" required={!voiceAssetId} onChange={(event) => { const file = event.target.files?.[0]; if (file) void upload("voice", file); }} />
              {uploading === "voice" ? <LoaderCircle className="is-spinning" aria-hidden /> : voiceAssetId ? <FileAudio aria-hidden /> : <Upload aria-hidden />}
              <strong>{config?.input_config.primary_asset.label ?? "参考音色"}</strong>
              <span>{voiceName || config?.input_config.primary_asset.help_text}</span>
            </label>
            {config?.input_config.secondary_asset?.target_parameter_key ? (
              <label className={`focused-upload ${emotionAssetId ? "is-ready" : ""}`}>
                <input type="file" accept="audio/mpeg,audio/wav,audio/x-wav,audio/flac,.mp3,.wav,.flac" required={Boolean(config.input_config.secondary_asset.required && !emotionAssetId)} onChange={(event) => { const file = event.target.files?.[0]; if (file) void upload("emotion", file); }} />
                {uploading === "emotion" ? <LoaderCircle className="is-spinning" aria-hidden /> : emotionAssetId ? <FileAudio aria-hidden /> : <Upload aria-hidden />}
                <strong>{config.input_config.secondary_asset.label}</strong>
                <span>{emotionName || config.input_config.secondary_asset.help_text || "可选"}</span>
              </label>
            ) : null}
          </div>
          {exposedParameters.length ? (
            <details className="focused-advanced"><summary>高级设置</summary><div>{exposedParameters.map((parameter) => <label className="focused-field" key={parameter.key}><span>{parameter.label}<small>{parameter.description}</small></span><ParameterInput parameter={parameter} value={parameters[parameter.key] ?? parameter.default} onChange={(value) => setParameters((current) => ({ ...current, [parameter.key]: value }))} /></label>)}</div></details>
          ) : null}
          <button className="focused-run-button" type="submit" disabled={submitting || !config?.configured || !text.trim() || !voiceAssetId}>{submitting ? <LoaderCircle className="is-spinning" aria-hidden /> : <Play aria-hidden />}{submitting ? "正在创建任务" : "开始克隆音频"}</button>
        </form>
      </MediaTaskCreateDialog>
    </main>
  );
}
