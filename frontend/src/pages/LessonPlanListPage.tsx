import { type ReactNode, useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  Bot,
  Clock,
  Download,
  FileText,
  GitBranch,
  Plus,
  Sparkles,
  Trash2,
} from "lucide-react";
import { Link } from "react-router";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "../components/ui/empty";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { downloadMarkdown } from "../lib/download";
import { deleteLessonPlan, fetchLessonPlans, isAbortError } from "../lib/api";
import { apiDateTimeToEpoch, formatDateTime } from "../lib/format";
import { lessonPlanVariantLabel } from "../lib/lessonPlanVariants";
import { cn } from "../lib/utils";
import type { LessonPlanSummary } from "../types";

type LessonPlanGroup = {
  courseId: string;
  title: string;
  root: LessonPlanSummary | null;
  variants: LessonPlanSummary[];
  updatedAt: string;
};

export function LessonPlanListPage() {
  const [lessonPlans, setLessonPlans] = useState<LessonPlanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchLessonPlans(controller.signal)
      .then((data) => {
        setLessonPlans(data);
        setNotice("");
      })
      .catch((caughtError) => {
        if (isAbortError(caughtError)) {
          return;
        }
        setNotice(caughtError instanceof Error ? caughtError.message : "读取教案列表失败。");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  const lessonPlanGroups = useMemo(() => groupLessonPlans(lessonPlans), [lessonPlans]);

  async function handleDownload(lessonPlan: LessonPlanSummary) {
    try {
      setNotice("");
      await downloadMarkdown(lessonPlan.id, lessonPlan.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  async function handleDelete(lessonPlan: LessonPlanSummary) {
    const relatedVariantCount = lessonPlans.filter((item) => item.source_lesson_plan_id === lessonPlan.id).length;
    const relationshipNote = relatedVariantCount > 0
      ? `\n\n该原教案下有 ${relatedVariantCount} 个变体。删除原教案后，变体仍会保留，并继续使用生成时快照对照。`
      : "";
    const confirmed = window.confirm(`确认删除“${lessonPlan.title}”吗？删除后无法在列表中恢复。${relationshipNote}`);
    if (!confirmed) return;

    try {
      setDeletingId(lessonPlan.id);
      setNotice("");
      await deleteLessonPlan(lessonPlan.id);

      // 删除原教案时后端会把变体来源外键置空；同步本地关系，避免页面刷新前仍显示可访问链接。
      setLessonPlans((currentLessonPlans) =>
        currentLessonPlans
          .filter((currentLessonPlan) => currentLessonPlan.id !== lessonPlan.id)
          .map((currentLessonPlan) => currentLessonPlan.source_lesson_plan_id === lessonPlan.id
            ? { ...currentLessonPlan, source_lesson_plan_id: null }
            : currentLessonPlan),
      );
      setNotice(relatedVariantCount > 0
        ? `已删除原教案“${lessonPlan.title}”，${relatedVariantCount} 个变体及其快照仍保留。`
        : `已删除教案：${lessonPlan.title}`);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "删除教案失败。");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="教学设计 · 版本资料库"
        title="教案版本库"
        description="以原教案为基线，集中管理面向不同年龄、基础和演出场景的适配版本。"
        action={
          <Button asChild>
            <Link to="/lesson-plans/generate">
              <Plus data-icon="inline-start" aria-hidden="true" />
              新建原教案
            </Link>
          </Button>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取教案" text="请稍候，系统正在从后端加载已保存内容和版本关系。" /> : null}

      {!loading && lessonPlanGroups.length === 0 ? (
        <EmptyState title="还没有保存的教案" text="先生成一份原教案，之后可继续创建低龄、基础、进阶或演出版。" />
      ) : null}

      <section className="lesson-plan-group-list" aria-label="按课程分组的教案列表">
        {lessonPlanGroups.map((group) => (
          <Card className="lesson-plan-group" key={group.courseId}>
            <CardHeader className="lesson-plan-group-header">
              <div className="lesson-plan-group-heading">
                <div className="readable-chip-row">
                  <Badge variant="outline">课程档案</Badge>
                  <Badge variant="secondary">
                    {group.root ? group.variants.length + 1 : group.variants.length} 个版本
                  </Badge>
                  {!group.root ? <Badge variant="destructive">基线已删除</Badge> : null}
                </div>
                <CardTitle>{group.title}</CardTitle>
                <CardDescription className="lesson-plan-group-meta">
                  <span>
                    <Clock aria-hidden="true" />
                    最近更新 {formatDateTime(group.updatedAt)}
                  </span>
                  <span>课程编号 {group.courseId.slice(0, 8).toUpperCase()}</span>
                </CardDescription>
              </div>
              <CardAction className="lesson-plan-group-count" aria-label={`${group.variants.length} 个适配版本`}>
                <strong>{group.variants.length.toString().padStart(2, "0")}</strong>
                <span>适配版本</span>
              </CardAction>
            </CardHeader>

            <CardContent className="lesson-plan-group-content">
              <section className="lesson-version-lane is-baseline" aria-label="基线教案">
                <VersionLaneHeading
                  icon={<FileText aria-hidden="true" />}
                  title="基线教案"
                  description="课程目标与流程的确认版本"
                />
                {group.root ? (
                  <LessonVersionCard
                    lessonPlan={group.root}
                    deleting={deletingId === group.root.id}
                    onDownload={handleDownload}
                    onDelete={handleDelete}
                  />
                ) : (
                  <Empty className="lesson-version-missing">
                    <EmptyHeader>
                      <EmptyMedia variant="icon"><FileText aria-hidden="true" /></EmptyMedia>
                      <EmptyTitle>原教案已删除</EmptyTitle>
                      <EmptyDescription>右侧变体仍保留生成时快照，可继续查看与导出。</EmptyDescription>
                    </EmptyHeader>
                  </Empty>
                )}
              </section>

              <section className="lesson-version-lane is-variants" aria-label="适配版本">
                <VersionLaneHeading
                  icon={<GitBranch aria-hidden="true" />}
                  title="适配版本"
                  description="同一课程背景下的场景化教案"
                  action={group.root && group.variants.length > 0 ? (
                    <Button asChild variant="outline" size="sm">
                      <Link to={`/lesson-plans/${group.root.id}/variants/generate`}>
                        <Plus data-icon="inline-start" aria-hidden="true" />
                        新建变体
                      </Link>
                    </Button>
                  ) : null}
                />
                {group.variants.length > 0 ? (
                  <div className="lesson-version-card-grid">
                    {group.variants.map((variant) => (
                      <LessonVersionCard
                        lessonPlan={variant}
                        deleting={deletingId === variant.id}
                        onDownload={handleDownload}
                        onDelete={handleDelete}
                        key={variant.id}
                      />
                    ))}
                  </div>
                ) : group.root ? (
                  <Empty className="lesson-variant-empty">
                    <EmptyHeader>
                      <EmptyMedia variant="icon"><Sparkles aria-hidden="true" /></EmptyMedia>
                      <EmptyTitle>让这份教案适应更多课堂</EmptyTitle>
                      <EmptyDescription>
                        从确认稿衍生低龄、基础、进阶或演出版，原教案内容不会被覆盖。
                      </EmptyDescription>
                    </EmptyHeader>
                    <EmptyContent>
                      <Button asChild size="sm">
                        <Link to={`/lesson-plans/${group.root.id}/variants/generate`}>
                          <Plus data-icon="inline-start" aria-hidden="true" />
                          创建第一个变体
                        </Link>
                      </Button>
                    </EmptyContent>
                  </Empty>
                ) : (
                  <Empty className="lesson-version-missing">
                    <EmptyHeader>
                      <EmptyMedia variant="icon"><GitBranch aria-hidden="true" /></EmptyMedia>
                      <EmptyTitle>暂无可用版本</EmptyTitle>
                      <EmptyDescription>当前课程档案中没有可继续衍生的基线教案。</EmptyDescription>
                    </EmptyHeader>
                  </Empty>
                )}
              </section>
            </CardContent>
          </Card>
        ))}
      </section>
    </main>
  );
}

function VersionLaneHeading({
  icon,
  title,
  description,
  action,
}: {
  icon: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <header className="lesson-version-lane-heading">
      <span className="lesson-version-lane-icon">{icon}</span>
      <span className="lesson-version-lane-copy">
        <strong>{title}</strong>
        <small>{description}</small>
      </span>
      {action ? <span className="lesson-version-lane-action">{action}</span> : null}
    </header>
  );
}

function LessonVersionCard({
  lessonPlan,
  deleting,
  onDownload,
  onDelete,
}: {
  lessonPlan: LessonPlanSummary;
  deleting: boolean;
  onDownload: (lessonPlan: LessonPlanSummary) => Promise<void>;
  onDelete: (lessonPlan: LessonPlanSummary) => Promise<void>;
}) {
  const isVariant = Boolean(lessonPlan.variant_type);
  const modelLabel = lessonPlan.model
    ? `${providerLabel(lessonPlan.provider)} · ${lessonPlan.model}`
    : null;

  return (
    <Card className={cn("lesson-version-card", isVariant ? "is-variant" : "is-root")}>
      <CardHeader>
        <div className="readable-chip-row">
          <Badge variant={isVariant ? "secondary" : "default"}>
            {isVariant ? lessonPlanVariantLabel(lessonPlan.variant_type) : "原教案"}
          </Badge>
          <Badge variant={statusBadgeVariant(lessonPlan.status)}>{statusLabel(lessonPlan.status)}</Badge>
        </div>
        <CardTitle>{lessonPlan.title}</CardTitle>
        <CardDescription className="lesson-version-meta">
          <span>
            <Clock aria-hidden="true" />
            {formatDateTime(lessonPlan.updated_at)}
          </span>
          {modelLabel ? (
            <span title={modelLabel}>
              <Bot aria-hidden="true" />
              {modelLabel}
              {lessonPlan.reasoning_level ? ` · ${reasoningLevelLabel(lessonPlan.reasoning_level)}` : ""}
            </span>
          ) : null}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p className="lesson-version-relation">
          <GitBranch aria-hidden="true" />
          <span>
            {isVariant ? (
              lessonPlan.source_lesson_plan_id
                ? "由同课程的原教案衍生，可随时返回基线对照。"
                : "原教案已删除，详情页仍保留生成时的完整快照。"
            ) : (
              "课程基线版本，可继续生成适合不同对象和场景的一级变体。"
            )}
          </span>
        </p>
      </CardContent>
      <CardFooter className="library-card-actions">
        <div className="lesson-version-primary-actions">
          <Button asChild size="sm">
            <Link to={`/lesson-plans/${lessonPlan.id}`}>
              打开教案
              <ArrowRight data-icon="inline-end" aria-hidden="true" />
            </Link>
          </Button>
          <Button variant="outline" size="sm" type="button" onClick={() => void onDownload(lessonPlan)}>
            <Download data-icon="inline-start" aria-hidden="true" />
            Markdown
          </Button>
        </div>
        <Button
          variant="destructive"
          size="icon"
          type="button"
          disabled={deleting}
          aria-label={deleting ? `正在删除${lessonPlan.title}` : `删除${lessonPlan.title}`}
          title={deleting ? "正在删除" : "删除教案"}
          onClick={() => void onDelete(lessonPlan)}
        >
          <Trash2 data-icon="inline-start" aria-hidden="true" />
        </Button>
      </CardFooter>
    </Card>
  );
}

/** 把后端状态转换成老师一眼可懂的中文标签，未知状态仍保留原值便于排查。 */
function statusLabel(status: string) {
  const labels: Record<string, string> = {
    draft: "草稿",
    generating: "生成中",
    generated: "已生成",
    reviewed: "已确认",
    failed: "生成失败",
  };
  return labels[status.toLowerCase()] ?? status;
}

function statusBadgeVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
  const normalizedStatus = status.toLowerCase();
  if (normalizedStatus === "failed") return "destructive";
  if (normalizedStatus === "reviewed") return "default";
  if (normalizedStatus === "generated") return "secondary";
  return "outline";
}

function providerLabel(provider: string | null) {
  if (provider === "deepseek") return "DeepSeek";
  if (provider === "qwen") return "通义千问";
  return provider ?? "模型";
}

function reasoningLevelLabel(reasoningLevel: string) {
  const labels: Record<string, string> = {
    off: "快速",
    standard: "标准",
    enhanced: "增强",
  };
  return labels[reasoningLevel] ?? reasoningLevel;
}

function groupLessonPlans(lessonPlans: LessonPlanSummary[]): LessonPlanGroup[] {
  const groups = new Map<string, LessonPlanSummary[]>();
  for (const lessonPlan of lessonPlans) {
    const current = groups.get(lessonPlan.course_id) ?? [];
    current.push(lessonPlan);
    groups.set(lessonPlan.course_id, current);
  }

  return Array.from(groups.entries())
    .map(([courseId, items]) => {
      const root = items.find((item) => !item.variant_type) ?? null;
      const variants = items
        .filter((item) => Boolean(item.variant_type))
        .sort((left, right) => apiDateTimeToEpoch(right.updated_at) - apiDateTimeToEpoch(left.updated_at));
      const updatedAt = items.reduce(
        (latest, item) => apiDateTimeToEpoch(item.updated_at) > apiDateTimeToEpoch(latest) ? item.updated_at : latest,
        items[0].updated_at,
      );
      return {
        courseId,
        root,
        variants,
        updatedAt,
        title: root?.title ?? variants[0]?.source_title_snapshot ?? variants[0]?.title ?? "未命名课程",
      };
    })
    .sort((left, right) => apiDateTimeToEpoch(right.updatedAt) - apiDateTimeToEpoch(left.updatedAt));
}
