import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { LessonEditor } from "../components/lesson-plans/LessonEditor";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { fetchLessonPlan, fetchLessonPlanVariants, updateLessonPlan } from "../lib/api";
import { downloadMarkdown } from "../lib/download";
import { formatDateTime } from "../lib/format";
import { lessonPlanVariantLabel } from "../lib/lessonPlanVariants";
import type { LessonPlanContent, LessonPlanResponse, LessonPlanSummary } from "../types";

export function LessonPlanDetailPage() {
  const { lessonPlanId } = useParams();
  const navigate = useNavigate();
  const [lessonPlan, setLessonPlan] = useState<LessonPlanResponse | null>(null);
  const [editedContent, setEditedContent] = useState<LessonPlanContent | null>(null);
  const [variants, setVariants] = useState<LessonPlanSummary[]>([]);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!lessonPlanId) return;

    let active = true;
    setLoading(true);
    setVariants([]);
    void fetchLessonPlan(lessonPlanId)
      .then(async (detail) => {
        if (!active) return;
        setLessonPlan(detail);
        setEditedContent(detail.edited_content ?? detail.content);
        setNotice("");

        // 原教案详情才查询直属变体；变体不能继续派生，因此无需加载多级版本树。
        if (!detail.variant_info) {
          const relatedVariants = await fetchLessonPlanVariants(detail.id);
          if (active) setVariants(relatedVariants);
        }
      })
      .catch((caughtError) => {
        if (active) setNotice(caughtError instanceof Error ? caughtError.message : "读取教案失败。");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [lessonPlanId]);

  async function persistLessonPlan(successNotice: string) {
    if (!lessonPlan || !editedContent) return null;

    setSaving(true);
    setNotice("");
    try {
      const updated = await updateLessonPlan(lessonPlan.id, editedContent);
      setLessonPlan(updated);
      setEditedContent(updated.edited_content ?? updated.content);
      setNotice(successNotice);
      return updated;
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "保存失败。");
      return null;
    } finally {
      setSaving(false);
    }
  }

  async function openVariantGenerator() {
    if (!lessonPlan || lessonPlan.variant_info) return;

    // 变体必须基于老师当前看到的确认稿；先保存再跳转，避免以旧内容创建版本。
    const updated = await persistLessonPlan("老师确认稿已保存，正在进入版本生成页。");
    if (updated) navigate(`/lesson-plans/${updated.id}/variants/generate`);
  }

  async function handleDownloadMarkdown() {
    if (!lessonPlan) return;

    try {
      setNotice("");
      await downloadMarkdown(lessonPlan.id, lessonPlan.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  const variantInfo = lessonPlan?.variant_info ?? null;
  const pageDescription = variantInfo
    ? "当前展示这一份可独立编辑、导出和用于课堂互动的变体教案。"
    : "维护老师确认稿，并从同一课程基线创建适配不同教学场景的一级版本。";

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow={variantInfo ? `T02 · ${lessonPlanVariantLabel(variantInfo.variant_type)}` : "教案详情 · 原教案"}
        title={lessonPlan?.title ?? "读取教案"}
        description={pageDescription}
        action={
          <div className="button-row">
            <Button variant="secondary" type="button" onClick={() => navigate("/lesson-plans")}>
              返回列表
            </Button>
            {lessonPlan && !variantInfo ? (
              <Button variant="secondary" type="button" disabled={!editedContent || saving} onClick={() => void openVariantGenerator()}>
                生成变体版本
              </Button>
            ) : null}
            {lessonPlan ? (
              <Button variant="secondary" type="button" onClick={() => navigate(`/interactions/generate?lessonPlanId=${lessonPlan.id}`)}>
                生成课堂互动
              </Button>
            ) : null}
            {lessonPlan ? (
              <Button variant="secondary" type="button" onClick={() => void handleDownloadMarkdown()}>
                导出 Markdown
              </Button>
            ) : null}
            <Button type="button" disabled={!editedContent || saving} onClick={() => void persistLessonPlan("老师编辑稿已保存。")}>
              {saving ? "保存中..." : "保存全部修改"}
            </Button>
          </div>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取教案" text="请稍候，系统正在读取教案详情和版本关系。" /> : null}

      {!loading && lessonPlan && !variantInfo ? (
        <RootVersionOverview lessonPlan={lessonPlan} variants={variants} />
      ) : null}

      {!loading && lessonPlan && variantInfo && editedContent ? (
        <>
          <Card className="variant-provenance-card">
            <CardHeader>
              <div className="readable-chip-row">
                <Badge>{lessonPlanVariantLabel(variantInfo.variant_type)}</Badge>
                <Badge variant="secondary">{lessonPlan.status}</Badge>
                {variantInfo.source_lesson_plan_id ? <Badge variant="outline">原教案仍可访问</Badge> : <Badge variant="outline">原教案已删除 · 保留快照</Badge>}
              </div>
              {variantInfo.source_lesson_plan_id ? (
                <CardAction>
                  <Button asChild size="sm" variant="outline">
                    <Link to={`/lesson-plans/${variantInfo.source_lesson_plan_id}`}>打开原教案</Link>
                  </Button>
                </CardAction>
              ) : null}
              <CardTitle>版本说明</CardTitle>
              <CardDescription>
                生成基线：{variantInfo.source_title_snapshot} · 创建于 {formatDateTime(lessonPlan.created_at)}
              </CardDescription>
            </CardHeader>
            <CardContent className="variant-provenance-grid">
              <div>
                <span>适用对象</span>
                <p>{editedContent.applicable_audience || "尚未填写适用对象。"}</p>
              </div>
              <div>
                <span>老师补充方向</span>
                <p>{variantInfo.adjustment_direction || "未填写额外方向，按固定预设生成。"}</p>
              </div>
              <div>
                <span>主要调整</span>
                {editedContent.adjustment_summary.length > 0 ? (
                  <ul>
                    {editedContent.adjustment_summary.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                  </ul>
                ) : <p>尚未填写调整摘要。</p>}
              </div>
            </CardContent>
          </Card>

          {/* 变体详情只呈现当前版本正文，来源关系由上方说明卡片承载，避免阅读时被双栏对比打断。 */}
          <Card className="surface-panel lesson-detail-card variant-lesson-detail-card">
            <CardHeader>
              <div className="readable-chip-row">
                <Badge>{lessonPlanVariantLabel(variantInfo.variant_type)}</Badge>
                <Badge variant="outline">可独立编辑</Badge>
              </div>
              <CardTitle>{editedContent.title}</CardTitle>
              <CardDescription>当前保存、导出和生成课堂互动时，均使用这份变体教案的内容。</CardDescription>
            </CardHeader>
            <CardContent>
              <LessonEditor content={editedContent} onChange={setEditedContent} modelInfo={lessonPlan.raw_model_info} />
            </CardContent>
          </Card>
        </>
      ) : null}

      {!loading && lessonPlan && !variantInfo && editedContent ? (
        <Card className="surface-panel lesson-detail-card">
          <CardHeader>
            <div className="readable-chip-row">
              <Badge variant="secondary">原教案</Badge>
              <Badge variant="outline">{lessonPlan.status}</Badge>
            </div>
            <CardTitle>老师确认稿</CardTitle>
            <CardDescription>本页保存后的内容会作为下一次变体生成的冻结基线。</CardDescription>
          </CardHeader>
          <CardContent>
            <LessonEditor content={editedContent} onChange={setEditedContent} modelInfo={lessonPlan.raw_model_info} />
          </CardContent>
        </Card>
      ) : null}

      {!loading && (!lessonPlan || !editedContent) ? (
        <EmptyState title="教案内容不可用" text="这份教案可能尚未生成成功，暂时无法编辑或导出。" />
      ) : null}
    </main>
  );
}

function RootVersionOverview({
  lessonPlan,
  variants,
}: {
  lessonPlan: LessonPlanResponse;
  variants: LessonPlanSummary[];
}) {
  return (
    <Card className="lesson-version-overview">
      <CardHeader>
        <div className="readable-chip-row">
          <Badge variant="outline">1 份原教案</Badge>
          <Badge variant="secondary">{variants.length} 个变体</Badge>
        </div>
        <CardTitle>同课程版本组</CardTitle>
        <CardDescription>所有变体复用同一个课程 ID，但各自保存正文、老师编辑稿和生成快照。</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="version-strip" aria-label="当前教案的变体版本">
          <div className="version-strip-item is-current">
            <Badge>原教案</Badge>
            <strong>{lessonPlan.title}</strong>
            <span>当前基线 · {formatDateTime(lessonPlan.updated_at)}</span>
          </div>
          {variants.map((variant) => (
            <Link className="version-strip-item" to={`/lesson-plans/${variant.id}`} key={variant.id}>
              <Badge variant="secondary">{lessonPlanVariantLabel(variant.variant_type)}</Badge>
              <strong>{variant.title}</strong>
              <span>{variant.status} · {formatDateTime(variant.updated_at)}</span>
            </Link>
          ))}
          {variants.length === 0 ? <p className="version-strip-empty">尚未创建变体，可从页面右上角开始生成。</p> : null}
        </div>
      </CardContent>
    </Card>
  );
}
