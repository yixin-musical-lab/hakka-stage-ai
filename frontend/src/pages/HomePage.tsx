import { useEffect, useState } from "react";
import { Link } from "react-router";
import { ModuleTile } from "../components/home/ModuleTile";
import { Button } from "../components/ui/button";
import {
  fetchHealth,
  fetchClassInteractions,
  fetchLessonPlans,
  fetchMovementGuides,
  fetchMusicalFusionPlans,
  fetchMusicalScripts,
  fetchPracticeSubmissions,
  fetchRoleTrainingPlans,
  fetchSongAdaptations,
} from "../lib/api";
import { futureModules } from "../lib/lessonPlanDefaults";
import type {
  ClassInteractionSummary,
  HealthResponse,
  LessonPlanSummary,
  MovementGuideSummary,
  MusicalFusionPlanSummary,
  MusicalScriptSummary,
  PracticeSubmissionSummary,
  RoleTrainingPlanSummary,
  SongAdaptationSummary,
} from "../types";

export function HomePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [lessonPlans, setLessonPlans] = useState<LessonPlanSummary[]>([]);
  const [classInteractions, setClassInteractions] = useState<ClassInteractionSummary[]>([]);
  const [musicalScripts, setMusicalScripts] = useState<MusicalScriptSummary[]>([]);
  const [songAdaptations, setSongAdaptations] = useState<SongAdaptationSummary[]>([]);
  const [musicalFusionPlans, setMusicalFusionPlans] = useState<MusicalFusionPlanSummary[]>([]);
  const [roleTrainingPlans, setRoleTrainingPlans] = useState<RoleTrainingPlanSummary[]>([]);
  const [movementGuides, setMovementGuides] = useState<MovementGuideSummary[]>([]);
  const [practiceSubmissions, setPracticeSubmissions] = useState<PracticeSubmissionSummary[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    void fetchHealth(controller.signal).then(setHealth).catch(() => setHealth(null));
    void fetchLessonPlans(controller.signal).then(setLessonPlans).catch(() => setLessonPlans([]));
    void fetchClassInteractions(controller.signal).then(setClassInteractions).catch(() => setClassInteractions([]));
    void fetchMusicalScripts(controller.signal).then(setMusicalScripts).catch(() => setMusicalScripts([]));
    void fetchSongAdaptations(controller.signal).then(setSongAdaptations).catch(() => setSongAdaptations([]));
    void fetchMusicalFusionPlans(controller.signal).then(setMusicalFusionPlans).catch(() => setMusicalFusionPlans([]));
    void fetchRoleTrainingPlans(controller.signal).then(setRoleTrainingPlans).catch(() => setRoleTrainingPlans([]));
    void fetchMovementGuides(controller.signal).then(setMovementGuides).catch(() => setMovementGuides([]));
    void fetchPracticeSubmissions(controller.signal).then(setPracticeSubmissions).catch(() => setPracticeSubmissions([]));
    return () => controller.abort();
  }, []);

  const latestPlan = lessonPlans[0];
  const latestInteraction = classInteractions[0];
  const latestScript = musicalScripts[0];
  const latestSongAdaptation = songAdaptations[0];
  const latestMusicalFusionPlan = musicalFusionPlans[0];
  const latestMovementGuide = movementGuides[0];
  const latestPracticeSubmission = practiceSubmissions[0];
  const configuredModelProviders =
    health?.dependencies
      .filter((dependency) => ["deepseek", "qwen"].includes(dependency.name) && dependency.configured)
      .map((dependency) => dependency.name)
      .join(" / ") || "配置待检查";
  const workbenchItems = [
    {
      label: "课堂互动",
      title: latestInteraction ? latestInteraction.title : "还没有保存的课堂互动方案",
      to: latestInteraction ? `/interactions/${latestInteraction.id}` : "/interactions/generate",
      action: latestInteraction ? "打开" : "创建",
    },
    {
      label: "最近剧本",
      title: latestScript ? latestScript.title : "还没有保存的剧本",
      to: latestScript ? `/musical-scripts/${latestScript.id}` : "/musical-scripts/generate",
      action: latestScript ? "打开" : "创建",
    },
    {
      label: "唱段适配",
      title: latestSongAdaptation ? latestSongAdaptation.title : "还没有保存的唱段适配",
      to: latestSongAdaptation ? `/song-adaptations/${latestSongAdaptation.id}` : "/musical-scripts",
      action: latestSongAdaptation ? "打开" : "生成",
    },
    {
      label: "歌舞融合",
      title: latestMusicalFusionPlan ? latestMusicalFusionPlan.title : "还没有保存的歌舞融合方案",
      to: latestMusicalFusionPlan ? `/musical-fusion-plans/${latestMusicalFusionPlan.id}` : "/musical-fusion-plans/generate",
      action: latestMusicalFusionPlan ? "打开" : "生成",
    },
    {
      label: "训练计划",
      title: `已保存 ${roleTrainingPlans.length} 份分角色训练计划`,
      to: "/role-training-plans",
      action: "查看",
    },
    {
      label: "示范材料",
      title: latestMovementGuide ? latestMovementGuide.title : "还没有保存的动作图解",
      to: latestMovementGuide ? `/movement-guides/${latestMovementGuide.id}` : "/movement-guides/new",
      action: latestMovementGuide ? "打开" : "创建",
    },
    {
      label: "课后练习",
      title: latestPracticeSubmission ? latestPracticeSubmission.task_title : "还没有练习视频提交",
      to: latestPracticeSubmission ? `/practice-submissions/${latestPracticeSubmission.id}` : "/practice-submissions/new",
      action: latestPracticeSubmission ? "打开" : "创建",
    },
    {
      label: "最近教案",
      title: latestPlan ? latestPlan.title : "还没有保存的教案",
      to: latestPlan ? `/lesson-plans/${latestPlan.id}` : "/lesson-plans/generate",
      action: latestPlan ? "打开" : "创建",
    },
  ];
  const overviewItems = [
    { label: "教案", count: lessonPlans.length, to: "/lesson-plans" },
    { label: "互动", count: classInteractions.length, to: "/interactions" },
    { label: "剧本", count: musicalScripts.length, to: "/musical-scripts" },
    { label: "唱段", count: songAdaptations.length, to: "/song-adaptations" },
    { label: "融合", count: musicalFusionPlans.length, to: "/musical-fusion-plans" },
    { label: "训练", count: roleTrainingPlans.length, to: "/role-training-plans" },
    { label: "示范", count: movementGuides.length, to: "/movement-guides" },
    { label: "练习", count: practiceSubmissions.length, to: "/practice-submissions" },
  ];
  const totalAssets =
    lessonPlans.length +
    classInteractions.length +
    musicalScripts.length +
    songAdaptations.length +
    musicalFusionPlans.length +
    roleTrainingPlans.length +
    movementGuides.length +
    practiceSubmissions.length;

  return (
    <main className="page-frame">
      <section className="home-hero">
        <div className="home-hero-main">
          <div className="hero-copy">
            <p className="eyebrow">教学闭环 / 创编闭环</p>
            <h1>把备课、排练与复盘收进一个清楚的工作台</h1>
            <p className="intro">
              从课前教案到课堂互动、示范材料、课后练习和歌舞剧创编，按老师的实际工作顺序集中管理。
            </p>
            <div className="hero-actions">
              <Button asChild>
                <Link to="/lesson-plans/generate">新建教案</Link>
              </Button>
              <Button asChild variant="secondary">
                <Link to="/lesson-plans">查看已保存</Link>
              </Button>
              <Button asChild variant="secondary">
                <Link to="/musical-scripts/generate">新建剧本</Link>
              </Button>
            </div>
          </div>

          <div className="hero-workbench" aria-label="最近工作">
            <div className="hero-workbench-header">
              <div>
                <p className="section-kicker">最近工作</p>
                <h2>继续推进</h2>
              </div>
              <Button asChild variant="secondary" size="sm">
                <Link to="/musical-scripts">剧本库</Link>
              </Button>
            </div>
            <div className="hero-workbench-grid">
              {workbenchItems.map((item) => (
                <Link className="hero-workbench-card" key={item.label} to={item.to}>
                  <span>
                    <small>{item.label}</small>
                    <strong>{item.title}</strong>
                  </span>
                  <em>{item.action}</em>
                </Link>
              ))}
            </div>
          </div>
        </div>
        <aside className="hero-overview" aria-label="工作台概览">
          <div className="hero-overview-panel">
            <div className="hero-overview-heading">
              <p>工作台概览</p>
              <strong>{totalAssets} 份资产</strong>
              <span>系统连接与生成资产集中看这一处。</span>
            </div>

            <div className="hero-overview-status">
              <div>
                <span>API</span>
                <strong>{health?.status === "ok" ? "运行中" : "等待连接"}</strong>
              </div>
              <div>
                <span>LLM</span>
                <strong>{configuredModelProviders}</strong>
              </div>
            </div>

            <ol className="hero-overview-list">
              {overviewItems.map((item, index) => (
                <li key={item.label}>
                  <Link to={item.to}>
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    <strong>{item.label}</strong>
                    <em>{item.count} 份</em>
                  </Link>
                </li>
              ))}
            </ol>
          </div>
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
          title="课堂互动"
          status="已接入"
          description="生成老师可现场照着执行的互动规则、逐步脚本、口令、学生动作、安全提醒和备用方案。"
          to="/interactions/generate"
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
          title="唱段适配"
          status="已接入"
          description="基于剧本、歌词和人工音乐段落表生成演唱分配、改词建议和间奏留白。"
          to="/song-adaptations"
        />
        <ModuleTile
          title="歌舞融合"
          status="已接入"
          description="基于剧本和唱段适配生成唱、跳、队形、衔接及排练结构建议。"
          to="/musical-fusion-plans"
        />
        <ModuleTile
          title="分角色训练"
          status="已接入"
          description="基于已确认剧本生成主角、配角、旁白、群演、领舞等角色训练任务。"
          to="/role-training-plans"
        />
        <ModuleTile
          title="示范材料"
          status="已接入"
          description="管理动作描述、步骤拆解、关键提示和示范视频 / 图片材料。"
          to="/movement-guides"
        />
        <ModuleTile
          title="课后练习"
          status="已接入"
          description="记录学生练习视频，生成基础观察报告，并保存老师复核后的反馈。"
          to="/practice-submissions"
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
    </main>
  );
}
