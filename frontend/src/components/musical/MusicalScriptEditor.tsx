import { useState } from "react";
import { TextareaField, TextField } from "../ui/FormFields";
import { EditableSection, EmptyReadable, ModelInfoLine, ReadableList, ReadableText } from "../ui/EditableSection";
import { FieldGroup, FieldLegend, FieldSet, FieldTitle } from "../ui/field";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import type { MusicalScriptContent, PerformanceSlot, ScriptAct, ScriptCharacter, ScriptDialogueLine } from "../../types";

export function MusicalScriptEditor({
  content,
  modelInfo,
  onChange,
}: {
  content: MusicalScriptContent;
  modelInfo: Record<string, unknown> | null;
  onChange: (content: MusicalScriptContent) => void;
}) {
  const [editingKey, setEditingKey] = useState<string | null>(null);

  function toggleEditing(key: string) {
    setEditingKey((current) => (current === key ? null : key));
  }

  function updateValue<Key extends keyof MusicalScriptContent>(key: Key, value: MusicalScriptContent[Key]) {
    onChange({ ...content, [key]: value });
  }

  return (
    <div className="lesson-editor readable-document">
      <EditableSection
        eyebrow="基础信息"
        title="剧目概况"
        summary="用于快速确认剧名、主题和整体故事方向。"
        isEditing={editingKey === "overview"}
        onToggleEdit={() => toggleEditing("overview")}
        editContent={
          <>
            <TextField label="剧名" value={content.title} onChange={(value) => updateValue("title", value)} />
            <TextareaField label="剧目简介" value={content.synopsis} onChange={(value) => updateValue("synopsis", value)} />
          </>
        }
      >
        <div className="readable-title-block">
          <h2>{content.title}</h2>
          <ReadableText value={content.synopsis} emptyText="暂无剧目简介。" />
        </div>
      </EditableSection>

      <EditableSection
        eyebrow="剧情结构"
        title="分幕剧情"
        summary={`${content.acts.length} 个剧情段落，包含故事推进、旁白和台词提示。`}
        isEditing={editingKey === "acts"}
        onToggleEdit={() => toggleEditing("acts")}
        editContent={<ActEditor values={content.acts} onChange={(values) => updateValue("acts", values)} />}
      >
        <ActReadView values={content.acts} />
      </EditableSection>

      <EditableSection
        eyebrow="角色"
        title="人物设定"
        summary={`${content.characters.length} 个角色，便于老师和学生快速分工。`}
        isEditing={editingKey === "characters"}
        onToggleEdit={() => toggleEditing("characters")}
        editContent={<CharacterEditor values={content.characters} onChange={(values) => updateValue("characters", values)} />}
      >
        <CharacterReadView values={content.characters} />
      </EditableSection>

      <EditableSection
        eyebrow="舞台调度"
        title="表演留白段落"
        summary="标注适合舞蹈、走位或群体表演插入的位置。"
        isEditing={editingKey === "performance_slots"}
        onToggleEdit={() => toggleEditing("performance_slots")}
        editContent={<PerformanceSlotEditor values={content.performance_slots} onChange={(values) => updateValue("performance_slots", values)} />}
      >
        <PerformanceSlotReadView values={content.performance_slots} />
      </EditableSection>

      <EditableSection
        eyebrow="复核"
        title="编导确认提醒"
        isEditing={editingKey === "director_notes"}
        onToggleEdit={() => toggleEditing("director_notes")}
        editContent={<EditableList title="编导确认提醒" values={content.director_notes} onChange={(values) => updateValue("director_notes", values)} />}
      >
        <ReadableList values={content.director_notes} />
      </EditableSection>

      {modelInfo ? <ModelInfoLine modelInfo={modelInfo} /> : null}
    </div>
  );
}

function ActReadView({ values }: { values: ScriptAct[] }) {
  if (values.length === 0) {
    return <EmptyReadable text="暂无分幕剧情。" />;
  }
  return (
    <div className="readable-timeline">
      {values.map((act, index) => (
        <article className="readable-record script-act-record" key={`act-read-${index}`}>
          <div className="readable-record-header">
            <div>
              <p className="readable-record-kicker">第 {index + 1} 幕</p>
              <h4>{act.name}</h4>
            </div>
            <div className="readable-chip-row">
              <span className="readable-chip">{act.duration_minutes} 分钟</span>
              <span className="readable-chip">{act.emotion || "未标注情绪"}</span>
            </div>
          </div>
          <div className="readable-two-column">
            <div>
              <h5>剧情大纲</h5>
              <ReadableText value={act.story_outline} emptyText="暂无剧情大纲。" />
            </div>
            <div>
              <h5>旁白</h5>
              <ReadableText value={act.narrator_text} emptyText="暂无旁白。" />
            </div>
          </div>
          <DialogueReadView values={act.dialogues} />
        </article>
      ))}
    </div>
  );
}

function DialogueReadView({ values }: { values: ScriptDialogueLine[] }) {
  if (values.length === 0) {
    return <EmptyReadable text="暂无台词。" />;
  }
  return (
    <div className="readable-dialogues">
      <h5>台词与表演提示</h5>
      {values.map((dialogue, index) => (
        <div className="readable-dialogue-row" key={`dialogue-read-${index}`}>
          <strong>{dialogue.role_name || "未命名角色"}</strong>
          <p>{dialogue.line || "暂无台词。"}</p>
          <em>{dialogue.stage_direction || "暂无表演提示。"}</em>
        </div>
      ))}
    </div>
  );
}

function ActEditor({ values, onChange }: { values: ScriptAct[]; onChange: (values: ScriptAct[]) => void }) {
  return (
    <FieldSet className="edit-section">
      <FieldLegend>分幕剧情</FieldLegend>
      {values.map((act, index) => (
        <FieldGroup className="nested-editor" key={`act-${index}`}>
          <div className="activity-row">
            <Input value={act.name} onChange={(event) => updateAct(index, { ...act, name: event.target.value })} aria-label="幕名" />
            <Input
              type="number"
              min={0}
              value={act.duration_minutes}
              onChange={(event) => updateAct(index, { ...act, duration_minutes: Number(event.target.value) })}
              aria-label="时长"
            />
            <Input value={act.emotion} onChange={(event) => updateAct(index, { ...act, emotion: event.target.value })} aria-label="情绪基调" />
          </div>
          <Textarea
            value={act.story_outline}
            rows={3}
            onChange={(event) => updateAct(index, { ...act, story_outline: event.target.value })}
            aria-label="剧情大纲"
          />
          <Textarea
            value={act.narrator_text}
            rows={3}
            onChange={(event) => updateAct(index, { ...act, narrator_text: event.target.value })}
            aria-label="旁白"
          />
          <DialogueEditor values={act.dialogues} onChange={(dialogues) => updateAct(index, { ...act, dialogues })} />
        </FieldGroup>
      ))}
    </FieldSet>
  );

  function updateAct(index: number, nextValue: ScriptAct) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }
}

function DialogueEditor({ values, onChange }: { values: ScriptDialogueLine[]; onChange: (values: ScriptDialogueLine[]) => void }) {
  return (
    <FieldGroup className="sub-list">
      <FieldTitle>台词</FieldTitle>
      {values.map((dialogue, index) => (
        <div className="dialogue-row" key={`dialogue-${index}`}>
          <Input
            value={dialogue.role_name}
            onChange={(event) => updateDialogue(index, { ...dialogue, role_name: event.target.value })}
            aria-label="角色名"
          />
          <Textarea
            value={dialogue.line}
            rows={2}
            onChange={(event) => updateDialogue(index, { ...dialogue, line: event.target.value })}
            aria-label="台词"
          />
          <Textarea
            value={dialogue.stage_direction}
            rows={2}
            onChange={(event) => updateDialogue(index, { ...dialogue, stage_direction: event.target.value })}
            aria-label="表演提示"
          />
        </div>
      ))}
    </FieldGroup>
  );

  function updateDialogue(index: number, nextValue: ScriptDialogueLine) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }
}

function CharacterReadView({ values }: { values: ScriptCharacter[] }) {
  if (values.length === 0) {
    return <EmptyReadable text="暂无人物设定。" />;
  }
  return (
    <div className="readable-grid">
      {values.map((character, index) => (
        <article className="readable-record" key={`character-read-${index}`}>
          <div className="readable-record-header">
            <h4>{character.name}</h4>
            <span className="readable-chip">{character.role_type || "未标注类型"}</span>
          </div>
          <dl className="readable-definition-list">
            <div>
              <dt>性格特点</dt>
              <dd>{character.personality || "暂无"}</dd>
            </div>
            <div>
              <dt>人物弧光</dt>
              <dd>{character.character_arc || "暂无"}</dd>
            </div>
            <div>
              <dt>表演提示</dt>
              <dd>{character.performance_tips || "暂无"}</dd>
            </div>
          </dl>
          <ReadableList values={character.key_lines} emptyText="暂无关键台词。" />
        </article>
      ))}
    </div>
  );
}

function CharacterEditor({ values, onChange }: { values: ScriptCharacter[]; onChange: (values: ScriptCharacter[]) => void }) {
  return (
    <FieldSet className="edit-section">
      <FieldLegend>人物设定</FieldLegend>
      {values.map((character, index) => (
        <FieldGroup className="nested-editor" key={`character-${index}`}>
          <div className="field-grid">
            <Input
              value={character.name}
              onChange={(event) => updateCharacter(index, { ...character, name: event.target.value })}
              aria-label="角色名称"
            />
            <Input
              value={character.role_type}
              onChange={(event) => updateCharacter(index, { ...character, role_type: event.target.value })}
              aria-label="角色类型"
            />
          </div>
          <Textarea
            value={character.personality}
            rows={2}
            onChange={(event) => updateCharacter(index, { ...character, personality: event.target.value })}
            aria-label="性格特点"
          />
          <Textarea
            value={character.character_arc}
            rows={2}
            onChange={(event) => updateCharacter(index, { ...character, character_arc: event.target.value })}
            aria-label="人物弧光"
          />
          <Textarea
            value={character.performance_tips}
            rows={2}
            onChange={(event) => updateCharacter(index, { ...character, performance_tips: event.target.value })}
            aria-label="表演提示"
          />
          <EditableList
            title="关键台词"
            values={character.key_lines}
            onChange={(keyLines) => updateCharacter(index, { ...character, key_lines: keyLines })}
          />
        </FieldGroup>
      ))}
    </FieldSet>
  );

  function updateCharacter(index: number, nextValue: ScriptCharacter) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }
}

function PerformanceSlotReadView({ values }: { values: PerformanceSlot[] }) {
  if (values.length === 0) {
    return <EmptyReadable text="暂无表演留白段落。" />;
  }
  return (
    <div className="readable-grid">
      {values.map((slot, index) => (
        <article className="readable-record" key={`slot-read-${index}`}>
          <div className="readable-record-header">
            <h4>{slot.act_name}</h4>
            <span className="readable-chip">{slot.slot_type || "未标注类型"}</span>
          </div>
          <ReadableText value={slot.description} emptyText="暂无留白说明。" />
          <dl className="readable-definition-list compact">
            <div>
              <dt>建议时长</dt>
              <dd>{slot.suggested_duration || "暂无"}</dd>
            </div>
            <div>
              <dt>提醒</dt>
              <dd>{slot.notes || "暂无"}</dd>
            </div>
          </dl>
        </article>
      ))}
    </div>
  );
}

function PerformanceSlotEditor({ values, onChange }: { values: PerformanceSlot[]; onChange: (values: PerformanceSlot[]) => void }) {
  return (
    <FieldSet className="edit-section">
      <FieldLegend>表演留白段落</FieldLegend>
      {values.map((slot, index) => (
        <div className="movement-row" key={`slot-${index}`}>
          <Input value={slot.act_name} onChange={(event) => updateSlot(index, { ...slot, act_name: event.target.value })} aria-label="对应幕名" />
          <Input value={slot.slot_type} onChange={(event) => updateSlot(index, { ...slot, slot_type: event.target.value })} aria-label="段落类型" />
          <Textarea
            value={`${slot.description}\n建议时长：${slot.suggested_duration}\n提醒：${slot.notes}`}
            rows={4}
            onChange={(event) => updateSlotFromText(index, slot, event.target.value)}
            aria-label="留白说明"
          />
        </div>
      ))}
    </FieldSet>
  );

  function updateSlot(index: number, nextValue: PerformanceSlot) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }

  function updateSlotFromText(index: number, slot: PerformanceSlot, value: string) {
    const [description = "", durationLine = "", notesLine = ""] = value.split("\n");
    updateSlot(index, {
      ...slot,
      description,
      suggested_duration: durationLine.replace("建议时长：", ""),
      notes: notesLine.replace("提醒：", ""),
    });
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
