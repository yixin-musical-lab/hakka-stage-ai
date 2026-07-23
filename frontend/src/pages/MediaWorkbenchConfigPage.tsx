import {
  ArrowLeft,
  CheckCircle2,
  CloudCog,
  FileJson,
  Image as ImageIcon,
  LoaderCircle,
  Save,
  Upload,
  Workflow,
} from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { useAuth } from "../contexts/AuthContext";
import {
  configureRunningHubWorkflowVersion,
  fetchMediaProviderOptions,
  fetchMediaWorkbenches,
  fetchRunningHubWorkflows,
  importRunningHubWorkflow,
  publishRunningHubWorkflowVersion,
  updateMediaWorkbenchConfiguration,
  updateRunningHubWorkflow,
} from "../lib/api";
import type {
  MediaProviderOptions,
  MediaWorkbenchConfig,
  WorkbenchFieldConfig,
  WorkflowOutputConfig,
  WorkflowParameterConfig,
  WorkflowTemplate,
  WorkflowVersion,
} from "../types";
import "./media-workbenches.css";


function readableError(reason: unknown, fallback: string) {
  return reason instanceof Error ? reason.message : fallback;
}


function ProviderState({ configured, mockMode }: { configured: boolean; mockMode: boolean }) {
  const ready = configured || mockMode;
  return (
    <span className={`config-provider-state ${ready ? "is-ready" : "is-missing"}`}>
      {ready ? <CheckCircle2 aria-hidden /> : <CloudCog aria-hidden />}
      {mockMode ? "Mock 模式可用" : configured ? "服务端密钥已配置" : "服务端密钥未配置"}
    </span>
  );
}


function WorkflowVersionEditor({
  version,
  onReload,
}: {
  version: WorkflowVersion;
  onReload: () => Promise<void>;
}) {
  const [parameters, setParameters] = useState<WorkflowParameterConfig[]>(version.parameters);
  const [outputs, setOutputs] = useState<WorkflowOutputConfig[]>(version.outputs);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    // 切换版本后重建编辑草稿，避免把上一版本的节点配置误写到新版本。
    setParameters(version.parameters.map((item) => ({ ...item })));
    setOutputs(version.outputs.map((item) => ({ ...item })));
    setError("");
  }, [version.id, version.parameters, version.outputs]);

  function updateParameter(index: number, patch: Partial<WorkflowParameterConfig>) {
    setParameters((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  }

  function updateOutput(index: number, patch: Partial<WorkflowOutputConfig>) {
    setOutputs((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  }

  async function save(publishAfterSave: boolean) {
    setSaving(true);
    setError("");
    try {
      // 发布前先保存当前页面草稿，保证实际绑定的是教师刚确认过的字段定义。
      await configureRunningHubWorkflowVersion(version.id, parameters, outputs);
      if (publishAfterSave) await publishRunningHubWorkflowVersion(version.id);
      await onReload();
    } catch (reason) {
      setError(readableError(reason, "工作流版本保存失败"));
    } finally {
      setSaving(false);
    }
  }

  const published = version.status === "published";
  return (
    <details className="workflow-version-editor" open={!published}>
      <summary>
        <span>版本 v{version.version_number} · {version.source_filename}</span>
        <strong className={published ? "is-published" : "is-draft"}>{published ? "已发布" : "待配置"}</strong>
      </summary>
      <div className="workflow-version-body">
        <p className="config-help">
          自动识别出 {parameters.length} 个输入参数、{outputs.length} 个输出节点。节点 ID 和字段名来自原始 JSON，不允许在这里改写。
        </p>
        <div className="workflow-config-table">
          <div className="workflow-config-head"><span>节点字段</span><span>用户名称</span><span>类型</span><span>显示位置</span><span>必填</span></div>
          {parameters.map((parameter, index) => (
            <div className="workflow-config-row" key={parameter.key}>
              <code>{parameter.key}</code>
              <input aria-label={`${parameter.key} 用户名称`} disabled={published} value={parameter.label} onChange={(event) => updateParameter(index, { label: event.target.value })} />
              <select aria-label={`${parameter.key} 类型`} disabled={published} value={parameter.value_type} onChange={(event) => updateParameter(index, { value_type: event.target.value as WorkflowParameterConfig["value_type"] })}>
                <option value="text">文本</option><option value="number">数字</option><option value="boolean">开关</option>
                <option value="file">文件</option><option value="select">选项</option><option value="json">JSON</option>
              </select>
              <select aria-label={`${parameter.key} 显示位置`} disabled={published} value={parameter.visibility} onChange={(event) => updateParameter(index, { visibility: event.target.value as WorkflowParameterConfig["visibility"] })}>
                <option value="basic">基础</option><option value="advanced">高级</option><option value="hidden">隐藏</option>
              </select>
              <label className="config-checkbox"><input type="checkbox" disabled={published} checked={parameter.required} onChange={(event) => updateParameter(index, { required: event.target.checked })} /><span>必填</span></label>
            </div>
          ))}
        </div>

        <div className="workflow-output-config">
          <h4>输出节点</h4>
          {outputs.length ? outputs.map((output, index) => (
            <div key={`${output.node_id}-${index}`}>
              <code>{output.node_id} · {output.class_type}</code>
              <input aria-label={`${output.node_id} 输出名称`} disabled={published} value={output.label} onChange={(event) => updateOutput(index, { label: event.target.value })} />
              <select aria-label={`${output.node_id} 媒体类型`} disabled={published} value={output.media_type} onChange={(event) => updateOutput(index, { media_type: event.target.value as WorkflowOutputConfig["media_type"] })}>
                <option value="audio">音频</option><option value="image">图片</option><option value="video">视频</option>
              </select>
              <label className="config-checkbox"><input type="checkbox" disabled={published} checked={output.enabled} onChange={(event) => updateOutput(index, { enabled: event.target.checked })} /><span>启用</span></label>
              <label className="config-checkbox"><input type="checkbox" disabled={published} checked={output.primary} onChange={(event) => updateOutput(index, { primary: event.target.checked })} /><span>主输出</span></label>
            </div>
          )) : <p className="config-help">未自动识别到输出节点，请先检查工作流是否包含保存音频、图片或视频的节点。</p>}
        </div>
        {error ? <div className="workbench-error" role="alert">{error}</div> : null}
        {!published ? (
          <div className="config-actions">
            <button type="button" className="config-secondary-button" disabled={saving} onClick={() => void save(false)}><Save aria-hidden />保存草稿</button>
            <button type="button" className="config-primary-button" disabled={saving || !outputs.some((item) => item.enabled)} onClick={() => void save(true)}>{saving ? <LoaderCircle className="is-spinning" aria-hidden /> : <CheckCircle2 aria-hidden />}保存并发布</button>
          </div>
        ) : null}
      </div>
    </details>
  );
}


function WorkflowTemplateCard({ template, onReload }: { template: WorkflowTemplate; onReload: () => Promise<void> }) {
  const [name, setName] = useState(template.name);
  const [description, setDescription] = useState(template.description);
  const [workflowId, setWorkflowId] = useState(template.external_workflow_id);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setName(template.name);
    setDescription(template.description);
    setWorkflowId(template.external_workflow_id);
  }, [template.id, template.name, template.description, template.external_workflow_id]);

  async function saveTemplate(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await updateRunningHubWorkflow(template.id, {
        name,
        description,
        external_workflow_id: workflowId,
        media_type: template.media_type,
      });
      await onReload();
    } catch (reason) {
      setError(readableError(reason, "工作流信息保存失败"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="workflow-library-card">
      <header><div><span>RunningHub · {template.media_type}</span><h3>{template.name}</h3></div><strong>{template.versions.length} 个版本</strong></header>
      <form className="workflow-template-form" onSubmit={saveTemplate}>
        <label className="config-field"><span>工作流名称</span><input required value={name} onChange={(event) => setName(event.target.value)} /></label>
        <label className="config-field config-field--wide"><span>说明</span><input value={description} onChange={(event) => setDescription(event.target.value)} /></label>
        <label className="config-field"><span>RunningHub workflowId</span><input required value={workflowId} onChange={(event) => setWorkflowId(event.target.value)} placeholder="平台工作流 ID" /></label>
        <button className="config-secondary-button" disabled={saving} type="submit"><Save aria-hidden />保存信息</button>
      </form>
      {error ? <div className="workbench-error" role="alert">{error}</div> : null}
      <div className="workflow-version-list">
        {template.versions.map((version) => <WorkflowVersionEditor key={version.id} version={version} onReload={onReload} />)}
      </div>
    </article>
  );
}


export function MediaWorkbenchConfigPage() {
  const { user } = useAuth();
  const [options, setOptions] = useState<MediaProviderOptions | null>(null);
  const [audioConfig, setAudioConfig] = useState<MediaWorkbenchConfig | null>(null);
  const [imageConfig, setImageConfig] = useState<MediaWorkbenchConfig | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<"audio" | "image" | "import" | "">("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [importFile, setImportFile] = useState<File | null>(null);
  const [importName, setImportName] = useState("IndexTTS2 音色克隆");
  const [importDescription, setImportDescription] = useState("克隆音色并支持情绪参考的音频生成工作流");
  const [importWorkflowId, setImportWorkflowId] = useState("");
  const [importTemplateId, setImportTemplateId] = useState("");

  async function load() {
    const [workbenchData, providerData, workflowData] = await Promise.all([
      fetchMediaWorkbenches(), fetchMediaProviderOptions(), fetchRunningHubWorkflows(),
    ]);
    setAudioConfig(workbenchData.find((item) => item.slug === "audio-clone") ?? null);
    setImageConfig(workbenchData.find((item) => item.slug === "image-to-image") ?? null);
    setOptions(providerData);
    setWorkflows(workflowData);
  }

  useEffect(() => {
    if (user?.role !== "teacher") { setLoading(false); return; }
    void load().catch((reason: unknown) => setError(readableError(reason, "配置加载失败"))).finally(() => setLoading(false));
  }, [user?.role]);

  const publishedVersions = useMemo(() => workflows.flatMap((template) => template.versions
    .filter((version) => version.status === "published")
    .map((version) => ({ template, version }))), [workflows]);
  const selectedAudioVersion = publishedVersions.find(({ version }) => version.id === audioConfig?.workflow_version_id)?.version;
  const textParameters = selectedAudioVersion?.parameters.filter((item) => item.value_type === "text") ?? [];
  const fileParameters = selectedAudioVersion?.parameters.filter((item) => item.value_type === "file") ?? [];
  const provider = (key: string) => options?.providers.find((item) => item.key === key);

  function updateAudioField(section: "prompt" | "primary_asset" | "secondary_asset", patch: Partial<WorkbenchFieldConfig>) {
    setAudioConfig((current) => {
      if (!current) return current;
      const fallback: WorkbenchFieldConfig = section === "secondary_asset"
        ? { label: "情绪参考", help_text: "可选；用于参考语气和情绪", required: false, media_type: "audio", target_parameter_key: "" }
        : current.input_config[section] as WorkbenchFieldConfig;
      return { ...current, input_config: { ...current.input_config, [section]: { ...(current.input_config[section] ?? fallback), ...patch } } };
    });
  }

  function selectAudioVersion(versionId: string) {
    const version = publishedVersions.find((item) => item.version.id === versionId)?.version;
    setAudioConfig((current) => current ? {
      ...current,
      workflow_version_id: versionId || null,
      input_config: {
        ...current.input_config,
        // 更换工作流后清空旧节点绑定，避免同名 key 偶然命中造成错误调用。
        prompt: { ...current.input_config.prompt, target_parameter_key: "" },
        primary_asset: { ...current.input_config.primary_asset, target_parameter_key: "" },
        secondary_asset: current.input_config.secondary_asset ? { ...current.input_config.secondary_asset, target_parameter_key: "" } : null,
        exposed_parameter_keys: [],
      },
      workflow_parameters: version?.parameters ?? [],
    } : current);
  }

  function toggleAudioParameter(key: string) {
    setAudioConfig((current) => {
      if (!current) return current;
      const selected = new Set(current.input_config.exposed_parameter_keys);
      if (selected.has(key)) selected.delete(key); else selected.add(key);
      return { ...current, input_config: { ...current.input_config, exposed_parameter_keys: [...selected] } };
    });
  }

  async function saveAudio(event: FormEvent) {
    event.preventDefault();
    if (!audioConfig) return;
    setSaving("audio"); setError(""); setNotice("");
    try {
      await updateMediaWorkbenchConfiguration("audio-clone", {
        display_name: audioConfig.display_name,
        description: audioConfig.description,
        workflow_version_id: audioConfig.workflow_version_id,
        model: "",
        provider_api_mode: "workflow",
        default_parameters: audioConfig.default_parameters,
        input_config: audioConfig.input_config,
        enabled: audioConfig.enabled,
      });
      await load();
      setNotice("克隆音频工作台配置已保存，用户侧只会看到这里开放的输入项。");
    } catch (reason) {
      setError(readableError(reason, "克隆音频配置保存失败"));
    } finally { setSaving(""); }
  }

  async function saveImage(event: FormEvent) {
    event.preventDefault();
    if (!imageConfig) return;
    setSaving("image"); setError(""); setNotice("");
    try {
      await updateMediaWorkbenchConfiguration("image-to-image", {
        display_name: imageConfig.display_name,
        description: imageConfig.description,
        workflow_version_id: null,
        model: imageConfig.model,
        provider_api_mode: "unified",
        default_parameters: imageConfig.default_parameters,
        input_config: imageConfig.input_config,
        enabled: imageConfig.enabled,
      });
      await load();
      setNotice("图生图工作台配置已保存。");
    } catch (reason) {
      setError(readableError(reason, "图生图配置保存失败"));
    } finally { setSaving(""); }
  }

  async function importWorkflow(event: FormEvent) {
    event.preventDefault();
    if (!importFile) return;
    setSaving("import"); setError(""); setNotice("");
    try {
      await importRunningHubWorkflow({
        file: importFile,
        name: importName,
        description: importDescription,
        mediaType: "audio",
        workflowId: importWorkflowId,
        templateId: importTemplateId || undefined,
      });
      setImportFile(null);
      setImportTemplateId("");
      await load();
      setNotice("工作流 JSON 已导入并完成自动识别，请在工作流库中检查参数和输出后发布。");
    } catch (reason) {
      setError(readableError(reason, "工作流导入失败"));
    } finally { setSaving(""); }
  }

  if (user?.role !== "teacher") {
    return <main className="workbench-config-page"><div className="config-access-denied"><CloudCog aria-hidden /><h1>此页面仅供教师配置</h1><p>工作台会沿用教师已经发布的供应商与工作流配置。</p><Link to="/media-studio">返回媒体工作台</Link></div></main>;
  }

  if (loading) return <main className="workbench-config-page"><div className="config-loading"><LoaderCircle className="is-spinning" aria-hidden />正在加载工作台配置……</div></main>;

  return (
    <main className="workbench-config-page">
      <header className="config-page-header">
        <Link to="/media-studio"><ArrowLeft aria-hidden />返回工作台</Link>
        <div><p className="eyebrow">教师配置中心</p><h1>工作流与 GRS AI API 配置</h1><p>把供应商节点、模型与默认参数集中配置一次，用户工作台只保留素材、提示词和结果。</p></div>
      </header>
      {error ? <div className="workbench-error" role="alert">{error}</div> : null}
      {notice ? <div className="config-notice" role="status"><CheckCircle2 aria-hidden />{notice}</div> : null}

      <nav className="config-section-nav" aria-label="配置页目录">
        <a href="#audio-workbench">克隆音频绑定</a><a href="#image-workbench">图生图 API</a><a href="#workflow-library">RunningHub 工作流库</a>
      </nav>

      {audioConfig ? (
        <section className="config-section" id="audio-workbench">
          <header className="config-section-header"><div className="config-section-icon"><Workflow aria-hidden /></div><div><p>工作台 01</p><h2>克隆音频 · RunningHub 绑定</h2><span>选择已发布版本，再把用户输入映射到自动识别出的 ComfyUI 节点字段。</span></div><ProviderState configured={Boolean(provider("runninghub")?.configured)} mockMode={Boolean(options?.mock_mode)} /></header>
          <form className="config-form" onSubmit={saveAudio}>
            <div className="config-form-grid">
              <label className="config-field"><span>工作台名称</span><input value={audioConfig.display_name} onChange={(event) => setAudioConfig({ ...audioConfig, display_name: event.target.value })} /></label>
              <label className="config-field config-field--wide"><span>工作台说明</span><input value={audioConfig.description} onChange={(event) => setAudioConfig({ ...audioConfig, description: event.target.value })} /></label>
              <label className="config-field config-field--wide"><span>已发布工作流版本</span><select required value={audioConfig.workflow_version_id ?? ""} onChange={(event) => selectAudioVersion(event.target.value)}><option value="">请选择已发布版本</option>{publishedVersions.map(({ template, version }) => <option key={version.id} value={version.id}>{template.name} · v{version.version_number}</option>)}</select><small>没有可选项时，请先在下方导入 JSON、确认自动识别结果并发布。</small></label>
            </div>
            <div className="binding-grid">
              <div className="binding-card"><strong>合成文本</strong><label className="config-field"><span>用户侧名称</span><input value={audioConfig.input_config.prompt.label} onChange={(event) => updateAudioField("prompt", { label: event.target.value })} /></label><label className="config-field"><span>绑定文本参数</span><select required value={audioConfig.input_config.prompt.target_parameter_key} onChange={(event) => updateAudioField("prompt", { target_parameter_key: event.target.value })}><option value="">请选择文本节点</option>{textParameters.map((item) => <option key={item.key} value={item.key}>{item.label} · {item.key}</option>)}</select></label></div>
              <div className="binding-card"><strong>参考音色</strong><label className="config-field"><span>用户侧名称</span><input value={audioConfig.input_config.primary_asset.label} onChange={(event) => updateAudioField("primary_asset", { label: event.target.value })} /></label><label className="config-field"><span>绑定文件参数</span><select required value={audioConfig.input_config.primary_asset.target_parameter_key} onChange={(event) => updateAudioField("primary_asset", { target_parameter_key: event.target.value })}><option value="">请选择文件节点</option>{fileParameters.map((item) => <option key={item.key} value={item.key}>{item.label} · {item.key}</option>)}</select></label></div>
              <div className="binding-card"><strong>情绪参考</strong><label className="config-field"><span>用户侧名称</span><input value={audioConfig.input_config.secondary_asset?.label ?? "情绪参考"} onChange={(event) => updateAudioField("secondary_asset", { label: event.target.value })} /></label><label className="config-field"><span>绑定文件参数</span><select value={audioConfig.input_config.secondary_asset?.target_parameter_key ?? ""} onChange={(event) => updateAudioField("secondary_asset", { target_parameter_key: event.target.value })}><option value="">不在工作台显示</option>{fileParameters.map((item) => <option key={item.key} value={item.key}>{item.label} · {item.key}</option>)}</select></label><label className="config-checkbox"><input type="checkbox" checked={Boolean(audioConfig.input_config.secondary_asset?.required)} onChange={(event) => updateAudioField("secondary_asset", { required: event.target.checked })} /><span>要求用户必须上传；未勾选时沿用 RunningHub 工作流默认输入</span></label></div>
            </div>
            {selectedAudioVersion ? <div className="exposed-parameters"><h3>用户侧高级参数</h3><p>勾选后才会出现在克隆音频工作台，其余节点参数沿用工作流默认值。文件和 JSON 参数必须在工作流层处理，不会作为普通文本输入开放。</p><div>{selectedAudioVersion.parameters.filter((item) => ["text", "number", "boolean", "select"].includes(item.value_type) && ![audioConfig.input_config.prompt.target_parameter_key, audioConfig.input_config.primary_asset.target_parameter_key, audioConfig.input_config.secondary_asset?.target_parameter_key].includes(item.key)).map((item) => <label className="config-checkbox" key={item.key}><input type="checkbox" checked={audioConfig.input_config.exposed_parameter_keys.includes(item.key)} onChange={() => toggleAudioParameter(item.key)} /><span>{item.label}<small>{item.key}</small></span></label>)}</div></div> : null}
            <div className="config-actions"><label className="config-switch"><input type="checkbox" checked={audioConfig.enabled} onChange={(event) => setAudioConfig({ ...audioConfig, enabled: event.target.checked })} /><span>启用克隆音频工作台</span></label><button className="config-primary-button" disabled={saving === "audio"} type="submit">{saving === "audio" ? <LoaderCircle className="is-spinning" aria-hidden /> : <Save aria-hidden />}保存克隆音频配置</button></div>
          </form>
        </section>
      ) : null}

      {imageConfig ? (
        <section className="config-section" id="image-workbench">
          <header className="config-section-header"><div className="config-section-icon config-section-icon--image"><ImageIcon aria-hidden /></div><div><p>工作台 02</p><h2>图生图 · GRS AI Unified API</h2><span>模型与默认输出参数由教师维护，参考图会在任务提交时从 MinIO 安全读取。</span></div><ProviderState configured={Boolean(provider("grsai")?.configured)} mockMode={Boolean(options?.mock_mode)} /></header>
          <form className="config-form" onSubmit={saveImage}>
            <div className="config-form-grid">
              <label className="config-field"><span>工作台名称</span><input value={imageConfig.display_name} onChange={(event) => setImageConfig({ ...imageConfig, display_name: event.target.value })} /></label>
              <label className="config-field config-field--wide"><span>工作台说明</span><input value={imageConfig.description} onChange={(event) => setImageConfig({ ...imageConfig, description: event.target.value })} /></label>
              <label className="config-field"><span>模型</span><select required value={imageConfig.model} onChange={(event) => setImageConfig({ ...imageConfig, model: event.target.value })}>{(provider("grsai")?.models ?? ["nano-banana-fast"]).map((model) => <option value={model} key={model}>{model}</option>)}</select></label>
              <label className="config-field"><span>接口模式</span><input readOnly value="Unified · /v1/api/generate" /><small>图生图固定使用支持 images 输入的统一接口。</small></label>
              <label className="config-field"><span>默认画幅</span><select value={String(imageConfig.default_parameters.aspectRatio ?? "auto")} onChange={(event) => setImageConfig({ ...imageConfig, default_parameters: { ...imageConfig.default_parameters, aspectRatio: event.target.value } })}><option value="auto">自动</option><option value="1:1">1:1</option><option value="16:9">16:9</option><option value="9:16">9:16</option><option value="4:3">4:3</option><option value="3:4">3:4</option></select></label>
              <label className="config-field"><span>默认尺寸</span><select value={String(imageConfig.default_parameters.imageSize ?? "1K")} onChange={(event) => setImageConfig({ ...imageConfig, default_parameters: { ...imageConfig.default_parameters, imageSize: event.target.value } })}><option value="1K">1K</option><option value="2K">2K</option><option value="4K">4K</option></select></label>
            </div>
            <div className="config-security-note"><CloudCog aria-hidden /><div><strong>API Key 不在页面保存</strong><span>请在后端环境变量中配置 GRSAI_API_KEY 和 GRSAI_BASE_URL。页面只显示“是否已配置”，不会回传密钥内容。</span></div></div>
            <div className="config-actions"><label className="config-switch"><input type="checkbox" checked={imageConfig.enabled} onChange={(event) => setImageConfig({ ...imageConfig, enabled: event.target.checked })} /><span>启用图生图工作台</span></label><button className="config-primary-button" disabled={saving === "image"} type="submit">{saving === "image" ? <LoaderCircle className="is-spinning" aria-hidden /> : <Save aria-hidden />}保存图生图配置</button></div>
          </form>
        </section>
      ) : null}

      <section className="config-section" id="workflow-library">
        <header className="config-section-header"><div className="config-section-icon"><FileJson aria-hidden /></div><div><p>RunningHub 管理</p><h2>工作流 JSON 导入与二次配置</h2><span>支持 ComfyUI API 格式 JSON。每次导入保存为独立版本，已发布版本保持不可变。</span></div></header>
        <form className="workflow-import-form" onSubmit={importWorkflow}>
          <label className="config-field"><span>导入方式</span><select value={importTemplateId} onChange={(event) => setImportTemplateId(event.target.value)}><option value="">创建新工作流</option>{workflows.map((item) => <option key={item.id} value={item.id}>作为“{item.name}”的新版本</option>)}</select></label>
          <label className="config-field"><span>工作流名称</span><input disabled={Boolean(importTemplateId)} required={!importTemplateId} value={importName} onChange={(event) => setImportName(event.target.value)} /></label>
          <label className="config-field"><span>RunningHub workflowId</span><input value={importWorkflowId} onChange={(event) => setImportWorkflowId(event.target.value)} placeholder="可先导入，真实调用前必须补齐" /></label>
          <label className="config-field config-field--wide"><span>说明</span><input disabled={Boolean(importTemplateId)} value={importDescription} onChange={(event) => setImportDescription(event.target.value)} /></label>
          <label className={`workflow-json-upload ${importFile ? "is-ready" : ""}`}><input type="file" accept="application/json,.json" required onChange={(event) => setImportFile(event.target.files?.[0] ?? null)} />{importFile ? <FileJson aria-hidden /> : <Upload aria-hidden />}<span><strong>{importFile?.name ?? "选择 ComfyUI API JSON"}</strong><small>最大 5MB；导入后自动识别节点参数与媒体输出</small></span></label>
          <button className="config-primary-button" disabled={saving === "import" || !importFile} type="submit">{saving === "import" ? <LoaderCircle className="is-spinning" aria-hidden /> : <Upload aria-hidden />}导入并识别</button>
        </form>
        <div className="workflow-library-list">
          {workflows.length ? workflows.map((template) => <WorkflowTemplateCard key={template.id} template={template} onReload={load} />) : <div className="config-empty-workflows"><Workflow aria-hidden /><strong>还没有 RunningHub 工作流</strong><span>先导入用户提供的 ComfyUI API JSON，系统会建立参数草稿。</span></div>}
        </div>
      </section>
    </main>
  );
}
