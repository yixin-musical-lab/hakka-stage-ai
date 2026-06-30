import { useState } from "react";
import { TextareaField, TextField } from "../ui/FormFields";
import { EditableSection, EmptyReadable, ModelInfoLine, ReadableList, ReadableText } from "../ui/EditableSection";
import { FieldGroup, FieldLegend, FieldSet } from "../ui/field";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
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
  const [editingKey, setEditingKey] = useState<string | null>(null);

  function toggleEditing(key: string) {
    setEditingKey((current) => (current === key ? null : key));
  }

  function updateValue<Key extends keyof RoleTrainingContent>(key: Key, value: RoleTrainingContent[Key]) {
    onChange({ ...content, [key]: value });
  }

  return (
    <div className="lesson-editor readable-document">
      <EditableSection
        eyebrow="基础信息"
        title="排练概况"
        summary="用于快速确认训练计划名称和整体排练目标。"
        isEditing={editingKey === "overview"}
        onToggleEdit={() => toggleEditing("overview")}
        editContent={
          <>
            <TextField label="训练计划标题" value={content.title} onChange={(value) => updateValue("title", value)} />
            <TextareaField label="排练概况" value={content.project_overview} onChange={(value) => updateValue("project_overview", value)} />
          </>
        }
      >
        <div className="readable-title-block">
          <h2>{content.title}</h2>
          <ReadableText value={content.project_overview} emptyText="暂无排练概况。" />
        </div>
      </EditableSection>

      <EditableSection
        eyebrow="角色训练"
        title="分角色任务"
        summary={`${content.role_tasks.length} 个角色任务，覆盖台词、演唱、舞蹈和走位。`}
        isEditing={editingKey === "role_tasks"}
        onToggleEdit={() => toggleEditing("role_tasks")}
        editContent={<RoleTaskEditor values={content.role_tasks} onChange={(values) => updateValue("role_tasks", values)} />}
      >
        <RoleTaskReadView values={content.role_tasks} />
      </EditableSection>

      <EditableSection
        eyebrow="排练节奏"
        title="每日排练安排"
        summary={`${content.daily_plan.length} 天排练安排，方便老师按天检查。`}
        isEditing={editingKey === "daily_plan"}
        onToggleEdit={() => toggleEditing("daily_plan")}
        editContent={<DailyPlanEditor values={content.daily_plan} onChange={(values) => updateValue("daily_plan", values)} />}
      >
        <DailyPlanReadView values={content.daily_plan} />
      </EditableSection>

      <EditableSection
        eyebrow="复核"
        title="老师检查点"
        isEditing={editingKey === "teacher_checkpoints"}
        onToggleEdit={() => toggleEditing("teacher_checkpoints")}
        editContent={
          <EditableList
            title="老师检查点"
            values={content.teacher_checkpoints}
            onChange={(values) => updateValue("teacher_checkpoints", values)}
          />
        }
      >
        <ReadableList values={content.teacher_checkpoints} />
      </EditableSection>

      {modelInfo ? <ModelInfoLine modelInfo={modelInfo} /> : null}
    </div>
  );
}

function RoleTaskReadView({ values }: { values: RoleTrainingItem[] }) {
  if (values.length === 0) {
    return <EmptyReadable text="暂无分角色任务。" />;
  }
  return (
    <div className="readable-grid">
      {values.map((roleTask, index) => (
        <article className="readable-record" key={`role-task-read-${index}`}>
          <div className="readable-record-header">
            <h4>{roleTask.role_name}</h4>
            <span className="readable-chip">{roleTask.role_type || "未标注角色类型"}</span>
          </div>
          <dl className="readable-definition-list">
            <div>
              <dt>台词重点</dt>
              <dd>{roleTask.line_focus || "暂无"}</dd>
            </div>
            <div>
              <dt>演唱重点</dt>
              <dd>{roleTask.singing_focus || "暂无"}</dd>
            </div>
            <div>
              <dt>舞蹈重点</dt>
              <dd>{roleTask.dance_focus || "暂无"}</dd>
            </div>
            <div>
              <dt>走位提醒</dt>
              <dd>{roleTask.blocking_tips || "暂无"}</dd>
            </div>
          </dl>
          <div className="readable-two-column">
            <div>
              <h5>每日任务</h5>
              <ReadableList values={roleTask.daily_tasks} emptyText="暂无每日任务。" />
            </div>
            <div>
              <h5>角色检查点</h5>
              <ReadableList values={roleTask.teacher_checkpoints} emptyText="暂无角色检查点。" />
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function RoleTaskEditor({ values, onChange }: { values: RoleTrainingItem[]; onChange: (values: RoleTrainingItem[]) => void }) {
  return (
    <FieldSet className="edit-section">
      <FieldLegend>分角色任务</FieldLegend>
      {values.map((roleTask, index) => (
        <FieldGroup className="nested-editor" key={`role-task-${index}`}>
          <div className="field-grid">
            <Input
              value={roleTask.role_name}
              onChange={(event) => updateRoleTask(index, { ...roleTask, role_name: event.target.value })}
              aria-label="角色名称"
            />
            <Input
              value={roleTask.role_type}
              onChange={(event) => updateRoleTask(index, { ...roleTask, role_type: event.target.value })}
              aria-label="角色类型"
            />
          </div>
          <Textarea
            value={roleTask.line_focus}
            rows={2}
            onChange={(event) => updateRoleTask(index, { ...roleTask, line_focus: event.target.value })}
            aria-label="台词训练重点"
          />
          <Textarea
            value={roleTask.singing_focus}
            rows={2}
            onChange={(event) => updateRoleTask(index, { ...roleTask, singing_focus: event.target.value })}
            aria-label="演唱训练重点"
          />
          <Textarea
            value={roleTask.dance_focus}
            rows={2}
            onChange={(event) => updateRoleTask(index, { ...roleTask, dance_focus: event.target.value })}
            aria-label="舞蹈训练重点"
          />
          <Textarea
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
        </FieldGroup>
      ))}
    </FieldSet>
  );

  function updateRoleTask(index: number, nextValue: RoleTrainingItem) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }
}

function DailyPlanReadView({ values }: { values: RoleDailyPlan[] }) {
  if (values.length === 0) {
    return <EmptyReadable text="暂无每日排练安排。" />;
  }
  return (
    <div className="readable-timeline">
      {values.map((dailyPlan, index) => (
        <article className="readable-record" key={`daily-plan-read-${index}`}>
          <div className="readable-record-header">
            <div>
              <p className="readable-record-kicker">第 {index + 1} 天</p>
              <h4>{dailyPlan.day}</h4>
            </div>
            <span className="readable-chip">{dailyPlan.focus || "未标注重点"}</span>
          </div>
          <ReadableList values={dailyPlan.tasks} emptyText="暂无当天任务。" />
          <div className="readable-callout">
            <strong>预期结果</strong>
            <ReadableText value={dailyPlan.expected_result} emptyText="暂无预期结果。" />
          </div>
        </article>
      ))}
    </div>
  );
}

function DailyPlanEditor({ values, onChange }: { values: RoleDailyPlan[]; onChange: (values: RoleDailyPlan[]) => void }) {
  return (
    <FieldSet className="edit-section">
      <FieldLegend>每日排练安排</FieldLegend>
      {values.map((dailyPlan, index) => (
        <FieldGroup className="nested-editor" key={`daily-plan-${index}`}>
          <div className="field-grid">
            <Input value={dailyPlan.day} onChange={(event) => updateDailyPlan(index, { ...dailyPlan, day: event.target.value })} aria-label="日期" />
            <Input
              value={dailyPlan.focus}
              onChange={(event) => updateDailyPlan(index, { ...dailyPlan, focus: event.target.value })}
              aria-label="当天重点"
            />
          </div>
          <EditableList title="当天任务" values={dailyPlan.tasks} onChange={(tasks) => updateDailyPlan(index, { ...dailyPlan, tasks })} />
          <Textarea
            value={dailyPlan.expected_result}
            rows={2}
            onChange={(event) => updateDailyPlan(index, { ...dailyPlan, expected_result: event.target.value })}
            aria-label="预期结果"
          />
        </FieldGroup>
      ))}
    </FieldSet>
  );

  function updateDailyPlan(index: number, nextValue: RoleDailyPlan) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }
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
