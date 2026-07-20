import { ArrowRight, AudioLines, Image as ImageIcon, Settings2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router";
import { useAuth } from "../contexts/AuthContext";
import { fetchMediaProviderOptions, fetchMediaWorkbenches } from "../lib/api";
import type { MediaProviderOptions, MediaWorkbenchConfig } from "../types";
import "./media-studio.css";


const cards = {
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
    steps: ["上传参考图片", "描述修改要求", "获取生成图片"],
  },
};


export function MediaStudioPage() {
  const { user } = useAuth();
  const [workbenches, setWorkbenches] = useState<MediaWorkbenchConfig[]>([]);
  const [options, setOptions] = useState<MediaProviderOptions | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([fetchMediaWorkbenches(controller.signal), fetchMediaProviderOptions(controller.signal)])
      .then(([workbenchData, providerData]) => { setWorkbenches(workbenchData); setOptions(providerData); })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "工作台加载失败");
      });
    return () => controller.abort();
  }, []);

  return (
    <main className="workbench-hub">
      <header className="workbench-hub-hero">
        <div>
          <p className="eyebrow">AI 媒体创作</p>
          <h1>选择一个工作台开始创作</h1>
          <p>工作流和供应商参数已由配置页统一管理。你只需要提供素材、输入要求，然后等待结果。</p>
        </div>
        <div className={`workbench-runtime-badge ${options?.mock_mode ? "is-mock" : ""}`}>
          <strong>{options?.mock_mode ? "Mock 安全模式" : "真实运行模式"}</strong>
          <span>{options?.mock_mode ? "不会产生第三方费用" : "执行任务会产生供应商费用"}</span>
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
                  <span>{workbench.configuration_issues[0]}</span>
                </div>
              )}
            </article>
          );
        })}
      </section>

      {user?.role === "teacher" ? (
        <footer className="workbench-config-entry">
          <div><Settings2 aria-hidden /><span><strong>工作台配置</strong><small>绑定 RunningHub 工作流和 GRS AI 模型</small></span></div>
          <Link to="/media-studio/configuration">打开配置页<ArrowRight aria-hidden /></Link>
        </footer>
      ) : null}
    </main>
  );
}
