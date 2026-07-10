import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { LessonEditor } from "../components/lesson-plans/LessonEditor";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { fetchLessonPlan, updateLessonPlan } from "../lib/api";
import { downloadMarkdown } from "../lib/download";
import type { LessonPlanContent, LessonPlanResponse } from "../types";

export function LessonPlanDetailPage() {
  const { lessonPlanId } = useParams();
  const navigate = useNavigate();
  const [lessonPlan, setLessonPlan] = useState<LessonPlanResponse | null>(null);
  const [editedContent, setEditedContent] = useState<LessonPlanContent | null>(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!lessonPlanId) {
      return;
    }

    void fetchLessonPlan(lessonPlanId)
      .then((detail) => {
        setLessonPlan(detail);
        setEditedContent(detail.edited_content ?? detail.content);
        setNotice("");
      })
      .catch((caughtError) => setNotice(caughtError instanceof Error ? caughtError.message : "读取教案失败。"))
      .finally(() => setLoading(false));
  }, [lessonPlanId]);

  async function saveLessonPlan() {
    if (!lessonPlan || !editedContent) {
      return;
    }

    setSaving(true);
    setNotice("");
    try {
      const updated = await updateLessonPlan(lessonPlan.id, editedContent);
      setLessonPlan(updated);
      setEditedContent(updated.edited_content ?? updated.content);
      setNotice("老师编辑稿已保存。");
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "保存失败。");
    } finally {
      setSaving(false);
    }
  }

  async function handleDownloadMarkdown() {
    if (!lessonPlan) {
      return;
    }

    try {
      setNotice("");
      await downloadMarkdown(lessonPlan.id, lessonPlan.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="教案详情"
        title={lessonPlan?.title ?? "读取教案"}
        description="查看、继续修改并导出老师确认稿。"
        action={
          <div className="button-row">
            <Button variant="secondary" type="button" onClick={() => navigate("/lesson-plans")}>
              返回列表
            </Button>
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
            <Button type="button" disabled={!editedContent || saving} onClick={() => void saveLessonPlan()}>
              {saving ? "保存中..." : "保存全部修改"}
            </Button>
          </div>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取教案" text="请稍候，系统正在读取教案详情。" /> : null}

      {editedContent ? (
        <Card asChild className="surface-panel">
          <section>
            <LessonEditor content={editedContent} onChange={setEditedContent} modelInfo={lessonPlan?.raw_model_info ?? null} />
          </section>
        </Card>
      ) : !loading ? (
        <EmptyState title="教案内容不可用" text="这份教案可能尚未生成成功，暂时无法编辑或导出。" />
      ) : null}
    </main>
  );
}
