import { useEffect, useState } from "react";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { StatusItem } from "../components/ui/StatusItem";
import { fetchHealth, isAbortError } from "../lib/api";
import type { HealthResponse } from "../types";

export function HealthPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    void fetchHealth(controller.signal)
      .then((data) => {
        setHealth(data);
        setNotice("");
      })
      .catch((caughtError) => {
        if (isAbortError(caughtError)) {
          return;
        }
        setNotice(caughtError instanceof Error ? caughtError.message : "后端连接失败。");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="系统状态"
        title="/health 连通检查"
        description="这个页面只负责展示后端健康检查和关键依赖配置状态。"
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在检查系统状态" text="等待后端 /health 响应。" /> : null}

      {health ? (
        <section className="health-grid">
          <StatusItem label="服务" value={health.service} />
          <StatusItem label="状态" value={health.status} />
          <StatusItem label="消息" value={health.message} />
          {health.dependencies.map((dependency) => (
            <Card asChild className="dependency-card" key={dependency.name}>
              <article>
                <Badge variant={dependency.configured ? "default" : "secondary"}>{dependency.configured ? "已配置" : "缺失"}</Badge>
                <h2>{dependency.name}</h2>
                <p>{dependency.endpoint}</p>
              </article>
            </Card>
          ))}
        </section>
      ) : null}
    </main>
  );
}
