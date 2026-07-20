import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { Button } from "../components/ui/button";
import { TextareaField, TextField } from "../components/ui/FormFields";
import { Field, FieldLabel } from "../components/ui/field";
import { Input } from "../components/ui/input";
import { PageTitle } from "../components/ui/PageTitle";
import { createPracticeSubmission, fetchMovementGuide, fetchMovementGuides, isAbortError, uploadPracticeVideo } from "../lib/api";
import { initialPracticeSubmissionForm } from "../lib/lessonPlanDefaults";
import type { MovementGuideResponse, MovementGuideSummary, PracticeSubmissionForm } from "../types";

export function PracticeSubmissionCreatePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<PracticeSubmissionForm>(initialPracticeSubmissionForm);
  const [focusInput, setFocusInput] = useState(initialPracticeSubmissionForm.evaluation_focus.join("、"));
  const [movementGuides, setMovementGuides] = useState<MovementGuideSummary[]>([]);
  const [selectedGuideId, setSelectedGuideId] = useState("");
  const [selectedVideoFile, setSelectedVideoFile] = useState<File | null>(null);
  const [notice, setNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    void fetchMovementGuides(controller.signal)
      .then(setMovementGuides)
      .catch((caughtError) => {
        if (isAbortError(caughtError)) {
          return;
        }
        setMovementGuides([]);
      });
    return () => controller.abort();
  }, []);

  async function submitPractice(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) {
      return;
    }

    setSubmitting(true);
    setNotice("");
    try {
      const created = await createPracticeSubmission({
        ...form,
        evaluation_focus: splitFocus(focusInput),
      });
      navigate(`/practice-submissions/${created.id}`);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "创建练习提交失败。");
    } finally {
      setSubmitting(false);
    }
  }

  async function uploadSelectedVideo() {
    if (!selectedVideoFile || uploading) {
      return;
    }

    setUploading(true);
    setNotice("");
    try {
      const uploaded = await uploadPracticeVideo(selectedVideoFile);
      updateForm("video_url", uploaded.url);
      updateForm("video_file_name", uploaded.original_file_name);
      setNotice(`视频已上传并回填地址：${uploaded.original_file_name}`);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "上传练习视频失败。");
    } finally {
      setUploading(false);
    }
  }

  async function selectReferenceGuide(guideId: string) {
    setSelectedGuideId(guideId);
    if (!guideId) {
      return;
    }

    setNotice("");
    try {
      const guide = await fetchMovementGuide(guideId);
      const referenceUrl = extractReferenceVideoUrl(guide);
      updateForm("reference_action_name", guide.action_name);
      if (referenceUrl) {
        updateForm("reference_video_url", referenceUrl);
        setNotice(`已从示范材料带入标准动作：${guide.action_name}`);
      } else {
        setNotice(`已带入标准动作名称：${guide.action_name}。这份示范材料暂未记录参考视频地址。`);
      }
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "读取示范材料失败。");
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="课后练习"
        title="新建练习提交"
        description="录入学生练习视频地址、任务要求和老师关注重点，先跑通提交与复核流程。"
        action={
          <Button variant="secondary" type="button" onClick={() => navigate("/practice-submissions")}>
            练习提交列表
          </Button>
        }
      />

      <section className="lesson-layout">
        <form className="surface-panel input-panel" onSubmit={submitPractice}>
          <div className="section-heading">
            <div>
              <p className="section-kicker">T06</p>
              <h2>练习视频记录</h2>
            </div>
            <Button variant="secondary" type="button" onClick={fillExample}>
              填入示例
            </Button>
          </div>

          <div className="field-grid">
            <TextField label="课程或片段" value={form.course_title} required={false} onChange={(value) => updateForm("course_title", value)} />
            <TextField label="练习任务" value={form.task_title} onChange={(value) => updateForm("task_title", value)} />
          </div>
          <TextareaField label="任务要求" value={form.task_description} required={false} onChange={(value) => updateForm("task_description", value)} />

          <div className="field-grid">
            <TextField label="学生姓名" value={form.student_name} onChange={(value) => updateForm("student_name", value)} />
            <TextField label="小组 / 角色" value={form.student_group} required={false} onChange={(value) => updateForm("student_group", value)} />
          </div>

          <section className="upload-box" aria-label="上传练习视频">
            <Field className="field">
              <FieldLabel>本地练习视频</FieldLabel>
              <Input
                accept="video/*,.mp4,.mov,.m4v,.webm"
                type="file"
                onChange={(event) => setSelectedVideoFile(event.target.files?.[0] ?? null)}
              />
            </Field>
            <Button variant="secondary" type="button" disabled={!selectedVideoFile || uploading} onClick={() => void uploadSelectedVideo()}>
              {uploading ? "上传中..." : "上传并回填地址"}
            </Button>
            <p>建议上传 15-60 秒短视频。第一阶段仅保存文件和地址，视频分析后续由 Worker 接入。</p>
          </section>

          <TextField label="练习视频地址" value={form.video_url} onChange={(value) => updateForm("video_url", value)} />
          <div className="field-grid">
            <TextField label="视频文件名" value={form.video_file_name} required={false} onChange={(value) => updateForm("video_file_name", value)} />
            <Field className="field">
              <FieldLabel>视频时长（秒）</FieldLabel>
              <Input
                min={0}
                max={600}
                type="number"
                value={form.video_duration_seconds ?? ""}
                onChange={(event) => updateForm("video_duration_seconds", event.target.value ? Number(event.target.value) : null)}
              />
            </Field>
          </div>
          <TextareaField label="学生补充说明" value={form.video_notes} required={false} onChange={(value) => updateForm("video_notes", value)} />

          <Field className="field">
            <FieldLabel>从示范材料选择标准动作</FieldLabel>
            <select value={selectedGuideId} onChange={(event) => void selectReferenceGuide(event.target.value)}>
              <option value="">手动填写标准动作</option>
              {movementGuides.map((guide) => (
                <option key={guide.id} value={guide.id}>
                  {guide.action_name} / {guide.title}
                </option>
              ))}
            </select>
          </Field>

          <div className="field-grid">
            <TextField
              label="标准动作名称"
              value={form.reference_action_name}
              required={false}
              onChange={(value) => updateForm("reference_action_name", value)}
            />
            <TextField
              label="标准动作视频地址"
              value={form.reference_video_url}
              required={false}
              onChange={(value) => updateForm("reference_video_url", value)}
            />
          </div>
          <TextareaField label="评价重点" value={focusInput} required={false} onChange={setFocusInput} />

          {notice ? <p className="notice">{notice}</p> : null}
          <Button className="w-full" type="submit" disabled={submitting}>
            {submitting ? "创建中..." : "创建练习提交"}
          </Button>
        </form>

        <aside className="surface-panel result-panel">
          <div className="section-heading">
            <div>
              <p className="section-kicker">当前范围</p>
              <h2>第一阶段先跑通报告复核</h2>
            </div>
          </div>
          <div className="empty-state">
            <h3>视频分析由后续 Worker 接入</h3>
            <p>当前保存视频地址、标准动作线索和评价重点；基础观察报告不会输出动作正确率或专业判分。</p>
          </div>
        </aside>
      </section>
    </main>
  );

  function updateForm<Key extends keyof PracticeSubmissionForm>(key: Key, value: PracticeSubmissionForm[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function fillExample() {
    setForm(initialPracticeSubmissionForm);
    setFocusInput(initialPracticeSubmissionForm.evaluation_focus.join("、"));
    setSelectedGuideId("");
  }
}

function splitFocus(value: string) {
  const items = value.split(/[、，,\n]/).map((item) => item.trim());
  return items.filter(Boolean);
}

function extractReferenceVideoUrl(guide: MovementGuideResponse) {
  if (guide.reference_video_url) {
    return guide.reference_video_url;
  }

  const content = guide.edited_content ?? guide.content;
  const referenceAsset = content?.media_assets.find(
    (asset) =>
      Boolean(asset.url) &&
      ["reference_video", "confirmed_skeleton", "digital_human_video", "courseware_video"].includes(asset.asset_type),
  );
  return referenceAsset?.url ?? "";
}
