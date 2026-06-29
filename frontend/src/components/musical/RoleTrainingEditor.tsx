import { TextareaField, TextField } from "../ui/FormFields";
import type { RoleDailyPlan, RoleTrainingContent, RoleTrainingItem } from "../../types";

export function RoleTrainingEditor({
  content,
  modelInfo,
  onChange,
}: {
  content: RoleTrainingContent;
  modelInfo: Record<string, unknown> | null;
  onChange: (content: RoleTrainingContent) => void;
}) {
  function updateValue<Key extends keyof RoleTrainingContent>(key: Key, value: RoleTrainingContent[Key]) {
    onChange({ ...content, [key]: value });
  }

  return (
    <div className="lesson-editor">
      <TextField label="训练计划标题" value={content.title} onChange={(value) => updateValue("title", value)} />
      <TextareaField label="排练概况" value={content.project_overview} onChange={(value) => updateValue("project_overview", value)} />
      <RoleTaskList values={content.role_tasks} onChange={(values) => updateValue("role_tasks", values)} />
      <DailyPlanList values={content.daily_plan} onChange={(values) => updateValue("daily_plan", values)} />
      <EditableList title="老师检查点" values={content.teacher_checkpoints} onChange={(values) => updateValue("teacher_checkpoints", values)} />
      {modelInfo ? <ModelInfo modelInfo={modelInfo} /> : null}
    </div>
  );
}

function RoleTaskList({ values, onChange }: { values: RoleTrainingItem[]; onChange: (values: RoleTrainingItem[]) => void }) {
  return (
    <section className="edit-section">
      <h3>分角色任务</h3>
      {values.map((roleTask, index) => (
        <div className="nested-editor" key={`role-task-${index}`}>
          <div className="field-grid">
            <input
              value={roleTask.role_name}
              onChange={(event) => updateRoleTask(index, { ...roleTask, role_name: event.target.value })}
              aria-label="角色名称"
            />
            <input
              value={roleTask.role_type}
              onChange={(event) => updateRoleTask(index, { ...roleTask, role_type: event.target.value })}
              aria-label="角色类型"
            />
          </div>
          <textarea
            value={roleTask.line_focus}
            rows={2}
            onChange={(event) => updateRoleTask(index, { ...roleTask, line_focus: event.target.value })}
            aria-label="台词训练重点"
          />
          <textarea
            value={roleTask.singing_focus}
            rows={2}
            onChange={(event) => updateRoleTask(index, { ...roleTask, singing_focus: event.target.value })}
            aria-label="演唱训练重点"
          />
          <textarea
            value={roleTask.dance_focus}
            rows={2}
            onChange={(event) => updateRoleTask(index, { ...roleTask, dance_focus: event.target.value })}
            aria-label="舞蹈训练重点"
          />
          <textarea
            value={roleTask.blocking_tips}
            rows={2}
            onChange={(event) => updateRoleTask(index, { ...roleTask, blocking_tips: event.target.value })}
            aria-label="走位提醒"
          />
          <EditableList
            title="每日任务"
            values={roleTask.daily_tasks}
            onChange={(dailyTasks) => updateRoleTask(index, { ...roleTask, daily_tasks: dailyTasks })}
          />
          <EditableList
            title="角色检查点"
            values={roleTask.teacher_checkpoints}
            onChange={(checkpoints) => updateRoleTask(index, { ...roleTask, teacher_checkpoints: checkpoints })}
          />
        </div>
      ))}
    </section>
  );

  function updateRoleTask(index: number, nextValue: RoleTrainingItem) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }
}

function DailyPlanList({ values, onChange }: { values: RoleDailyPlan[]; onChange: (values: RoleDailyPlan[]) => void }) {
  return (
    <section className="edit-section">
      <h3>每日排练安排</h3>
      {values.map((dailyPlan, index) => (
        <div className="nested-editor" key={`daily-plan-${index}`}>
          <div className="field-grid">
            <input value={dailyPlan.day} onChange={(event) => updateDailyPlan(index, { ...dailyPlan, day: event.target.value })} aria-label="日期" />
            <input
              value={dailyPlan.focus}
              onChange={(event) => updateDailyPlan(index, { ...dailyPlan, focus: event.target.value })}
              aria-label="当天重点"
            />
          </div>
          <EditableList title="当天任务" values={dailyPlan.tasks} onChange={(tasks) => updateDailyPlan(index, { ...dailyPlan, tasks })} />
          <textarea
            value={dailyPlan.expected_result}
            rows={2}
            onChange={(event) => updateDailyPlan(index, { ...dailyPlan, expected_result: event.target.value })}
            aria-label="预期结果"
          />
        </div>
      ))}
    </section>
  );

  function updateDailyPlan(index: number, nextValue: RoleDailyPlan) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }
}

function EditableList({ title, values, onChange }: { title: string; values: string[]; onChange: (values: string[]) => void }) {
  return (
    <section className="edit-section compact-section">
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

function ModelInfo({ modelInfo }: { modelInfo: Record<string, unknown> }) {
  return (
    <p className="model-info">
      模型：{String(modelInfo.provider)} / {String(modelInfo.model)} / {String(modelInfo.prompt_version)}
      {modelInfo.reasoning_level ? ` / ${String(modelInfo.reasoning_level)}` : ""}
    </p>
  );
}
