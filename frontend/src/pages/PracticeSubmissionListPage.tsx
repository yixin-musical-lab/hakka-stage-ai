import { useEffect, useState } from "react";
import { Link } from "react-router";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { deletePracticeSubmission, fetchPracticeSubmissions, isAbortError } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { PracticeSubmissionSummary } from "../types";

export function PracticeSubmissionListPage() {
  const [submissions, setSubmissions] = useState<PracticeSubmissionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchPracticeSubmissions(controller.signal)
      .then((data) => {
        setSubmissions(data);
        setNotice("");
      })
      .catch((caughtError) => {
        if (isAbortError(caughtError)) {
          return;
        }
        setNotice(caughtError instanceof Error ? caughtError.message : "读取练习提交列表失败。");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  async function handleDelete(submission: PracticeSubmissionSummary) {
    const confirmed = window.confirm(`确认删除“${submission.student_name} / ${submission.task_title}”吗？删除后关联报告也会一起删除。`);
    if (!confirmed) {
      return;
    }

    try {
      setDeletingId(submission.id);
      setNotice("");
      await deletePracticeSubmission(submission.id);
      setSubmissions((current) => current.filter((item) => item.id !== submission.id));
      setNotice(`已删除练习提交：${submission.student_name} / ${submission.task_title}`);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "删除练习提交失败。");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="课后练习"
        title="练习提交与复核"
        description="集中查看学生练习视频记录、基础观察报告和老师复核状态。"
        action={
          <Button asChild>
            <Link to="/practice-submissions/new">新建练习提交</Link>
          </Button>
        }
      />

      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取练习提交" text="请稍候，系统正在从后端加载已保存内容。" /> : null}
      {!loading && submissions.length === 0 ? (
        <EmptyState title="还没有练习提交" text="先创建一条练习视频记录，再生成基础观察报告和老师点评。" />
      ) : null}

      <section className="lesson-list" aria-label="课后练习提交列表">
        {submissions.map((submission) => (
          <Card asChild className="lesson-list-item" key={submission.id}>
            <article>
              <div>
                <Badge variant="secondary">{submission.report_status ?? submission.status}</Badge>
                <h2>{submission.task_title}</h2>
                <p>
                  学生：{submission.student_name}
                  {submission.student_group ? ` · ${submission.student_group}` : ""}
                  {submission.course_title ? ` · ${submission.course_title}` : ""}
                </p>
                <p>
                  报告：{submission.report_status ?? "未生成"}
                  {submission.analysis_mode ? ` · ${submission.analysis_mode}` : ""}
                </p>
                <p>更新时间：{formatDateTime(submission.updated_at)}</p>
              </div>
              <div className="button-row">
                <Button asChild variant="secondary">
                  <Link to={`/practice-submissions/${submission.id}`}>查看</Link>
                </Button>
                <Button
                  variant="destructive"
                  type="button"
                  disabled={deletingId === submission.id}
                  onClick={() => void handleDelete(submission)}
                >
                  {deletingId === submission.id ? "删除中" : "删除"}
                </Button>
              </div>
            </article>
          </Card>
        ))}
      </section>
    </main>
  );
}
