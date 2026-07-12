import { useId, useState } from "react";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { EditableSection, EmptyReadable, ModelInfoLine, ReadableList, ReadableText } from "../ui/EditableSection";
import { Field, FieldGroup, FieldLabel, FieldLegend, FieldSet } from "../ui/field";
import { TextareaField, TextField } from "../ui/FormFields";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { ToggleGroup, ToggleGroupItem } from "../ui/toggle-group";
import type {
  NextRehearsalPlan,
  RehearsalIssue,
  RehearsalReviewContent,
  RehearsalRoleSuggestion,
  ReusableReviewTemplate,
} from "../../types";

export function RehearsalReviewEditor({
  content,
  modelInfo,
  onChange,
}: {
  content: RehearsalReviewContent;
  modelInfo: Record<string, unknown> | null;
  onChange: (content: RehearsalReviewContent) => void;
}) {
  const [editingKey, setEditingKey] = useState<string | null>(null);

  function updateValue<Key extends keyof RehearsalReviewContent>(key: Key, value: RehearsalReviewContent[Key]) {
    onChange({ ...content, [key]: value });
  }

  function toggle(key: string) {
    setEditingKey((current) => (current === key ? null : key));
  }

  return (
    <div className="lesson-editor readable-document rehearsal-review-document">
      <EditableSection
        eyebrow="复盘概况"
        title="本次排练 / 演出总结"
        summary="先确认报告标题、现场概况和已经完成较好的部分。"
        isEditing={editingKey === "overview"}
        onToggleEdit={() => toggle("overview")}
        editContent={
          <FieldGroup>
            <TextField label="报告标题" value={content.title} onChange={(value) => updateValue("title", value)} />
            <TextareaField label="排练 / 演出概况" rows={6} value={content.overview} onChange={(value) => updateValue("overview", value)} />
            <EditableTextList label="完成较好的部分" values={content.highlights} onChange={(values) => updateValue("highlights", values)} />
          </FieldGroup>
        }
      >
        <div className="readable-title-block">
          <h2>{content.title}</h2>
          <ReadableText value={content.overview} />
          <h5>完成较好的部分</h5>
          <ReadableList values={content.highlights} />
        </div>
      </EditableSection>

      <EditableSection
        eyebrow="问题闭环"
        title="问题、原因与改进措施"
        summary={`${content.issues.length} 项问题，均需给出下一次可观察的检查点。`}
        isEditing={editingKey === "issues"}
        onToggleEdit={() => toggle("issues")}
        editContent={<IssueEditor values={content.issues} onChange={(values) => updateValue("issues", values)} />}
      >
        <IssueReadView values={content.issues} />
      </EditableSection>

      <EditableSection
        eyebrow="角色任务"
        title="分角色改进建议"
        summary={`${content.role_suggestions.length} 个角色或角色组，便于下一次直接分配任务。`}
        isEditing={editingKey === "roles"}
        onToggleEdit={() => toggle("roles")}
        editContent={<RoleSuggestionEditor values={content.role_suggestions} onChange={(values) => updateValue("role_suggestions", values)} />}
      >
        <RoleSuggestionReadView values={content.role_suggestions} />
      </EditableSection>

      <EditableSection
        eyebrow="专项建议"
        title="唱、跳、表演与调度"
        summary="把专业判断留给老师，报告只整理可执行的辅助建议。"
        isEditing={editingKey === "special_advice"}
        onToggleEdit={() => toggle("special_advice")}
        editContent={
          <FieldGroup>
            <TextareaField label="唱段与节奏建议" rows={4} value={content.singing_and_rhythm_advice} onChange={(value) => updateValue("singing_and_rhythm_advice", value)} />
            <TextareaField label="舞蹈与队形建议" rows={4} value={content.dance_and_formation_advice} onChange={(value) => updateValue("dance_and_formation_advice", value)} />
            <TextareaField label="表演与舞台调度建议" rows={4} value={content.performance_and_blocking_advice} onChange={(value) => updateValue("performance_and_blocking_advice", value)} />
          </FieldGroup>
        }
      >
        <div className="readable-three-column rehearsal-advice-grid">
          <div>
            <h5>唱段与节奏</h5>
            <ReadableText value={content.singing_and_rhythm_advice} />
          </div>
          <div>
            <h5>舞蹈与队形</h5>
            <ReadableText value={content.dance_and_formation_advice} />
          </div>
          <div>
            <h5>表演与调度</h5>
            <ReadableText value={content.performance_and_blocking_advice} />
          </div>
        </div>
      </EditableSection>

      <EditableSection
        eyebrow="下一次"
        title="下一次排练计划"
        summary="把复盘结论转成可以按顺序执行和检查的任务。"
        isEditing={editingKey === "next_plan"}
        onToggleEdit={() => toggle("next_plan")}
        editContent={<NextPlanEditor value={content.next_rehearsal_plan} onChange={(value) => updateValue("next_rehearsal_plan", value)} />}
      >
        <NextPlanReadView value={content.next_rehearsal_plan} />
      </EditableSection>

      <EditableSection
        eyebrow="沉淀"
        title="教学反思与可复用模板"
        summary="模板只保留观察框架，不复制本次事实、日期和视频。"
        isEditing={editingKey === "reflection_template"}
        onToggleEdit={() => toggle("reflection_template")}
        editContent={
          <FieldGroup>
            <TextareaField label="教学反思" rows={6} value={content.teaching_reflection} onChange={(value) => updateValue("teaching_reflection", value)} />
            <TemplateEditor value={content.reusable_template} onChange={(value) => updateValue("reusable_template", value)} />
          </FieldGroup>
        }
      >
        <ReadableText value={content.teaching_reflection} />
        <div className="review-template-card">
          <p className="readable-record-kicker">复盘模板</p>
          <h4>{content.reusable_template.template_title}</h4>
          <div className="readable-two-column">
            <div>
              <h5>建议复盘重点</h5>
              <ReadableList values={content.reusable_template.review_focus} />
            </div>
            <div>
              <h5>现场观察提示</h5>
              <ReadableList values={content.reusable_template.observation_prompts} />
            </div>
          </div>
          <h5>结束检查清单</h5>
          <ReadableList values={content.reusable_template.closing_checklist} />
        </div>
      </EditableSection>

      <EditableSection
        eyebrow="人工确认"
        title="编导复核与能力边界"
        summary="任何建议都需要老师或编导结合现场情况确认。"
        isEditing={editingKey === "review_boundary"}
        onToggleEdit={() => toggle("review_boundary")}
        editContent={
          <FieldGroup>
            <EditableTextList label="编导复核提醒" values={content.reviewer_notes} onChange={(values) => updateValue("reviewer_notes", values)} />
            <TextareaField label="能力边界" rows={4} value={content.boundary_note} onChange={(value) => updateValue("boundary_note", value)} />
          </FieldGroup>
        }
      >
        <ReadableList values={content.reviewer_notes} />
        <div className="review-boundary-note">
          <strong>能力边界</strong>
          <ReadableText value={content.boundary_note} />
        </div>
      </EditableSection>

      {modelInfo ? <ModelInfoLine modelInfo={modelInfo} /> : null}
    </div>
  );
}

function IssueReadView({ values }: { values: RehearsalIssue[] }) {
  if (values.length === 0) {
    return <EmptyReadable text="暂无结构化问题。" />;
  }
  const priorityLabel = { high: "高优先级", medium: "中优先级", low: "低优先级" };
  return (
    <div className="readable-timeline">
      {values.map((issue, index) => (
        <article className="readable-record" key={`review-issue-${index}`}>
          <div className="readable-record-header">
            <div>
              <p className="readable-record-kicker">问题 {index + 1}</p>
              <h4>{issue.category}</h4>
            </div>
            <Badge variant={issue.priority === "high" ? "default" : "outline"}>{priorityLabel[issue.priority]}</Badge>
          </div>
          <ReadableText value={issue.observation} />
          <div className="readable-two-column">
            <div>
              <h5>可能原因</h5>
              <ReadableText value={issue.possible_cause} />
            </div>
            <div>
              <h5>改进措施</h5>
              <ReadableText value={issue.improvement_action} />
            </div>
          </div>
          <div className="review-checkpoint">
            <strong>下次检查</strong>
            <span>{issue.next_check}</span>
          </div>
        </article>
      ))}
    </div>
  );
}

function IssueEditor({ values, onChange }: { values: RehearsalIssue[]; onChange: (values: RehearsalIssue[]) => void }) {
  function update(index: number, value: RehearsalIssue) {
    onChange(values.map((item, itemIndex) => (itemIndex === index ? value : item)));
  }

  return (
    <FieldSet className="edit-section">
      <FieldLegend>问题、原因与改进措施</FieldLegend>
      {values.map((issue, index) => (
        <FieldGroup className="nested-editor" key={`review-issue-edit-${index}`}>
          <div className="field-grid">
            <Field>
              <FieldLabel htmlFor={`review-issue-category-${index}`}>问题类别</FieldLabel>
              <Input id={`review-issue-category-${index}`} value={issue.category} onChange={(event) => update(index, { ...issue, category: event.target.value })} />
            </Field>
            <Field>
              <FieldLabel id={`review-issue-priority-${index}`}>优先级</FieldLabel>
              <ToggleGroup
                aria-labelledby={`review-issue-priority-${index}`}
                type="single"
                value={issue.priority}
                variant="outline"
                onValueChange={(value) => {
                  if (value) {
                    update(index, { ...issue, priority: value as RehearsalIssue["priority"] });
                  }
                }}
              >
                <ToggleGroupItem value="high">高</ToggleGroupItem>
                <ToggleGroupItem value="medium">中</ToggleGroupItem>
                <ToggleGroupItem value="low">低</ToggleGroupItem>
              </ToggleGroup>
            </Field>
          </div>
          <TextareaField label="观察现象" rows={3} value={issue.observation} onChange={(value) => update(index, { ...issue, observation: value })} />
          <TextareaField label="可能原因" rows={3} value={issue.possible_cause} onChange={(value) => update(index, { ...issue, possible_cause: value })} />
          <TextareaField label="改进措施" rows={3} value={issue.improvement_action} onChange={(value) => update(index, { ...issue, improvement_action: value })} />
          <TextareaField label="下次检查点" rows={2} value={issue.next_check} onChange={(value) => update(index, { ...issue, next_check: value })} />
          <Button type="button" variant="destructive" disabled={values.length === 1} onClick={() => onChange(values.filter((_, itemIndex) => itemIndex !== index))}>
            删除此问题
          </Button>
        </FieldGroup>
      ))}
      <Button
        type="button"
        variant="secondary"
        onClick={() =>
          onChange([
            ...values,
            { category: "其他", observation: "", possible_cause: "", improvement_action: "", priority: "medium", next_check: "" },
          ])
        }
      >
        添加问题
      </Button>
    </FieldSet>
  );
}

function RoleSuggestionReadView({ values }: { values: RehearsalRoleSuggestion[] }) {
  if (values.length === 0) {
    return <EmptyReadable text="暂无分角色建议。" />;
  }
  return (
    <div className="readable-record-grid">
      {values.map((item, index) => (
        <article className="readable-record" key={`role-review-${index}`}>
          <p className="readable-record-kicker">角色任务</p>
          <h4>{item.role_name}</h4>
          <ReadableText value={item.observation} />
          <h5>改进建议</h5>
          <ReadableText value={item.suggestion} />
          <h5>下次任务</h5>
          <ReadableList values={item.next_tasks} />
        </article>
      ))}
    </div>
  );
}

function RoleSuggestionEditor({ values, onChange }: { values: RehearsalRoleSuggestion[]; onChange: (values: RehearsalRoleSuggestion[]) => void }) {
  function update(index: number, value: RehearsalRoleSuggestion) {
    onChange(values.map((item, itemIndex) => (itemIndex === index ? value : item)));
  }
  return (
    <FieldSet className="edit-section">
      <FieldLegend>分角色改进建议</FieldLegend>
      {values.map((item, index) => (
        <FieldGroup className="nested-editor" key={`role-review-edit-${index}`}>
          <TextField label="角色或角色组" value={item.role_name} onChange={(value) => update(index, { ...item, role_name: value })} />
          <TextareaField label="观察" rows={3} value={item.observation} onChange={(value) => update(index, { ...item, observation: value })} />
          <TextareaField label="建议" rows={3} value={item.suggestion} onChange={(value) => update(index, { ...item, suggestion: value })} />
          <EditableTextList label="下次任务" values={item.next_tasks} onChange={(nextTasks) => update(index, { ...item, next_tasks: nextTasks })} />
          <Button type="button" variant="destructive" disabled={values.length === 1} onClick={() => onChange(values.filter((_, itemIndex) => itemIndex !== index))}>
            删除此角色建议
          </Button>
        </FieldGroup>
      ))}
      <Button
        type="button"
        variant="secondary"
        onClick={() => onChange([...values, { role_name: "新角色组", observation: "", suggestion: "", next_tasks: [""] }])}
      >
        添加角色建议
      </Button>
    </FieldSet>
  );
}

function NextPlanReadView({ value }: { value: NextRehearsalPlan }) {
  return (
    <div className="next-rehearsal-plan">
      <div className="next-plan-goal">
        <p className="readable-record-kicker">下一次总目标</p>
        <h4>{value.goal}</h4>
      </div>
      <div className="readable-three-column">
        <div>
          <h5>重点任务</h5>
          <ReadableList values={value.focus_items} />
        </div>
        <div>
          <h5>执行步骤</h5>
          <ReadableList values={value.action_steps} />
        </div>
        <div>
          <h5>老师检查点</h5>
          <ReadableList values={value.teacher_checkpoints} />
        </div>
      </div>
    </div>
  );
}

function NextPlanEditor({ value, onChange }: { value: NextRehearsalPlan; onChange: (value: NextRehearsalPlan) => void }) {
  return (
    <FieldGroup>
      <TextareaField label="下一次总目标" rows={3} value={value.goal} onChange={(goal) => onChange({ ...value, goal })} />
      <EditableTextList label="重点任务" values={value.focus_items} onChange={(focusItems) => onChange({ ...value, focus_items: focusItems })} />
      <EditableTextList label="执行步骤" values={value.action_steps} onChange={(actionSteps) => onChange({ ...value, action_steps: actionSteps })} />
      <EditableTextList label="老师检查点" values={value.teacher_checkpoints} onChange={(teacherCheckpoints) => onChange({ ...value, teacher_checkpoints: teacherCheckpoints })} />
    </FieldGroup>
  );
}

function TemplateEditor({ value, onChange }: { value: ReusableReviewTemplate; onChange: (value: ReusableReviewTemplate) => void }) {
  return (
    <FieldSet className="edit-section compact-section">
      <FieldLegend>报告内可复用模板</FieldLegend>
      <TextField label="模板标题" value={value.template_title} onChange={(templateTitle) => onChange({ ...value, template_title: templateTitle })} />
      <EditableTextList label="建议复盘重点" values={value.review_focus} onChange={(reviewFocus) => onChange({ ...value, review_focus: reviewFocus })} />
      <EditableTextList label="现场观察提示" values={value.observation_prompts} onChange={(prompts) => onChange({ ...value, observation_prompts: prompts })} />
      <EditableTextList label="结束检查清单" values={value.closing_checklist} onChange={(checklist) => onChange({ ...value, closing_checklist: checklist })} />
    </FieldSet>
  );
}

function EditableTextList({ label, values, onChange }: { label: string; values: string[]; onChange: (values: string[]) => void }) {
  const listId = useId();
  return (
    <FieldSet className="edit-section compact-section">
      <FieldLegend variant="label">{label}</FieldLegend>
      <FieldGroup>
        {values.map((value, index) => (
          <Field orientation="horizontal" key={`${label}-${index}`}>
            <FieldLabel className="sr-only" htmlFor={`${listId}-${index}`}>
              {label} {index + 1}
            </FieldLabel>
            <Textarea
              id={`${listId}-${index}`}
              rows={2}
              value={value}
              onChange={(event) => onChange(values.map((item, itemIndex) => (itemIndex === index ? event.target.value : item)))}
            />
            <Button type="button" variant="secondary" disabled={values.length === 1} onClick={() => onChange(values.filter((_, itemIndex) => itemIndex !== index))}>
              删除
            </Button>
          </Field>
        ))}
      </FieldGroup>
      <Button type="button" variant="secondary" onClick={() => onChange([...values, ""])}>
        添加一项
      </Button>
    </FieldSet>
  );
}
