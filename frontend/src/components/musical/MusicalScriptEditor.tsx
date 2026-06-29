import { TextareaField, TextField } from "../ui/FormFields";
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
  function updateValue<Key extends keyof MusicalScriptContent>(key: Key, value: MusicalScriptContent[Key]) {
    onChange({ ...content, [key]: value });
  }

  return (
    <div className="lesson-editor">
      <TextField label="剧名" value={content.title} onChange={(value) => updateValue("title", value)} />
      <TextareaField label="剧目简介" value={content.synopsis} onChange={(value) => updateValue("synopsis", value)} />
      <ActList values={content.acts} onChange={(values) => updateValue("acts", values)} />
      <CharacterList values={content.characters} onChange={(values) => updateValue("characters", values)} />
      <PerformanceSlotList values={content.performance_slots} onChange={(values) => updateValue("performance_slots", values)} />
      <EditableList title="编导确认提醒" values={content.director_notes} onChange={(values) => updateValue("director_notes", values)} />
      {modelInfo ? <ModelInfo modelInfo={modelInfo} /> : null}
    </div>
  );
}

function ActList({ values, onChange }: { values: ScriptAct[]; onChange: (values: ScriptAct[]) => void }) {
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
          <DialogueList values={act.dialogues} onChange={(dialogues) => updateAct(index, { ...act, dialogues })} />
        </FieldGroup>
      ))}
    </FieldSet>
  );

  function updateAct(index: number, nextValue: ScriptAct) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }
}

function DialogueList({ values, onChange }: { values: ScriptDialogueLine[]; onChange: (values: ScriptDialogueLine[]) => void }) {
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

function CharacterList({ values, onChange }: { values: ScriptCharacter[]; onChange: (values: ScriptCharacter[]) => void }) {
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

function PerformanceSlotList({ values, onChange }: { values: PerformanceSlot[]; onChange: (values: PerformanceSlot[]) => void }) {
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

function ModelInfo({ modelInfo }: { modelInfo: Record<string, unknown> }) {
  return (
    <p className="model-info">
      模型：{String(modelInfo.provider)} / {String(modelInfo.model)} / {String(modelInfo.prompt_version)}
      {modelInfo.reasoning_level ? ` / ${String(modelInfo.reasoning_level)}` : ""}
    </p>
  );
}
