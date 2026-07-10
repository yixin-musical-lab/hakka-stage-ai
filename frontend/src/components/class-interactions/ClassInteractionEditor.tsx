import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import type { ClassInteractionContent, TeacherScriptStep, TeachingPhase } from "../../types";
import { Button } from "../ui/button";
import { EditableSection, EmptyReadable, ModelInfoLine, ReadableList, ReadableText } from "../ui/EditableSection";
import { Field, FieldGroup, FieldLabel, FieldLegend, FieldSet } from "../ui/field";
import { NumberField, TextareaField, TextField } from "../ui/FormFields";
import { Input } from "../ui/input";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Textarea } from "../ui/textarea";

const teachingPhases: TeachingPhase[] = ["开场", "热身", "动作学习", "分组展示", "收束"];
type ClassInteractionListKey =
  | "game_rules"
  | "command_phrases"
  | "student_actions"
  | "encouragement_phrases"
  | "safety_notes"
  | "variations"
  | "teacher_check_notes";

export function ClassInteractionEditor({
  content,
  modelInfo,
  onChange,
}: {
  content: ClassInteractionContent;
  modelInfo: Record<string, unknown> | null;
  onChange: (content: ClassInteractionContent) => void;
}) {
  const [editingKey, setEditingKey] = useState<string | null>(null);

  function updateValue<Key extends keyof ClassInteractionContent>(key: Key, value: ClassInteractionContent[Key]) {
    onChange({ ...content, [key]: value });
  }

  function toggleEditing(key: string) {
    setEditingKey((current) => (current === key ? null : key));
  }

  return (
    <div className="lesson-editor readable-document">
      <EditableSection
        eyebrow="执行概况"
        title="互动目标与条件"
        summary="课堂阶段、目标、时长和现场条件集中确认。"
        isEditing={editingKey === "overview"}
        onToggleEdit={() => toggleEditing("overview")}
        editContent={
          <>
            <TextField label="方案标题" value={content.title} onChange={(value) => updateValue("title", value)} />
            <PhaseField value={content.teaching_phase} onChange={(value) => updateValue("teaching_phase", value)} />
            <NumberField label="互动时长（分钟）" value={content.duration_minutes} onChange={(value) => updateValue("duration_minutes", value)} />
            <TextareaField label="互动目标" value={content.interaction_goal} onChange={(value) => updateValue("interaction_goal", value)} />
            <TextareaField label="场地、材料与限制" value={content.space_materials} onChange={(value) => updateValue("space_materials", value)} />
          </>
        }
      >
        <div className="readable-title-block">
          <div className="readable-record-header">
            <h2>{content.title}</h2>
            <span className="readable-chip">{content.teaching_phase} · {content.duration_minutes} 分钟</span>
          </div>
          <ReadableText value={content.interaction_goal} emptyText="暂无互动目标。" />
          <div className="readable-callout">
            <strong>场地与材料</strong>
            <ReadableText value={content.space_materials} emptyText="暂无场地材料说明。" />
          </div>
        </div>
      </EditableSection>

      <TextListSection title="小游戏与互动规则" values={content.game_rules} editingKey="game_rules" eyebrow="互动规则" />

      <EditableSection
        eyebrow="现场流程"
        title="老师逐步执行脚本"
        summary={`${content.teacher_script.length} 个步骤，逐项包含老师动作、口令和学生回应。`}
        isEditing={editingKey === "teacher_script"}
        onToggleEdit={() => toggleEditing("teacher_script")}
        editContent={<TeacherScriptEditor values={content.teacher_script} onChange={(values) => updateValue("teacher_script", values)} />}
      >
        <TeacherScriptReadView values={content.teacher_script} />
      </EditableSection>

      <TextListSection title="老师口令" values={content.command_phrases} editingKey="command_phrases" eyebrow="现场话术" />
      <TextListSection title="学生动作与回应" values={content.student_actions} editingKey="student_actions" eyebrow="学生回应" />

      <EditableSection
        eyebrow="课堂组织"
        title="分组与站位"
        isEditing={editingKey === "grouping_method"}
        onToggleEdit={() => toggleEditing("grouping_method")}
        editContent={<TextareaField label="分组与组织方式" value={content.grouping_method} onChange={(value) => updateValue("grouping_method", value)} />}
      >
        <ReadableText value={content.grouping_method} emptyText="暂无分组说明。" />
      </EditableSection>

      <TextListSection title="鼓励用语" values={content.encouragement_phrases} editingKey="encouragement_phrases" eyebrow="课堂反馈" />
      <TextListSection title="安全提醒" values={content.safety_notes} editingKey="safety_notes" eyebrow="安全" />
      <TextListSection title="变式与备用方案" values={content.variations} editingKey="variations" eyebrow="现场调整" />
      <TextListSection title="老师开始前确认" values={content.teacher_check_notes} editingKey="teacher_check_notes" eyebrow="课前复核" />

      {modelInfo ? <ModelInfoLine modelInfo={modelInfo} /> : null}
    </div>
  );

  function TextListSection({
    title,
    values,
    editingKey: sectionKey,
    eyebrow,
  }: {
    title: string;
    values: string[];
    editingKey: ClassInteractionListKey;
    eyebrow: string;
  }) {
    return (
      <EditableSection
        eyebrow={eyebrow}
        title={title}
        isEditing={editingKey === sectionKey}
        onToggleEdit={() => toggleEditing(sectionKey)}
        editContent={<EditableList title={title} values={values} onChange={(nextValues) => updateValue(sectionKey, nextValues)} />}
      >
        <ReadableList values={values} />
      </EditableSection>
    );
  }
}

function PhaseField({ value, onChange }: { value: TeachingPhase; onChange: (value: TeachingPhase) => void }) {
  return (
    <Field className="field">
      <FieldLabel>课堂阶段</FieldLabel>
      <Select value={value} onValueChange={(nextValue) => onChange(nextValue as TeachingPhase)}>
        <SelectTrigger className="w-full bg-card">
          <SelectValue placeholder="选择课堂阶段" />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            {teachingPhases.map((phase) => <SelectItem key={phase} value={phase}>{phase}</SelectItem>)}
          </SelectGroup>
        </SelectContent>
      </Select>
    </Field>
  );
}

function TeacherScriptReadView({ values }: { values: TeacherScriptStep[] }) {
  if (values.length === 0) {
    return <EmptyReadable text="暂无执行步骤。" />;
  }
  return (
    <div className="readable-timeline">
      {values.map((step, index) => (
        <article className="readable-record" key={`teacher-step-read-${index}`}>
          <div className="readable-record-header">
            <div>
              <p className="readable-record-kicker">步骤 {step.step_no}</p>
              <h4>{step.name}</h4>
            </div>
            <span className="readable-chip">{step.duration_hint}</span>
          </div>
          <dl className="readable-definition-list">
            <div><dt>老师动作</dt><dd>{step.teacher_action}</dd></div>
            <div><dt>老师口令</dt><dd>{step.teacher_cue}</dd></div>
            <div><dt>学生动作</dt><dd>{step.student_action}</dd></div>
          </dl>
        </article>
      ))}
    </div>
  );
}

function TeacherScriptEditor({ values, onChange }: { values: TeacherScriptStep[]; onChange: (values: TeacherScriptStep[]) => void }) {
  function updateStep(index: number, nextValue: TeacherScriptStep) {
    onChange(values.map((value, valueIndex) => valueIndex === index ? nextValue : value));
  }

  function addStep() {
    onChange([...values, { step_no: values.length + 1, name: "新增步骤", duration_hint: "1 分钟", teacher_action: "", teacher_cue: "", student_action: "" }]);
  }

  function removeStep(index: number) {
    onChange(values.filter((_, valueIndex) => valueIndex !== index).map((step, valueIndex) => ({ ...step, step_no: valueIndex + 1 })));
  }

  return (
    <FieldSet className="edit-section">
      <FieldLegend>老师逐步执行脚本</FieldLegend>
      {values.map((step, index) => (
        <FieldGroup className="nested-editor" key={`teacher-step-${index}`}>
          <div className="field-grid">
            <Input type="number" min={1} value={step.step_no} onChange={(event) => updateStep(index, { ...step, step_no: Number(event.target.value) })} aria-label="步骤序号" />
            <Input value={step.name} onChange={(event) => updateStep(index, { ...step, name: event.target.value })} aria-label="步骤名称" />
            <Input value={step.duration_hint} onChange={(event) => updateStep(index, { ...step, duration_hint: event.target.value })} aria-label="建议耗时" />
          </div>
          <Textarea value={step.teacher_action} rows={2} onChange={(event) => updateStep(index, { ...step, teacher_action: event.target.value })} aria-label="老师动作" />
          <Textarea value={step.teacher_cue} rows={2} onChange={(event) => updateStep(index, { ...step, teacher_cue: event.target.value })} aria-label="老师口令" />
          <Textarea value={step.student_action} rows={2} onChange={(event) => updateStep(index, { ...step, student_action: event.target.value })} aria-label="学生动作" />
          <Button type="button" variant="outline" size="sm" disabled={values.length <= 1} onClick={() => removeStep(index)}>
            <Trash2 /> 删除步骤
          </Button>
        </FieldGroup>
      ))}
      <Button type="button" variant="secondary" size="sm" onClick={addStep}><Plus /> 添加步骤</Button>
    </FieldSet>
  );
}

function EditableList({ title, values, onChange }: { title: string; values: string[]; onChange: (values: string[]) => void }) {
  return (
    <FieldSet className="edit-section compact-section">
      <FieldLegend>{title}</FieldLegend>
      {values.map((value, index) => (
        <FieldGroup className="nested-editor" key={`${title}-${index}`}>
          <Textarea value={value} rows={2} onChange={(event) => onChange(values.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} />
          <Button type="button" variant="outline" size="sm" disabled={values.length <= 1} onClick={() => onChange(values.filter((_, itemIndex) => itemIndex !== index))}>
            <Trash2 /> 删除
          </Button>
        </FieldGroup>
      ))}
      <Button type="button" variant="secondary" size="sm" onClick={() => onChange([...values, ""])}><Plus /> 添加一项</Button>
    </FieldSet>
  );
}

export { PhaseField };
