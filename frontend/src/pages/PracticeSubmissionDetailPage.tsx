import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { PracticeReportEditor } from "../components/practice/PracticeReportEditor";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { analyzePracticeSubmission, fetchPracticeSubmission, updatePracticeReport } from "../lib/api";
import { downloadPracticeReportMarkdown } from "../lib/download";
import { formatDateTime } from "../lib/format";
import type { PracticeReportContent, PracticeSubmissionDetail } from "../types";

export function PracticeSubmissionDetailPage() {
  const { submissionId } = useParams();
  const navigate = useNavigate();
  const [submission, setSubmission] = useState<PracticeSubmissionDetail | null>(null);
  const [editedContent, setEditedContent] = useState<PracticeReportContent | null>(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!submissionId) {
      return;
    }
    void loadSubmission(submissionId);
  }, [submissionId]);

  async function loadSubmission(id: string) {
    setLoading(true);
    try {
      const detail = await fetchPracticeSubmission(id);
      setSubmission(detail);
      setEditedContent(detail.report?.edited_content ?? detail.report?.content ?? null);
      setNotice("");
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "读取练习提交失败。");
    } finally {
      setLoading(false);
    }
  }

  async function handleAnalyze() {
    if (!submission) {
      return;
    }
    setAnalyzing(true);
    setNotice("");
    try {
      const result = await analyzePracticeSubmission(submission.id);
      await loadSubmission(submission.id);
      setNotice(result.message);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "生成基础观察报告失败。");
    } finally {
      setAnalyzing(false);
    }
  }

  async function saveReview() {
    if (!submission?.report || !editedContent) {
      return;
    }
    setSaving(true);
    setNotice("");
    try {
      const updatedReport = await updatePracticeReport(submission.report.id, editedContent, editedContent.teacher_final_comment);
      setSubmission((current) => (current ? { ...current, status: "reviewed", report: updatedReport } : current));
      setEditedContent(updatedReport.edited_content ?? updatedReport.content);
      setNotice("老师复核稿已保存。");
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "保存老师复核稿失败。");
    } finally {
      setSaving(false);
    }
  }

  async function handleDownloadMarkdown() {
    if (!submission?.report) {
      return;
    }
    try {
      setNotice("");
      await downloadPracticeReportMarkdown(submission.report.id, submission.report.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  const report = submission?.report ?? null;

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="练习详情"
        title={submission?.task_title ?? "读取练习提交"}
        description="查看学生提交的视频线索，生成基础观察稿，并保存老师复核后的最终反馈。"
        action={
          <div className="button-row">
            <Button variant="secondary" type="button" onClick={() => navigate("/practice-submissions")}>
              返回列表
            </Button>
            {submission ? (
              <Button variant="secondary" type="button" disabled={analyzing} onClick={() => void handleAnalyze()}>
                {analyzing ? "生成中..." : report ? "重新生成观察稿" : "生成基础观察"}
              </Button>
            ) : null}
            {report ? (
              <Button variant="secondary" type="button" onClick={() => void handleDownloadMarkdown()}>
                导出 Markdown
              </Button>
            ) : null}
            <Button type="button" disabled={!editedContent || saving} onClick={() => void saveReview()}>
              {saving ? "保存中..." : "保存老师复核"}
            </Button>
          </div>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取练习提交" text="请稍候，系统正在读取练习详情。" /> : null}

      {submission ? (
        <section className="surface-panel">
          <div className="section-heading">
            <div>
              <p className="section-kicker">提交信息</p>
              <h2>
                {submission.student_name}
                {submission.student_group ? ` · ${submission.student_group}` : ""}
              </h2>
            </div>
            <Badge variant="secondary">{report?.status ?? submission.status}</Badge>
          </div>
          <div className="health-grid">
            <InfoItem label="课程 / 片段" value={submission.course_title || "未填写"} />
            <InfoItem label="视频文件" value={submission.video_file_name || "未填写"} />
            <InfoItem label="视频时长" value={submission.video_duration_seconds == null ? "未填写" : `${submission.video_duration_seconds} 秒`} />
            <InfoItem label="标准动作" value={submission.reference_action_name || "未填写"} />
            <InfoItem label="评价重点" value={submission.evaluation_focus.join("、") || "未填写"} />
            <InfoItem label="更新时间" value={formatDateTime(submission.updated_at)} />
          </div>
          <p className="model-info">
            视频地址：
            <a href={submission.video_url} rel="noreferrer" target="_blank">
              {submission.video_url}
            </a>
          </p>
          {isProbablyVideoUrl(submission.video_url) ? <video className="practice-video-preview" controls src={submission.video_url} /> : null}
          {submission.task_description ? <p className="model-info">任务要求：{submission.task_description}</p> : null}
          {submission.video_notes ? <p className="model-info">学生说明：{submission.video_notes}</p> : null}
        </section>
      ) : null}

      {editedContent && report ? (
        <section className="surface-panel">
          <PracticeReportEditor content={editedContent} onChange={setEditedContent} modelInfo={report.raw_analysis_info} />
        </section>
      ) : !loading && submission ? (
        <EmptyState title="还没有练习观察报告" text="点击“生成基础观察”，系统会根据提交信息生成一份可复核报告草稿。" />
      ) : null}
    </main>
  );
}

function isProbablyVideoUrl(value: string) {
  return /\.(mp4|mov|m4v|webm|avi|mkv)(\?.*)?$/i.test(value);
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <Card asChild className="dependency-card">
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </Card>
  );
}
