import { useEffect, useState } from "react";
import { Link } from "react-router";
import { ModuleTile } from "../components/home/ModuleTile";
import { StatusItem } from "../components/ui/StatusItem";
import { fetchHealth, fetchLessonPlans, fetchMusicalScripts, fetchRoleTrainingPlans } from "../lib/api";
import { futureModules } from "../lib/lessonPlanDefaults";
import type { HealthResponse, LessonPlanSummary, MusicalScriptSummary, RoleTrainingPlanSummary } from "../types";

export function HomePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [lessonPlans, setLessonPlans] = useState<LessonPlanSummary[]>([]);
  const [musicalScripts, setMusicalScripts] = useState<MusicalScriptSummary[]>([]);
  const [roleTrainingPlans, setRoleTrainingPlans] = useState<RoleTrainingPlanSummary[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    void fetchHealth(controller.signal).then(setHealth).catch(() => setHealth(null));
    void fetchLessonPlans(controller.signal).then(setLessonPlans).catch(() => setLessonPlans([]));
    void fetchMusicalScripts(controller.signal).then(setMusicalScripts).catch(() => setMusicalScripts([]));
    void fetchRoleTrainingPlans(controller.signal).then(setRoleTrainingPlans).catch(() => setRoleTrainingPlans([]));
    return () => controller.abort();
  }, []);

  const latestPlan = lessonPlans[0];
  const latestScript = musicalScripts[0];
  const configuredModelProviders =
    health?.dependencies
      .filter((dependency) => ["deepseek", "qwen"].includes(dependency.name) && dependency.configured)
      .map((dependency) => dependency.name)
      .join(" / ") || "配置待检查";

  return (
    <main className="page-frame">
      <section className="home-hero">
        <div>
          <p className="eyebrow">教学闭环 / 创编闭环</p>
          <h1>把备课、排练与复盘收进一个清楚的工作台</h1>
          <p className="intro">
            先从课前教案生成跑通真实 AI 链路，再逐步接入课堂互动、示范材料、课后练习和歌舞剧创编模块。
          </p>
          <div className="hero-actions">
            <Link className="primary-button link-button" to="/lesson-plans/generate">
              新建教案
            </Link>
            <Link className="secondary-button link-button" to="/lesson-plans">
              查看已保存
            </Link>
            <Link className="secondary-button link-button" to="/musical-scripts/generate">
              新建剧本
            </Link>
          </div>
        </div>
        <aside className="hero-status" aria-label="系统概况">
          <StatusItem label="API" value={health?.status === "ok" ? "运行中" : "等待连接"} />
          <StatusItem label="LLM" value={configuredModelProviders} />
          <StatusItem label="教案数量" value={`${lessonPlans.length} 份`} />
          <StatusItem label="剧本数量" value={`${musicalScripts.length} 份`} />
        </aside>
      </section>

      <section className="module-grid" aria-label="模块导航">
        <ModuleTile
          title="课前教案生成"
          status="已接入"
          description="填写课程条件，选择 DeepSeek 或百炼 Qwen 生成结构化教案，支持编辑保存和导出。"
          to="/lesson-plans/generate"
        />
        <ModuleTile
          title="教案资料库"
          status="已接入"
          description="查看已生成和已确认的教案，重新编辑并导出 Markdown。"
          to="/lesson-plans"
        />
        <ModuleTile
          title="歌舞剧创编"
          status="已接入"
          description="生成分幕剧情、人物设定、台词、旁白和舞蹈、独唱、群舞留白段落。"
          to="/musical-scripts/generate"
        />
        <ModuleTile
          title="分角色训练"
          status="已接入"
          description="基于已确认剧本生成主角、配角、旁白、群演、领舞等角色训练任务。"
          to="/role-training-plans"
        />
        {futureModules.map((moduleName) => (
          <ModuleTile
            key={moduleName}
            title={moduleName}
            status="即将接入"
            description="后续会沿用当前任务、编辑、保存和导出模式扩展。"
          />
        ))}
      </section>

      <section className="content-band">
        <div className="section-heading">
          <div>
            <p className="section-kicker">最近剧本</p>
            <h2>{latestScript ? latestScript.title : "还没有保存的剧本"}</h2>
          </div>
          {latestScript ? (
            <Link className="secondary-button link-button" to={`/musical-scripts/${latestScript.id}`}>
              打开
            </Link>
          ) : (
            <Link className="secondary-button link-button" to="/musical-scripts/generate">
              创建第一份
            </Link>
          )}
        </div>
      </section>

      <section className="content-band">
        <div className="section-heading">
          <div>
            <p className="section-kicker">训练计划</p>
            <h2>已保存 {roleTrainingPlans.length} 份分角色训练计划</h2>
          </div>
          <Link className="secondary-button link-button" to="/role-training-plans">
            查看
          </Link>
        </div>
      </section>

      <section className="content-band">
        <div className="section-heading">
          <div>
            <p className="section-kicker">最近教案</p>
            <h2>{latestPlan ? latestPlan.title : "还没有保存的教案"}</h2>
          </div>
          {latestPlan ? (
            <Link className="secondary-button link-button" to={`/lesson-plans/${latestPlan.id}`}>
              打开
            </Link>
          ) : (
            <Link className="secondary-button link-button" to="/lesson-plans/generate">
              创建第一份
            </Link>
          )}
        </div>
      </section>
    </main>
  );
}
