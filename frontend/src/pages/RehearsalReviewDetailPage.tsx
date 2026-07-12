import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { RehearsalReviewEditor } from "../components/rehearsal-reviews/RehearsalReviewEditor";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import {
  deleteRehearsalReview,
  fetchRehearsalReview,
  rehearsalReviewVideoUrl,
  updateRehearsalReview,
} from "../lib/api";
import { downloadRehearsalReviewMarkdown } from "../lib/download";
import type { RehearsalReviewContent, RehearsalReviewResponse } from "../types";


export function RehearsalReviewDetailPage() {
  const { rehearsalReviewId } = useParams();
  const navigate = useNavigate();
  const [review, setReview] = useState<RehearsalReviewResponse | null>(null);
  const [editedContent, setEditedContent] = useState<RehearsalReviewContent | null>(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!rehearsalReviewId) {
      return;
    }
    void fetchRehearsalReview(rehearsalReviewId)
      .then((detail) => {
        setReview(detail);
        setEditedContent(detail.edited_content ?? detail.content);
        setNotice("");
      })
      .catch((caughtError) => setNotice(caughtError instanceof Error ? caughtError.message : "读取排练复盘报告失败。"))
      .finally(() => setLoading(false));
  }, [rehearsalReviewId]);

  async function saveReview() {
    if (!review || !editedContent) {
      return;
    }
    setSaving(true);
    setNotice("");
    try {
      const updated = await updateRehearsalReview(review.id, editedContent);
      setReview(updated);
      setEditedContent(updated.edited_content ?? updated.content);
      setNotice("老师 / 编导确认稿已保存。\n");
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "保存复盘报告失败。");
    } finally {
      setSaving(false);
    }
  }

  async function handleDownload() {
    if (!review) {
      return;
    }
    try {
      setNotice("");
      await downloadRehearsalReviewMarkdown(review.id, review.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  async function handleDelete() {
    if (!review || !window.confirm(`确认删除“${review.title}”吗？MinIO 视频附件也会一起删除。`)) {
      return;
    }
    setDeleting(true);
    setNotice("");
    try {
      await deleteRehearsalReview(review.id);
      navigate("/rehearsal-reviews");
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "删除复盘报告失败。");
      setDeleting(false);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="M08 复盘报告详情"
        title={review?.title ?? "读取排练复盘报告"}
        description="人工复核问题、原因和下一次任务；视频只用于现场回看，不参与 AI 分析。"
        action={
          <div className="button-row">
            <Button variant="secondary" type="button" onClick={() => navigate("/rehearsal-reviews")}>返回列表</Button>
            {review ? <Button variant="secondary" type="button" onClick={() => navigate(`/musical-scripts/${review.script_id}`)}>查看剧本</Button> : null}
            {review ? <Button variant="secondary" type="button" onClick={() => navigate(`/rehearsal-reviews/generate?template_from=${review.id}`)}>以此模板新建</Button> : null}
            {review ? <Button variant="secondary" type="button" onClick={() => void handleDownload()}>导出 Markdown</Button> : null}
            <Button type="button" disabled={!editedContent || saving} onClick={() => void saveReview()}>{saving ? "保存中……" : "保存全部修改"}</Button>
            {review ? <Button variant="destructive" type="button" disabled={deleting} onClick={() => void handleDelete()}>{deleting ? "删除中……" : "删除报告"}</Button> : null}
          </div>
        }
      />

      {review ? (
        <div className="readable-chip-row">
          <Badge variant="secondary">{review.event_type === "performance" ? "演出复盘" : "排练复盘"}</Badge>
          <Badge variant="outline">{review.event_date}</Badge>
          <Badge variant="outline">{review.status}</Badge>
          {review.has_video_attachment ? <Badge variant="outline">MinIO 视频附件</Badge> : null}
        </div>
      ) : null}
      <div className="review-boundary-banner" role="note">
        <strong>视频未进入 AI</strong>
        <span>报告内容来自老师填写的观察记录。视频播放器只用于人工回看，不能把报告理解为自动视频分析结果。</span>
      </div>
      {notice ? <p className="notice">{notice.trim()}</p> : null}
      {loading ? <EmptyState title="正在读取复盘报告" text="请稍候，系统正在加载报告正文和附件信息。" /> : null}

      {review ? (
        <Card className="surface-panel review-source-card">
          <CardHeader>
            <CardTitle>本次复盘来源</CardTitle>
            <CardDescription>报告已保存上游确认稿快照，M04/M05 后续删除不会改变当前结论。</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="review-source-grid">
              <div><span>本次内容</span><strong>{review.rehearsal_content}</strong></div>
              <div><span>下一次目标</span><strong>{review.next_goal}</strong></div>
              <div><span>复盘重点</span><strong>{review.review_focus.join("、")}</strong></div>
              <div><span>上游资料</span><strong>{review.fusion_plan_id ? "已引用 M04" : "未引用 M04"} · {review.role_training_plan_id ? "已引用 M05" : "未引用 M05"}</strong></div>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {review?.has_video_attachment ? (
        <Card className="surface-panel review-video-card">
          <CardHeader>
            <CardTitle>现场视频附件</CardTitle>
            <CardDescription>{review.video_original_file_name} · {formatFileSize(review.video_size_bytes)} · 通过后端从 MinIO 私有桶代理播放</CardDescription>
          </CardHeader>
          <CardContent>
            <video className="review-video-player" controls preload="metadata" src={rehearsalReviewVideoUrl(review.id)} />
            {review.video_notes ? <p className="review-video-note">老师备注：{review.video_notes}</p> : null}
          </CardContent>
        </Card>
      ) : null}

      {editedContent ? (
        <Card className="surface-panel review-editor-card">
          <CardContent>
            <RehearsalReviewEditor content={editedContent} onChange={setEditedContent} modelInfo={review?.raw_model_info ?? null} />
          </CardContent>
        </Card>
      ) : !loading ? (
        <EmptyState title="复盘报告内容不可用" text="这份报告可能尚未生成成功，暂时无法编辑或导出。" />
      ) : null}
    </main>
  );
}


function formatFileSize(sizeBytes: number | null) {
  if (!sizeBytes) {
    return "大小未知";
  }
  return sizeBytes < 1024 * 1024
    ? `${Math.max(1, Math.round(sizeBytes / 1024))} KB`
    : `${(sizeBytes / 1024 / 1024).toFixed(1)} MB`;
}
