import { TextareaField, TextField } from "../ui/FormFields";
import type { LessonActivity, LessonPlanContent, MovementStep } from "../../types";

export function LessonEditor({
  content,
  modelInfo,
  onChange,
}: {
  content: LessonPlanContent;
  modelInfo: Record<string, unknown> | null;
  onChange: (content: LessonPlanContent) => void;
}) {
  function updateValue<Key extends keyof LessonPlanContent>(key: Key, value: LessonPlanContent[Key]) {
    onChange({ ...content, [key]: value });
  }

  return (
    <div className="lesson-editor">
      <TextField label="教案标题" value={content.title} onChange={(value) => updateValue("title", value)} />
      <TextareaField label="课程概况" value={content.course_overview} onChange={(value) => updateValue("course_overview", value)} />
      <EditableList title="教学目标" values={content.teaching_goals} onChange={(values) => updateValue("teaching_goals", values)} />
      <EditableList title="教学重难点" values={content.key_points} onChange={(values) => updateValue("key_points", values)} />
      <EditableList title="易错点" values={content.common_mistakes} onChange={(values) => updateValue("common_mistakes", values)} />
      <ActivityList title="热身" values={content.warmup} onChange={(values) => updateValue("warmup", values)} />
      <ActivityList title="主体教学" values={content.main_teaching} onChange={(values) => updateValue("main_teaching", values)} />
      <MovementList values={content.movement_breakdown} onChange={(values) => updateValue("movement_breakdown", values)} />
      <ActivityList title="放松" values={content.cooldown} onChange={(values) => updateValue("cooldown", values)} />
      <EditableList title="课后任务" values={content.homework} onChange={(values) => updateValue("homework", values)} />
      <EditableList title="老师提醒" values={content.teacher_notes} onChange={(values) => updateValue("teacher_notes", values)} />
      {modelInfo ? (
        <p className="model-info">
          模型：{String(modelInfo.provider)} / {String(modelInfo.model)} / {String(modelInfo.prompt_version)}
          {modelInfo.reasoning_level ? ` / ${String(modelInfo.reasoning_level)}` : ""}
        </p>
      ) : null}
    </div>
  );
}

function EditableList({ title, values, onChange }: { title: string; values: string[]; onChange: (values: string[]) => void }) {
  return (
    <section className="edit-section">
      <h3>{title}</h3>
      {values.map((value, index) => (
        <textarea
          key={`${title}-${index}`}
          value={value}
          rows={2}
          onChange={(event) => onChange(values.map((item, itemIndex) => (itemIndex === index ? event.target.value : item)))}
        />
      ))}
    </section>
  );
}

function ActivityList({
  title,
  values,
  onChange,
}: {
  title: string;
  values: LessonActivity[];
  onChange: (values: LessonActivity[]) => void;
}) {
  return (
    <section className="edit-section">
      <h3>{title}</h3>
      {values.map((activity, index) => (
        <div className="activity-row" key={`${title}-${index}`}>
          <input
            value={activity.name}
            onChange={(event) => updateActivity(index, { ...activity, name: event.target.value })}
            aria-label={`${title}名称`}
          />
          <input
            type="number"
            min={0}
            value={activity.duration_minutes}
            onChange={(event) => updateActivity(index, { ...activity, duration_minutes: Number(event.target.value) })}
            aria-label={`${title}时长`}
          />
          <textarea
            value={activity.description}
            rows={3}
            onChange={(event) => updateActivity(index, { ...activity, description: event.target.value })}
            aria-label={`${title}说明`}
          />
        </div>
      ))}
    </section>
  );

  function updateActivity(index: number, nextValue: LessonActivity) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }
}

function MovementList({ values, onChange }: { values: MovementStep[]; onChange: (values: MovementStep[]) => void }) {
  return (
    <section className="edit-section">
      <h3>动作拆解</h3>
      {values.map((step, index) => (
        <div className="movement-row" key={`movement-${index}`}>
          <input
            value={step.name}
            onChange={(event) => updateStep(index, { ...step, name: event.target.value })}
            aria-label="动作名称"
          />
          <input value={step.beats} onChange={(event) => updateStep(index, { ...step, beats: event.target.value })} aria-label="节拍" />
          <textarea
            value={step.teaching_tips}
            rows={3}
            onChange={(event) => updateStep(index, { ...step, teaching_tips: event.target.value })}
            aria-label="动作提示"
          />
        </div>
      ))}
    </section>
  );

  function updateStep(index: number, nextValue: MovementStep) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }
}
