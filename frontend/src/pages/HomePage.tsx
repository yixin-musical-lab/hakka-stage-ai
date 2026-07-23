import {
  Activity,
  ArrowRight,
  BookOpen,
  Check,
  Clapperboard,
  Drama,
  FileText,
  FolderKanban,
  GraduationCap,
  MessageSquareText,
  Music2,
  Plus,
  Sparkles,
  Users,
  Video,
} from "lucide-react";
import { useEffect, useState, type ComponentType } from "react";
import { Link } from "react-router";
import { ModuleTile } from "../components/home/ModuleTile";
import { Button } from "../components/ui/button";
import { useLayoutPreference } from "../contexts/LayoutPreferenceContext";
import { fetchHealth, fetchWorkspaceOverview, isAbortError } from "../lib/api";
import { apiDateTimeToEpoch, formatDateTime } from "../lib/format";
import { futureModules } from "../lib/lessonPlanDefaults";
import type { HealthResponse, WorkspaceOverviewResponse } from "../types";

type RecentAsset = {
  id: string;
  title: string;
  kind: string;
  updatedAt: string;
  to: string;
  icon: ComponentType<{ "aria-hidden"?: boolean }>;
};

export function HomePage() {
  const { layoutMode } = useLayoutPreference();
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [overview, setOverview] = useState<WorkspaceOverviewResponse | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    // 健康检查与轻量概览并行读取；概览接口只返回统计和九条最新摘要，不加载业务正文。
    void Promise.all([
      fetchHealth(controller.signal).then(setHealth).catch((caughtError) => resetUnlessAborted(caughtError, () => setHealth(null))),
      fetchWorkspaceOverview(controller.signal).then(setOverview).catch((caughtError) => resetUnlessAborted(caughtError, () => setOverview(null))),
    ]).finally(() => {
      if (active) setLoading(false);
    });
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  if (layoutMode === "classic") {
    return <ClassicHomePage health={health} overview={overview} />;
  }

  const latestPlan = overview?.lesson_plans.latest;
  const latestInteraction = overview?.class_interactions.latest;
  const latestScript = overview?.musical_scripts.latest;
  const latestSongAdaptation = overview?.song_adaptations.latest;
  const latestMusicalFusionPlan = overview?.musical_fusion_plans.latest;
  const latestRoleTrainingPlan = overview?.role_training_plans.latest;
  const latestMovementGuide = overview?.movement_guides.latest;
  const latestPracticeSubmission = overview?.practice_submissions.latest;
  const latestRehearsalReview = overview?.rehearsal_reviews.latest;

  const recentAssets: RecentAsset[] = [];
  if (latestPlan) recentAssets.push({ id: latestPlan.id, title: latestPlan.title, kind: "教案", updatedAt: latestPlan.updated_at, to: `/lesson-plans/${latestPlan.id}`, icon: BookOpen });
  if (latestInteraction) recentAssets.push({ id: latestInteraction.id, title: latestInteraction.title, kind: "课堂互动", updatedAt: latestInteraction.updated_at, to: `/interactions/${latestInteraction.id}`, icon: MessageSquareText });
  if (latestScript) recentAssets.push({ id: latestScript.id, title: latestScript.title, kind: "剧本", updatedAt: latestScript.updated_at, to: `/musical-scripts/${latestScript.id}`, icon: Drama });
  if (latestSongAdaptation) recentAssets.push({ id: latestSongAdaptation.id, title: latestSongAdaptation.title, kind: "唱段", updatedAt: latestSongAdaptation.updated_at, to: `/song-adaptations/${latestSongAdaptation.id}`, icon: Music2 });
  if (latestMusicalFusionPlan) recentAssets.push({ id: latestMusicalFusionPlan.id, title: latestMusicalFusionPlan.title, kind: "歌舞融合", updatedAt: latestMusicalFusionPlan.updated_at, to: `/musical-fusion-plans/${latestMusicalFusionPlan.id}`, icon: Sparkles });
  if (latestRoleTrainingPlan) recentAssets.push({ id: latestRoleTrainingPlan.id, title: latestRoleTrainingPlan.title, kind: "训练计划", updatedAt: latestRoleTrainingPlan.updated_at, to: `/role-training-plans/${latestRoleTrainingPlan.id}`, icon: Users });
  if (latestMovementGuide) recentAssets.push({ id: latestMovementGuide.id, title: latestMovementGuide.title, kind: "示范材料", updatedAt: latestMovementGuide.updated_at, to: `/movement-guides/${latestMovementGuide.id}`, icon: Video });
  if (latestPracticeSubmission) recentAssets.push({ id: latestPracticeSubmission.id, title: latestPracticeSubmission.title, kind: "课后练习", updatedAt: latestPracticeSubmission.updated_at, to: `/practice-submissions/${latestPracticeSubmission.id}`, icon: GraduationCap });
  if (latestRehearsalReview) recentAssets.push({ id: latestRehearsalReview.id, title: latestRehearsalReview.title, kind: "排练复盘", updatedAt: latestRehearsalReview.updated_at, to: `/rehearsal-reviews/${latestRehearsalReview.id}`, icon: Clapperboard });
  recentAssets.sort((left, right) => apiDateTimeToEpoch(right.updatedAt) - apiDateTimeToEpoch(left.updatedAt));

  // 当前后端尚未提供跨模块的项目归属关系，因此这里只做全站资产阶段汇总，
  // 不把不同课程、剧目或练习记录误判为同一个“当前项目”。
  const workflowStages = [
    { label: "策划", description: "确定主题与教学目标", count: (overview?.lesson_plans.count ?? 0) + (overview?.musical_scripts.count ?? 0), to: "/lesson-plans/generate" },
    { label: "教案", description: "教案与课堂互动", count: (overview?.lesson_plans.count ?? 0) + (overview?.class_interactions.count ?? 0), to: "/lesson-plans" },
    { label: "创编", description: "剧本、唱段与歌舞", count: (overview?.musical_scripts.count ?? 0) + (overview?.song_adaptations.count ?? 0) + (overview?.musical_fusion_plans.count ?? 0), to: "/musical-scripts" },
    { label: "训练", description: "角色与动作示范", count: (overview?.role_training_plans.count ?? 0) + (overview?.movement_guides.count ?? 0), to: "/role-training-plans" },
    { label: "排练", description: "练习提交与现场推进", count: overview?.practice_submissions.count ?? 0, to: "/practice-submissions" },
    { label: "复盘", description: "问题整理与改进计划", count: overview?.rehearsal_reviews.count ?? 0, to: "/rehearsal-reviews" },
  ];
  const filledStageCount = workflowStages.filter((stage) => stage.count > 0).length;
  const nextStageIndex = Math.min(workflowStages.findIndex((stage) => stage.count === 0), workflowStages.length - 1);
  const normalizedNextStageIndex = nextStageIndex < 0 ? workflowStages.length - 1 : nextStageIndex;
  const totalAssets = overview
    ? Object.values(overview).reduce((total, module) => total + module.count, 0)
    : 0;
  const currentAsset = recentAssets[0];
  const configuredProviders =
    health?.dependencies
      .filter((dependency) => ["deepseek", "qwen"].includes(dependency.name) && dependency.configured)
      .map((dependency) => dependency.name)
      .join(" / ") || "待配置";

  const quickCreateItems = [
    { title: "新建教案", description: "从课程目标开始备课", to: "/lesson-plans/generate", icon: BookOpen },
    { title: "新建课堂互动", description: "准备可执行的课堂脚本", to: "/interactions/generate", icon: MessageSquareText },
    { title: "新建剧本", description: "建立一台剧目的创编主线", to: "/musical-scripts/generate", icon: Drama },
    { title: "记录排练复盘", description: "整理问题和下一轮计划", to: "/rehearsal-reviews/generate", icon: Clapperboard },
  ];

  return (
    <main className="page-frame project-dashboard">
      <header className="dashboard-welcome">
        <div>
          <p className="eyebrow">工作中心</p>
          <h1>把一门课、一台剧目，从构想到复盘推进到底</h1>
          <p className="intro">用统一阶段视图连接生成内容、训练材料和排练记录。</p>
        </div>
        <div className="dashboard-welcome-actions">
          {loading ? <span className="dashboard-loading">正在汇总全站内容…</span> : null}
          <Button asChild><Link to="/musical-scripts/generate"><Plus aria-hidden />新建剧本创编</Link></Button>
          <Button asChild variant="secondary"><Link to="/lesson-plans/generate">新建教案</Link></Button>
        </div>
      </header>

      <section className="project-focus" aria-labelledby="workspace-overview-title">
        <div className="project-focus-heading">
          <div>
            <p className="section-kicker">全站资产概览</p>
            <h2 id="workspace-overview-title">教学与排演工作流</h2>
            <p>全站教学与创编资产按工作阶段汇总展示，具体内容仍保留在各自资料库中。</p>
          </div>
          <div className="project-focus-progress">
            <span>{filledStageCount} / {workflowStages.length} 工作阶段已有内容</span>
            <div aria-label={`工作阶段内容覆盖 ${filledStageCount} / ${workflowStages.length}`}>
              <span style={{ width: `${(filledStageCount / workflowStages.length) * 100}%` }} />
            </div>
          </div>
        </div>

        <ol className="project-stage-flow">
          {workflowStages.map((stage, index) => {
            const complete = stage.count > 0;
            const current = index === normalizedNextStageIndex;
            return (
              <li className={`${complete ? "is-complete" : ""}${current ? " is-current" : ""}`} key={stage.label}>
                <Link to={stage.to}>
                  <span className="project-stage-index">{complete ? <Check aria-hidden /> : String(index + 1).padStart(2, "0")}</span>
                  <span><strong>{stage.label}</strong><small>{stage.description}</small></span>
                  <em>{stage.count ? `${stage.count} 份` : "待开始"}</em>
                </Link>
              </li>
            );
          })}
        </ol>
      </section>

      <section className="dashboard-main-grid">
        <article className="continue-card">
          <div className="continue-card-icon"><FolderKanban aria-hidden /></div>
          <div className="continue-card-copy">
            <p className="section-kicker">继续推进</p>
            <h2>{currentAsset?.title ?? "还没有工作内容"}</h2>
            <p>{currentAsset ? `${currentAsset.kind} · 更新于 ${formatDateTime(currentAsset.updatedAt)}` : "先建立教案或剧本，首页会自动汇总最近内容。"}</p>
          </div>
          <Button asChild>
            <Link to={currentAsset?.to ?? "/lesson-plans/generate"}>{currentAsset ? "继续编辑" : "开始创建"}<ArrowRight aria-hidden /></Link>
          </Button>
        </article>

        <aside className="workspace-status-card" aria-label="工作空间状态">
          <div className="workspace-status-heading"><Activity aria-hidden /><span><small>工作空间状态</small><strong>{health?.status === "ok" ? "服务运行中" : "等待后端连接"}</strong></span></div>
          <dl>
            <div><dt>内容资产</dt><dd>{totalAssets} 份</dd></div>
            <div><dt>已配置模型</dt><dd>{configuredProviders}</dd></div>
            <div><dt>最近更新</dt><dd>{currentAsset ? formatDateTime(currentAsset.updatedAt) : "暂无"}</dd></div>
          </dl>
          <Link to="/health">查看详细状态<ArrowRight aria-hidden /></Link>
        </aside>
      </section>

      <section className="dashboard-section" aria-labelledby="quick-create-title">
        <div className="dashboard-section-heading">
          <div><p className="section-kicker">快捷入口</p><h2 id="quick-create-title">从关键工作开始</h2></div>
        </div>
        <div className="quick-create-grid">
          {quickCreateItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link key={item.to} to={item.to}>
                <span><Icon aria-hidden /></span>
                <strong>{item.title}</strong>
                <small>{item.description}</small>
                <ArrowRight aria-hidden className="quick-create-arrow" />
              </Link>
            );
          })}
        </div>
      </section>

      <section className="dashboard-section" aria-labelledby="recent-assets-title">
        <div className="dashboard-section-heading">
          <div><p className="section-kicker">最近资产</p><h2 id="recent-assets-title">最近更新</h2></div>
          <Link to="/lesson-plans">进入资料库<ArrowRight aria-hidden /></Link>
        </div>
        {recentAssets.length ? (
          <div className="recent-assets-list">
            {recentAssets.slice(0, 6).map((asset) => {
              const Icon = asset.icon;
              return (
                <Link key={`${asset.kind}-${asset.id}`} to={asset.to}>
                  <span className="recent-asset-icon"><Icon aria-hidden /></span>
                  <span><strong>{asset.title}</strong><small>{asset.kind}</small></span>
                  <time dateTime={asset.updatedAt}>{formatDateTime(asset.updatedAt)}</time>
                  <ArrowRight aria-hidden />
                </Link>
              );
            })}
          </div>
        ) : (
          <div className="dashboard-empty">
            <FileText aria-hidden />
            <div><strong>还没有内容资产</strong><p>创建第一份教案或剧本后，最近内容会集中显示在这里。</p></div>
          </div>
        )}
      </section>
    </main>
  );
}

function ClassicHomePage({
  health,
  overview,
}: {
  health: HealthResponse | null;
  overview: WorkspaceOverviewResponse | null;
}) {
  const latestPlan = overview?.lesson_plans.latest;
  const latestInteraction = overview?.class_interactions.latest;
  const latestScript = overview?.musical_scripts.latest;
  const latestSongAdaptation = overview?.song_adaptations.latest;
  const latestMusicalFusionPlan = overview?.musical_fusion_plans.latest;
  const latestMovementGuide = overview?.movement_guides.latest;
  const latestPracticeSubmission = overview?.practice_submissions.latest;
  const latestRehearsalReview = overview?.rehearsal_reviews.latest;
  const configuredModelProviders =
    health?.dependencies
      .filter((dependency) => ["deepseek", "qwen"].includes(dependency.name) && dependency.configured)
      .map((dependency) => dependency.name)
      .join(" / ") || "配置待检查";

  const workbenchItems = [
    {
      label: "课堂互动",
      title: latestInteraction?.title ?? "还没有保存的课堂互动方案",
      to: latestInteraction ? `/interactions/${latestInteraction.id}` : "/interactions/generate",
      action: latestInteraction ? "打开" : "创建",
    },
    {
      label: "最近剧本",
      title: latestScript?.title ?? "还没有保存的剧本",
      to: latestScript ? `/musical-scripts/${latestScript.id}` : "/musical-scripts/generate",
      action: latestScript ? "打开" : "创建",
    },
    {
      label: "唱段适配",
      title: latestSongAdaptation?.title ?? "还没有保存的唱段适配",
      to: latestSongAdaptation ? `/song-adaptations/${latestSongAdaptation.id}` : "/musical-scripts",
      action: latestSongAdaptation ? "打开" : "生成",
    },
    {
      label: "歌舞融合",
      title: latestMusicalFusionPlan?.title ?? "还没有保存的歌舞融合方案",
      to: latestMusicalFusionPlan ? `/musical-fusion-plans/${latestMusicalFusionPlan.id}` : "/musical-fusion-plans/generate",
      action: latestMusicalFusionPlan ? "打开" : "生成",
    },
    {
      label: "训练计划",
      title: `已保存 ${overview?.role_training_plans.count ?? 0} 份分角色训练计划`,
      to: "/role-training-plans",
      action: "查看",
    },
    {
      label: "排练复盘",
      title: latestRehearsalReview?.title ?? "还没有保存的排练复盘",
      to: latestRehearsalReview ? `/rehearsal-reviews/${latestRehearsalReview.id}` : "/rehearsal-reviews/generate",
      action: latestRehearsalReview ? "打开" : "创建",
    },
    {
      label: "示范材料",
      title: latestMovementGuide?.title ?? "还没有保存的动作图解",
      to: latestMovementGuide ? `/movement-guides/${latestMovementGuide.id}` : "/movement-guides/new",
      action: latestMovementGuide ? "打开" : "创建",
    },
    {
      label: "课后练习",
      title: latestPracticeSubmission?.title ?? "还没有练习视频提交",
      to: latestPracticeSubmission ? `/practice-submissions/${latestPracticeSubmission.id}` : "/practice-submissions/new",
      action: latestPracticeSubmission ? "打开" : "创建",
    },
    {
      label: "最近教案",
      title: latestPlan?.title ?? "还没有保存的教案",
      to: latestPlan ? `/lesson-plans/${latestPlan.id}` : "/lesson-plans/generate",
      action: latestPlan ? "打开" : "创建",
    },
  ];

  const overviewItems = [
    { label: "教案", count: overview?.lesson_plans.count ?? 0, to: "/lesson-plans" },
    { label: "互动", count: overview?.class_interactions.count ?? 0, to: "/interactions" },
    { label: "剧本", count: overview?.musical_scripts.count ?? 0, to: "/musical-scripts" },
    { label: "唱段", count: overview?.song_adaptations.count ?? 0, to: "/song-adaptations" },
    { label: "融合", count: overview?.musical_fusion_plans.count ?? 0, to: "/musical-fusion-plans" },
    { label: "训练", count: overview?.role_training_plans.count ?? 0, to: "/role-training-plans" },
    { label: "复盘", count: overview?.rehearsal_reviews.count ?? 0, to: "/rehearsal-reviews" },
    { label: "示范", count: overview?.movement_guides.count ?? 0, to: "/movement-guides" },
    { label: "练习", count: overview?.practice_submissions.count ?? 0, to: "/practice-submissions" },
  ];
  const totalAssets = overviewItems.reduce((total, item) => total + item.count, 0);

  return (
    <main className="page-frame">
      <section className="home-hero">
        <div className="home-hero-main">
          <div className="hero-copy">
            <p className="eyebrow">教学闭环 / 创编闭环</p>
            <h1>把备课、排练与复盘收进一个清楚的工作台</h1>
            <p className="intro">从课前教案到课堂互动、示范材料、课后练习和歌舞剧创编，按老师的实际工作顺序集中管理。</p>
            <div className="hero-actions">
              <Button asChild><Link to="/lesson-plans/generate">新建教案</Link></Button>
              <Button asChild variant="secondary"><Link to="/lesson-plans">查看已保存</Link></Button>
              <Button asChild variant="secondary"><Link to="/musical-scripts/generate">新建剧本</Link></Button>
            </div>
          </div>

          <div className="hero-workbench" aria-label="最近工作">
            <div className="hero-workbench-header">
              <div><p className="section-kicker">最近工作</p><h2>继续推进</h2></div>
              <Button asChild variant="secondary" size="sm"><Link to="/musical-scripts">剧本库</Link></Button>
            </div>
            <div className="hero-workbench-grid">
              {workbenchItems.map((item) => (
                <Link className="hero-workbench-card" key={item.label} to={item.to}>
                  <span><small>{item.label}</small><strong>{item.title}</strong></span>
                  <em>{item.action}</em>
                </Link>
              ))}
            </div>
          </div>
        </div>

        <aside className="hero-overview" aria-label="工作台概览">
          <div className="hero-overview-panel">
            <div className="hero-overview-heading"><p>工作台概览</p><strong>{totalAssets} 份资产</strong><span>系统连接与生成资产集中看这一处。</span></div>
            <div className="hero-overview-status">
              <div><span>API</span><strong>{health?.status === "ok" ? "运行中" : "等待连接"}</strong></div>
              <div><span>LLM</span><strong>{configuredModelProviders}</strong></div>
            </div>
            <ol className="hero-overview-list">
              {overviewItems.map((item, index) => (
                <li key={item.label}><Link to={item.to}><span>{String(index + 1).padStart(2, "0")}</span><strong>{item.label}</strong><em>{item.count} 份</em></Link></li>
              ))}
            </ol>
          </div>
        </aside>
      </section>

      <section className="module-grid" aria-label="模块导航">
        <ModuleTile title="课前教案生成" status="已接入" description="填写课程条件，选择大模型生成结构化教案，支持编辑、保存和导出。" to="/lesson-plans/generate" />
        <ModuleTile title="课堂互动" status="已接入" description="生成课堂互动规则、逐步脚本、口令、学生动作和安全提醒。" to="/interactions/generate" />
        <ModuleTile title="教案资料库" status="已接入" description="查看原教案和变体版本，继续编辑并导出。" to="/lesson-plans" />
        <ModuleTile title="歌舞剧创编" status="已接入" description="生成分幕剧情、人物设定、台词和表演段落。" to="/musical-scripts/generate" />
        <ModuleTile title="唱段适配" status="已接入" description="生成演唱分配、改词建议和间奏留白。" to="/song-adaptations" />
        <ModuleTile title="歌舞融合" status="已接入" description="生成唱、跳、队形、衔接及排练结构建议。" to="/musical-fusion-plans" />
        <ModuleTile title="分角色训练" status="已接入" description="生成主角、配角、旁白、群演和领舞训练任务。" to="/role-training-plans" />
        <ModuleTile title="排练 / 演出复盘" status="已接入" description="整理排练问题、原因、改进计划和教学反思。" to="/rehearsal-reviews" />
        <ModuleTile title="示范材料" status="已接入" description="管理动作描述、步骤拆解、关键提示和示范材料。" to="/movement-guides" />
        <ModuleTile title="课后练习" status="已接入" description="记录学生练习视频、基础观察报告和老师反馈。" to="/practice-submissions" />
        {futureModules.map((moduleName) => (
          <ModuleTile key={moduleName} title={moduleName} status="即将接入" description="后续沿用当前任务、编辑、保存和导出模式扩展。" />
        ))}
      </section>
    </main>
  );
}

/** 首页允许概览或健康检查独立失败，但 StrictMode 主动中止的请求不应回写兜底状态。 */
function resetUnlessAborted(caughtError: unknown, reset: () => void) {
  if (!isAbortError(caughtError)) {
    reset();
  }
}
