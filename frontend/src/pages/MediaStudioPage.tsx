import { ArrowRight, AudioLines, Film, Image as ImageIcon, Settings2 } from "lucide-react";
import { useEffect, useState, type ComponentType } from "react";
import { Link } from "react-router";
import { useAuth } from "../contexts/AuthContext";
import { fetchMediaProviderOptions, fetchMediaWorkbenches, fetchVeoOptions } from "../lib/api";
import type {
  MediaProviderOptions,
  MediaWorkbenchConfig,
  VeoOptionsResponse,
} from "../types";
import "./media-studio.css";


type WorkbenchCardMeta = {
  icon: ComponentType<{ "aria-hidden"?: boolean }>;
  eyebrow: string;
  action: string;
  to: string;
  steps: string[];
};

const cards: Record<MediaWorkbenchConfig["slug"], WorkbenchCardMeta> = {
  "audio-clone": {
    icon: AudioLines,
    eyebrow: "声音创作",
    action: "进入克隆音频",
    to: "/media-studio/audio-clone",
    steps: ["上传参考音色", "输入朗读文本", "获取克隆语音"],
  },
  "image-to-image": {
    icon: ImageIcon,
    eyebrow: "图像创作",
    action: "进入图生图",
    to: "/media-studio/image-to-image",
    steps: ["上传一张或多张参考图", "描述合成要求", "获取一张生成图片"],
  },
};

const veoCard: WorkbenchCardMeta = {
  icon: Film,
  eyebrow: "视频创作",
  action: "进入 Wan 图生视频",
  to: "/media-studio/veo",
  steps: ["上传首帧或填写图片 URL", "描述动作与镜头", "获取 Wan 视频"],
};


export function MediaStudioPage() {
  const { user } = useAuth();
  const [workbenches, setWorkbenches] = useState<MediaWorkbenchConfig[]>([]);
  const [mediaOptions, setMediaOptions] = useState<MediaProviderOptions | null>(null);
  const [veoOptions, setVeoOptions] = useState<VeoOptionsResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    void Promise.allSettled([
      fetchMediaWorkbenches(controller.signal),
      fetchMediaProviderOptions(controller.signal),
      fetchVeoOptions(controller.signal),
    ]).then(([workbenchResult, mediaOptionsResult, veoOptionsResult]) => {
      if (controller.signal.aborted) return;

      if (workbenchResult.status === "fulfilled") {
        setWorkbenches(workbenchResult.value);
      } else {
        setError(workbenchResult.reason instanceof Error ? workbenchResult.reason.message : "原有媒体工作台加载失败");
      }
      if (mediaOptionsResult.status === "fulfilled") setMediaOptions(mediaOptionsResult.value);
      if (veoOptionsResult.status === "fulfilled") setVeoOptions(veoOptionsResult.value);
    });
    return () => controller.abort();
  }, []);

  const mediaRuntimeLabel = mediaOptions?.mock_mode ? "Mock 安全模式" : "真实运行模式";
  const VeoIcon = veoCard.icon;

  return (
    <main className="workbench-hub">
      <header className="workbench-hub-hero">
        <div>
          <p className="eyebrow">AI 媒体创作</p>
          <h1>选择一个工作台开始创作</h1>
          <p>原有克隆音频、GRS AI 图生图工作流完整保留，视频生成使用阿里云百炼 Wan 2.7。</p>
        </div>
        <div className={`workbench-runtime-badge ${mediaOptions?.mock_mode ? "is-mock" : ""}`}>
          <strong>{mediaRuntimeLabel}</strong>
          <span>
            原媒体任务：{mediaOptions?.mock_mode ? "不会产生第三方费用" : "执行时可能产生供应商费用"}
            {" · "}
            Wan 视频：{veoOptions?.configured ? (veoOptions.mock_mode ? "Mock" : "已配置") : "待配置"}
          </span>
        </div>
      </header>

      {error ? <div className="workbench-error" role="alert">{error}</div> : null}

      <section className="workbench-card-grid" aria-label="媒体工作台列表">
        {workbenches.map((workbench) => {
          const meta = cards[workbench.slug];
          const Icon = meta.icon;
          return (
            <article className={`workbench-entry-card workbench-entry-card--${workbench.slug}`} key={workbench.slug}>
              <div className="workbench-entry-icon"><Icon aria-hidden /></div>
              <p>{meta.eyebrow}</p>
              <h2>{workbench.display_name}</h2>
              <p>{workbench.description}</p>
              <ol>{meta.steps.map((step) => <li key={step}>{step}</li>)}</ol>
              {workbench.configured ? (
                <Link to={meta.to}>{meta.action}<ArrowRight aria-hidden /></Link>
              ) : (
                <div className="workbench-not-ready">
                  <strong>尚未完成配置</strong>
                  <span>{workbench.configuration_issues[0] ?? "请在配置页检查供应商和工作流设置"}</span>
                </div>
              )}
            </article>
          );
        })}

        <article className="workbench-entry-card workbench-entry-card--veo-video">
          <div className="workbench-entry-icon"><VeoIcon aria-hidden /></div>
          <p>{veoCard.eyebrow}</p>
          <h2>Wan 2.7 图生视频</h2>
          <p>使用首帧或首尾帧生成舞台分镜、动作示范和创意短片。</p>
          <ol>{veoCard.steps.map((step) => <li key={step}>{step}</li>)}</ol>
          {veoOptions?.configured ? (
            <Link to={veoCard.to}>{veoCard.action}<ArrowRight aria-hidden /></Link>
          ) : (
            <div className="workbench-not-ready">
              <strong>尚未完成配置</strong>
              <span>请在服务端配置 DASHSCOPE_API_KEY，或开启 VIDEO_MOCK_MODE</span>
            </div>
          )}
        </article>
      </section>

      {user?.role === "teacher" ? (
        <footer className="workbench-config-entry">
          <div>
            <Settings2 aria-hidden />
            <span>
              <strong>原工作台配置</strong>
              <small>绑定 RunningHub 克隆音频工作流和 GRS AI 图生图模型</small>
            </span>
          </div>
          <Link to="/media-studio/configuration">打开配置页<ArrowRight aria-hidden /></Link>
        </footer>
      ) : null}
    </main>
  );
}
