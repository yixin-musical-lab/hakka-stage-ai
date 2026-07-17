import { useState } from "react";
import { TextareaField, TextField } from "../ui/FormFields";
import { EditableSection, ModelInfoLine, ReadableList, ReadableText } from "../ui/EditableSection";
import { FieldLegend, FieldSet } from "../ui/field";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import type { LessonActivity, LessonPlanContent, MovementStep } from "../../types";

export function LessonEditor({
  content,
  modelInfo,
  onChange,
  readOnly = false,
}: {
  content: LessonPlanContent;
  modelInfo: Record<string, unknown> | null;
  onChange: (content: LessonPlanContent) => void;
  readOnly?: boolean;
}) {
  const [editingKey, setEditingKey] = useState<string | null>(null);

  function toggleEditing(key: string) {
    setEditingKey((current) => (current === key ? null : key));
  }

  function updateValue<Key extends keyof LessonPlanContent>(key: Key, value: LessonPlanContent[Key]) {
    onChange({ ...content, [key]: value });
  }

  return (
    <div className="lesson-editor readable-document">
      <EditableSection
        eyebrow="基础信息"
        title="课程概况"
        summary="用于快速确认本节课主题、对象和整体教学方向。"
        isEditing={editingKey === "overview"}
        onToggleEdit={() => toggleEditing("overview")}
        canEdit={!readOnly}
        editContent={
          <>
            <TextField label="教案标题" value={content.title} onChange={(value) => updateValue("title", value)} />
            <TextareaField label="课程概况" value={content.course_overview} onChange={(value) => updateValue("course_overview", value)} />
          </>
        }
      >
        <div className="readable-title-block">
          <h2>{content.title}</h2>
          <ReadableText value={content.course_overview} emptyText="暂无课程概况。" />
        </div>
      </EditableSection>

      {content.applicable_audience !== null || content.adjustment_summary.length > 0 ? (
        <EditableSection
          eyebrow="T02 版本说明"
          title="适用对象与调整摘要"
          summary="说明这一版适合谁，以及相对生成时原稿做了哪些调整。"
          isEditing={editingKey === "variant_summary"}
          onToggleEdit={() => toggleEditing("variant_summary")}
          canEdit={!readOnly}
          editContent={
            <>
              <TextareaField
                label="适用班级或学员"
                value={content.applicable_audience ?? ""}
                onChange={(value) => updateValue("applicable_audience", value)}
              />
              <EditableList
                title="相对原版的调整说明"
                values={content.adjustment_summary}
                onChange={(values) => updateValue("adjustment_summary", values)}
              />
            </>
          }
        >
          <div className="variant-summary-content">
            <div>
              <p className="readable-record-kicker">适用对象</p>
              <ReadableText value={content.applicable_audience ?? ""} emptyText="暂无适用对象说明。" />
            </div>
            <div>
              <p className="readable-record-kicker">主要调整</p>
              <ReadableList values={content.adjustment_summary} emptyText="暂无调整说明。" />
            </div>
          </div>
        </EditableSection>
      ) : null}

      <TextListSection
        title="教学目标"
        values={content.teaching_goals}
        isEditing={editingKey === "teaching_goals"}
        onToggleEdit={() => toggleEditing("teaching_goals")}
        onChange={(values) => updateValue("teaching_goals", values)}
        canEdit={!readOnly}
      />
      <TextListSection
        title="教学重难点"
        values={content.key_points}
        isEditing={editingKey === "key_points"}
        onToggleEdit={() => toggleEditing("key_points")}
        onChange={(values) => updateValue("key_points", values)}
        canEdit={!readOnly}
      />
      <TextListSection
        title="易错点"
        values={content.common_mistakes}
        isEditing={editingKey === "common_mistakes"}
        onToggleEdit={() => toggleEditing("common_mistakes")}
        onChange={(values) => updateValue("common_mistakes", values)}
        canEdit={!readOnly}
      />

      <ActivitySection
        title="热身"
        values={content.warmup}
        isEditing={editingKey === "warmup"}
        onToggleEdit={() => toggleEditing("warmup")}
        onChange={(values) => updateValue("warmup", values)}
        canEdit={!readOnly}
      />
      <ActivitySection
        title="主体教学"
        values={content.main_teaching}
        isEditing={editingKey === "main_teaching"}
        onToggleEdit={() => toggleEditing("main_teaching")}
        onChange={(values) => updateValue("main_teaching", values)}
        canEdit={!readOnly}
      />
      <MovementSection
        values={content.movement_breakdown}
        isEditing={editingKey === "movement_breakdown"}
        onToggleEdit={() => toggleEditing("movement_breakdown")}
        onChange={(values) => updateValue("movement_breakdown", values)}
        canEdit={!readOnly}
      />
      <ActivitySection
        title="放松"
        values={content.cooldown}
        isEditing={editingKey === "cooldown"}
        onToggleEdit={() => toggleEditing("cooldown")}
        onChange={(values) => updateValue("cooldown", values)}
        canEdit={!readOnly}
      />

      <TextListSection
        title="课后任务"
        values={content.homework}
        isEditing={editingKey === "homework"}
        onToggleEdit={() => toggleEditing("homework")}
        onChange={(values) => updateValue("homework", values)}
        canEdit={!readOnly}
      />
      <TextListSection
        title="老师提醒"
        values={content.teacher_notes}
        isEditing={editingKey === "teacher_notes"}
        onToggleEdit={() => toggleEditing("teacher_notes")}
        onChange={(values) => updateValue("teacher_notes", values)}
        canEdit={!readOnly}
      />

      {modelInfo ? <ModelInfoLine modelInfo={modelInfo} /> : null}
    </div>
  );
}

function TextListSection({
  title,
  values,
  isEditing,
  onToggleEdit,
  onChange,
  canEdit,
}: {
  title: string;
  values: string[];
  isEditing: boolean;
  onToggleEdit: () => void;
  onChange: (values: string[]) => void;
  canEdit: boolean;
}) {
  return (
    <EditableSection
      eyebrow="教学说明"
      title={title}
      isEditing={isEditing}
      onToggleEdit={onToggleEdit}
      canEdit={canEdit}
      editContent={<EditableList title={title} values={values} onChange={onChange} />}
    >
      <ReadableList values={values} />
    </EditableSection>
  );
}

function EditableList({ title, values, onChange }: { title: string; values: string[]; onChange: (values: string[]) => void }) {
  return (
    <FieldSet className="edit-section compact-section">
      <FieldLegend>{title}</FieldLegend>
      {values.map((value, index) => (
        <Textarea
          key={`${title}-${index}`}
          value={value}
          rows={2}
          onChange={(event) => onChange(values.map((item, itemIndex) => (itemIndex === index ? event.target.value : item)))}
        />
      ))}
    </FieldSet>
  );
}

function ActivitySection({
  title,
  values,
  isEditing,
  onToggleEdit,
  onChange,
  canEdit,
}: {
  title: string;
  values: LessonActivity[];
  isEditing: boolean;
  onToggleEdit: () => void;
  onChange: (values: LessonActivity[]) => void;
  canEdit: boolean;
}) {
  return (
    <EditableSection
      eyebrow="教学流程"
      title={title}
      isEditing={isEditing}
      onToggleEdit={onToggleEdit}
      canEdit={canEdit}
      editContent={<ActivityEditor title={title} values={values} onChange={onChange} />}
    >
      <div className="readable-timeline">
        {values.map((activity, index) => (
          <article className="readable-record" key={`${title}-${index}`}>
            <div className="readable-record-header">
              <h4>{activity.name}</h4>
              <span className="readable-chip">{activity.duration_minutes} 分钟</span>
            </div>
            <ReadableText value={activity.description} emptyText="暂无活动说明。" />
          </article>
        ))}
      </div>
    </EditableSection>
  );
}

function ActivityEditor({
  title,
  values,
  onChange,
}: {
  title: string;
  values: LessonActivity[];
  onChange: (values: LessonActivity[]) => void;
}) {
  return (
    <FieldSet className="edit-section">
      <FieldLegend>{title}</FieldLegend>
      {values.map((activity, index) => (
        <div className="activity-row" key={`${title}-${index}`}>
          <Input
            value={activity.name}
            onChange={(event) => updateActivity(index, { ...activity, name: event.target.value })}
            aria-label={`${title}名称`}
          />
          <Input
            type="number"
            min={0}
            value={activity.duration_minutes}
            onChange={(event) => updateActivity(index, { ...activity, duration_minutes: Number(event.target.value) })}
            aria-label={`${title}时长`}
          />
          <Textarea
            value={activity.description}
            rows={3}
            onChange={(event) => updateActivity(index, { ...activity, description: event.target.value })}
            aria-label={`${title}说明`}
          />
        </div>
      ))}
    </FieldSet>
  );

  function updateActivity(index: number, nextValue: LessonActivity) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }
}

function MovementSection({
  values,
  isEditing,
  onToggleEdit,
  onChange,
  canEdit,
}: {
  values: MovementStep[];
  isEditing: boolean;
  onToggleEdit: () => void;
  onChange: (values: MovementStep[]) => void;
  canEdit: boolean;
}) {
  return (
    <EditableSection
      eyebrow="动作教学"
      title="动作拆解"
      isEditing={isEditing}
      onToggleEdit={onToggleEdit}
      canEdit={canEdit}
      editContent={<MovementEditor values={values} onChange={onChange} />}
    >
      <div className="readable-grid">
        {values.map((step, index) => (
          <article className="readable-record" key={`movement-${index}`}>
            <div className="readable-record-header">
              <h4>{step.name}</h4>
              <span className="readable-chip">{step.beats || "未标注节拍"}</span>
            </div>
            <ReadableText value={step.teaching_tips} emptyText="暂无动作提示。" />
          </article>
        ))}
      </div>
    </EditableSection>
  );
}

function MovementEditor({ values, onChange }: { values: MovementStep[]; onChange: (values: MovementStep[]) => void }) {
  return (
    <FieldSet className="edit-section">
      <FieldLegend>动作拆解</FieldLegend>
      {values.map((step, index) => (
        <div className="movement-row" key={`movement-${index}`}>
          <Input
            value={step.name}
            onChange={(event) => updateStep(index, { ...step, name: event.target.value })}
            aria-label="动作名称"
          />
          <Input value={step.beats} onChange={(event) => updateStep(index, { ...step, beats: event.target.value })} aria-label="节拍" />
          <Textarea
            value={step.teaching_tips}
            rows={3}
            onChange={(event) => updateStep(index, { ...step, teaching_tips: event.target.value })}
            aria-label="动作提示"
          />
        </div>
      ))}
    </FieldSet>
  );

  function updateStep(index: number, nextValue: MovementStep) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }
}
