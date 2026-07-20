import { useEffect, useState } from "react";
import { Link } from "react-router";
import { LibraryRecordCard } from "../components/library/LibraryRecordCard";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { deleteRehearsalReview, fetchRehearsalReviews, isAbortError } from "../lib/api";
import { downloadRehearsalReviewMarkdown } from "../lib/download";
import type { RehearsalReviewSummary } from "../types";


export function RehearsalReviewListPage() {
  const [reviews, setReviews] = useState<RehearsalReviewSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchRehearsalReviews(controller.signal)
      .then((rows) => {
        setReviews(rows);
        setNotice("");
      })
      .catch((caughtError) => {
        if (isAbortError(caughtError)) {
          return;
        }
        setNotice(caughtError instanceof Error ? caughtError.message : "读取排练复盘报告失败。");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  async function handleDownload(review: RehearsalReviewSummary) {
    try {
      setNotice("");
      await downloadRehearsalReviewMarkdown(review.id, review.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  async function handleDelete(review: RehearsalReviewSummary) {
    if (!window.confirm(`确认删除“${review.title}”吗？关联的 MinIO 视频附件也会删除。`)) {
      return;
    }
    try {
      setDeletingId(review.id);
      setNotice("");
      await deleteRehearsalReview(review.id);
      setReviews((current) => current.filter((item) => item.id !== review.id));
      setNotice(`已删除复盘报告：${review.title}`);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "删除复盘报告失败。");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="M08 复盘资料库"
        title="排练 / 演出复盘"
        description="集中查看老师确认后的问题、改进计划、教学反思和可复用观察模板。"
        action={
          <Button asChild>
            <Link to="/rehearsal-reviews/generate">新建复盘报告</Link>
          </Button>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取复盘报告" text="请稍候，系统正在加载已保存内容。" /> : null}
      {!loading && reviews.length === 0 ? (
        <EmptyState title="还没有复盘报告" text="完成一次排练或演出后，填写人工观察记录并生成第一份 M08 报告。" />
      ) : null}

      <section className="library-card-grid" aria-label="排练复盘报告列表">
        {reviews.map((review) => (
          <LibraryRecordCard
            key={review.id}
            kind="review"
            title={review.title}
            badges={
              <>
                <Badge variant="secondary">{review.event_type === "performance" ? "演出复盘" : "排练复盘"}</Badge>
                <Badge variant="outline">{review.status}</Badge>
                {review.has_video_attachment ? <Badge variant="outline">MinIO 视频</Badge> : null}
              </>
            }
            summaryLabel="现场日期"
            summary={review.event_date}
            updatedAt={review.updated_at}
            provider={review.provider}
            model={review.model}
            reasoningLevel={review.reasoning_level}
            viewTo={`/rehearsal-reviews/${review.id}`}
            viewLabel="查看报告"
            deleting={deletingId === review.id}
            onDownload={() => void handleDownload(review)}
            onDelete={() => void handleDelete(review)}
          />
        ))}
      </section>
    </main>
  );
}
