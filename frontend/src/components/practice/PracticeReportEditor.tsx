import { Button } from "../ui/button";
import { TextareaField, TextField } from "../ui/FormFields";
import type { PracticeIssuePoint, PracticeReportContent } from "../../types";

export function PracticeReportEditor({
  content,
  modelInfo,
  onChange,
}: {
  content: PracticeReportContent;
  modelInfo: Record<string, unknown> | null;
  onChange: (content: PracticeReportContent) => void;
}) {
  function updateValue<Key extends keyof PracticeReportContent>(key: Key, value: PracticeReportContent[Key]) {
    onChange({ ...content, [key]: value });
  }

  return (
    <div className="lesson-editor">
      <section className="edit-section">
        <h3>报告基础信息</h3>
        <TextField label="报告标题" value={content.title} onChange={(value) => updateValue("title", value)} />
        <TextareaField label="总体观察" value={content.summary} rows={4} onChange={(value) => updateValue("summary", value)} />
      </section>

      <EditableTextList title="视频基本信息" values={content.video_basic_info} onChange={(values) => updateValue("video_basic_info", values)} />
      <EditableTextList
        title="拍摄质量反馈"
        values={content.shooting_quality_feedback}
        onChange={(values) => updateValue("shooting_quality_feedback", values)}
      />
      <EditableTextList
        title="节奏与完整度观察"
        values={content.rhythm_and_completion_observations}
        onChange={(values) => updateValue("rhythm_and_completion_observations", values)}
      />
      <EditableTextList
        title="姿态和动作稳定性观察"
        values={content.posture_and_stability_observations}
        onChange={(values) => updateValue("posture_and_stability_observations", values)}
      />
      <IssuePointList values={content.structured_issue_points} onChange={(values) => updateValue("structured_issue_points", values)} />
      <EditableTextList title="练习建议" values={content.ai_suggestions} onChange={(values) => updateValue("ai_suggestions", values)} />
      <EditableTextList
        title="老师复核重点"
        values={content.teacher_review_points}
        onChange={(values) => updateValue("teacher_review_points", values)}
      />
      <EditableTextList
        title="下一次练习任务"
        values={content.next_practice_tasks}
        onChange={(values) => updateValue("next_practice_tasks", values)}
      />

      <TextareaField
        label="老师最终点评"
        value={content.teacher_final_comment}
        required={false}
        rows={4}
        onChange={(value) => updateValue("teacher_final_comment", value)}
      />
      <TextareaField
        label="能力边界说明"
        value={content.boundary_note}
        required={false}
        rows={3}
        onChange={(value) => updateValue("boundary_note", value)}
      />
      {modelInfo ? <AnalysisInfo modelInfo={modelInfo} /> : null}
    </div>
  );
}

function EditableTextList({ title, values, onChange }: { title: string; values: string[]; onChange: (values: string[]) => void }) {
  return (
    <section className="edit-section compact-section">
      <div className="section-heading">
        <div>
          <p className="section-kicker">练习报告</p>
          <h3>{title}</h3>
        </div>
        <Button variant="secondary" type="button" onClick={() => onChange([...values, ""])}>
          添加
        </Button>
      </div>
      {values.map((value, index) => (
        <div className="inline-edit-row" key={`${title}-${index}`}>
          <textarea
            value={value}
            rows={2}
            onChange={(event) => onChange(values.map((item, itemIndex) => (itemIndex === index ? event.target.value : item)))}
          />
          <Button variant="destructive" type="button" onClick={() => onChange(values.filter((_, itemIndex) => itemIndex !== index))}>
            删除
          </Button>
        </div>
      ))}
    </section>
  );
}

function IssuePointList({ values, onChange }: { values: PracticeIssuePoint[]; onChange: (values: PracticeIssuePoint[]) => void }) {
  return (
    <section className="edit-section">
      <div className="section-heading">
        <div>
          <p className="section-kicker">结构化观察</p>
          <h3>观察点</h3>
        </div>
        <Button variant="secondary" type="button" onClick={addIssue}>
          添加观察点
        </Button>
      </div>
      {values.map((issue, index) => (
        <div className="nested-editor" key={`practice-issue-${index}`}>
          <input value={issue.category} onChange={(event) => updateIssue(index, { ...issue, category: event.target.value })} aria-label="观察类别" />
          <textarea
            value={issue.description}
            rows={3}
            onChange={(event) => updateIssue(index, { ...issue, description: event.target.value })}
            aria-label="观察描述"
          />
          <textarea
            value={issue.suggestion}
            rows={2}
            onChange={(event) => updateIssue(index, { ...issue, suggestion: event.target.value })}
            aria-label="改进建议"
          />
          <Button variant="destructive" type="button" onClick={() => removeIssue(index)}>
            删除观察点
          </Button>
        </div>
      ))}
    </section>
  );

  function addIssue() {
    onChange([...values, { category: "新观察点", description: "", suggestion: "" }]);
  }

  function updateIssue(index: number, nextValue: PracticeIssuePoint) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }

  function removeIssue(index: number) {
    onChange(values.filter((_, valueIndex) => valueIndex !== index));
  }
}

function AnalysisInfo({ modelInfo }: { modelInfo: Record<string, unknown> }) {
  return (
    <p className="model-info">
      分析链路：{String(modelInfo.pipeline ?? "manual_first_stage")} / 姿态估计 {String(modelInfo.pose_estimation ?? "not_connected")} / DTW{" "}
      {String(modelInfo.dtw_alignment ?? "not_connected")} / LLM {String(modelInfo.llm_report ?? "not_connected")}
    </p>
  );
}
