import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type DependencyConfig = {
  name: string;
  configured: boolean;
  endpoint: string;
};

type HealthResponse = {
  status: string;
  service: string;
  message: string;
  dependencies: DependencyConfig[];
};

const backendPort = "8000";

function resolveApiBaseUrl() {
  const configuredUrl = import.meta.env.VITE_API_BASE_URL?.trim();

  // VITE_API_BASE_URL 留空或设置为 auto 时，使用当前页面的主机名访问后端。
  // 这样 http://localhost:5173 和 http://172.x.x.x:5173 都会自动请求同一台机器的 :8000。
  if (!configuredUrl || configuredUrl.toLowerCase() === "auto") {
    return `${window.location.protocol}//${window.location.hostname}:${backendPort}`;
  }

  return configuredUrl.replace(/\/$/, "");
}

const apiBaseUrl = resolveApiBaseUrl();
const frontendUrl = window.location.origin;

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();

    async function checkBackend() {
      try {
        setLoading(true);
        setError("");

        // 当前页面唯一职责是验证前后端连通；后续业务页面再接入路由和状态管理。
        const response = await fetch(`${apiBaseUrl}/health`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`后端返回异常状态码：${response.status}`);
        }

        setHealth((await response.json()) as HealthResponse);
      } catch (caughtError) {
        if (caughtError instanceof DOMException && caughtError.name === "AbortError") {
          return;
        }

        setError(caughtError instanceof Error ? caughtError.message : "未知连接错误");
      } finally {
        setLoading(false);
      }
    }

    void checkBackend();

    return () => controller.abort();
  }, []);

  const isOnline = health?.status === "ok";

  return (
    <main className="shell">
      <section className="status-panel" aria-labelledby="page-title">
        <p className="eyebrow">hakka-stage-ai</p>
        <h1 id="page-title">客韵智演最小运行骨架</h1>
        <p className="intro">
          当前阶段只验证 Docker 服务与前后端连通，不包含教案生成、视频分析或 AI 报告业务逻辑。
        </p>

        <div className={isOnline ? "status-card online" : "status-card offline"}>
          <span className="status-dot" aria-hidden="true" />
          <div>
            <strong>{loading ? "正在连接后端..." : isOnline ? "前后端已连通" : "后端连接失败"}</strong>
            <p>{health?.message ?? error ?? "等待 /health 响应"}</p>
          </div>
        </div>

        <dl className="meta-grid">
          <div>
            <dt>前端入口</dt>
            <dd>{frontendUrl}</dd>
          </div>
          <div>
            <dt>后端健康检查</dt>
            <dd>{apiBaseUrl}/health</dd>
          </div>
        </dl>

        {health ? (
          <div className="dependency-list" aria-label="依赖配置状态">
            {health.dependencies.map((dependency) => (
              <article key={dependency.name} className="dependency-item">
                <span>{dependency.name}</span>
                <strong>{dependency.configured ? "已读取配置" : "配置缺失"}</strong>
                <small>{dependency.endpoint}</small>
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
