import { useState } from "react";
import { TextareaField, TextField } from "../ui/FormFields";
import { EditableSection, EmptyReadable, ModelInfoLine, ReadableList, ReadableText } from "../ui/EditableSection";
import { FieldGroup, FieldLegend, FieldSet } from "../ui/field";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import type { DanceInterlude, SongAdaptationContent, SongSection } from "../../types";

export function SongAdaptationEditor({
  content,
  modelInfo,
  onChange,
}: {
  content: SongAdaptationContent;
  modelInfo: Record<string, unknown> | null;
  onChange: (content: SongAdaptationContent) => void;
}) {
  const [editingKey, setEditingKey] = useState<string | null>(null);

  function toggleEditing(key: string) {
    setEditingKey((current) => (current === key ? null : key));
  }

  function updateValue<Key extends keyof SongAdaptationContent>(key: Key, value: SongAdaptationContent[Key]) {
    onChange({ ...content, [key]: value });
  }

  return (
    <div className="lesson-editor readable-document">
      <EditableSection
        eyebrow="基础信息"
        title="唱段适配概况"
        summary="用于确认原曲来源、关联剧情和改写目标。"
        isEditing={editingKey === "overview"}
        onToggleEdit={() => toggleEditing("overview")}
        editContent={
          <>
            <TextField label="唱段适配标题" value={content.title} onChange={(value) => updateValue("title", value)} />
            <div className="field-grid">
              <TextField label="原曲 / 音乐来源" value={content.source_song} onChange={(value) => updateValue("source_song", value)} />
              <TextField label="关联剧情段落" value={content.related_scene} onChange={(value) => updateValue("related_scene", value)} />
            </div>
            <TextareaField label="改写目标" value={content.adaptation_goal} onChange={(value) => updateValue("adaptation_goal", value)} />
          </>
        }
      >
        <div className="readable-title-block">
          <h2>{content.title}</h2>
          <div className="readable-chip-row">
            <span className="readable-chip">{content.source_song || "未填写原曲"}</span>
            <span className="readable-chip">{content.related_scene || "未关联剧情"}</span>
          </div>
          <ReadableText value={content.adaptation_goal} emptyText="暂无改写目标。" />
        </div>
      </EditableSection>

      <EditableSection
        eyebrow="歌词"
        title="唱段结构与歌词建议"
        summary={`${content.sections.length} 个唱段段落，包含原词、改词和舞蹈衔接。`}
        isEditing={editingKey === "sections"}
        onToggleEdit={() => toggleEditing("sections")}
        editContent={<SongSectionEditor values={content.sections} onChange={(values) => updateValue("sections", values)} />}
      >
        <SongSectionReadView values={content.sections} />
      </EditableSection>

      <EditableSection
        eyebrow="舞蹈"
        title="间奏舞蹈与留白"
        summary="标注适合动作编排、队形变化或情绪转换的位置。"
        isEditing={editingKey === "dance_interludes"}
        onToggleEdit={() => toggleEditing("dance_interludes")}
        editContent={<DanceInterludeEditor values={content.dance_interludes} onChange={(values) => updateValue("dance_interludes", values)} />}
      >
        <DanceInterludeReadView values={content.dance_interludes} />
      </EditableSection>

      <EditableSection
        eyebrow="复核"
        title="复核提醒"
        isEditing={editingKey === "review_notes"}
        onToggleEdit={() => toggleEditing("review_notes")}
        editContent={<EditableList title="复核提醒" values={content.review_notes} onChange={(values) => updateValue("review_notes", values)} />}
      >
        <ReadableList values={content.review_notes} />
      </EditableSection>

      {modelInfo ? <ModelInfoLine modelInfo={modelInfo} /> : null}
    </div>
  );
}

function SongSectionReadView({ values }: { values: SongSection[] }) {
  if (values.length === 0) {
    return <EmptyReadable text="暂无唱段结构。" />;
  }
  return (
    <div className="readable-timeline">
      {values.map((section, index) => (
        <article className="readable-record" key={`song-section-read-${index}`}>
          <div className="readable-record-header">
            <div>
              <p className="readable-record-kicker">{section.section_no || `段落 ${index + 1}`}</p>
              <h4>{section.music_position || "未标注音乐位置"}</h4>
            </div>
            <div className="readable-chip-row">
              <span className="readable-chip">{section.singing_mode || "未标注演唱方式"}</span>
              <span className="readable-chip">{section.emotion || "未标注情绪"}</span>
            </div>
          </div>
          <div className="lyric-compare">
            <div>
              <h5>原歌词</h5>
              <ReadableText value={section.original_lyrics} emptyText="暂无原歌词。" />
            </div>
            <div>
              <h5>改写歌词</h5>
              <ReadableText value={section.adapted_lyrics} emptyText="暂无改写歌词。" />
            </div>
          </div>
          <div className="readable-two-column">
            <div>
              <h5>建议角色</h5>
              <ReadableList values={section.suggested_roles} emptyText="暂无建议角色。" />
            </div>
            <div>
              <h5>舞蹈留白</h5>
              <ReadableText value={section.dance_opportunity} emptyText="暂无舞蹈留白。" />
            </div>
          </div>
          <ReadableText value={section.transition_note} emptyText="暂无衔接说明。" />
        </article>
      ))}
    </div>
  );
}

function SongSectionEditor({ values, onChange }: { values: SongSection[]; onChange: (values: SongSection[]) => void }) {
  return (
    <FieldSet className="edit-section">
      <FieldLegend>唱段结构与歌词建议</FieldLegend>
      {values.map((section, index) => (
        <FieldGroup className="nested-editor" key={`song-section-${index}`}>
          <div className="field-grid">
            <Input
              value={section.section_no}
              onChange={(event) => updateSection(index, { ...section, section_no: event.target.value })}
              aria-label="唱段编号"
            />
            <Input
              value={section.music_position}
              onChange={(event) => updateSection(index, { ...section, music_position: event.target.value })}
              aria-label="音乐位置"
            />
          </div>
          <Textarea
            value={section.original_lyrics}
            rows={2}
            onChange={(event) => updateSection(index, { ...section, original_lyrics: event.target.value })}
            aria-label="原歌词"
          />
          <Textarea
            value={section.adapted_lyrics}
            rows={2}
            onChange={(event) => updateSection(index, { ...section, adapted_lyrics: event.target.value })}
            aria-label="改写歌词"
          />
          <div className="field-grid">
            <Input
              value={section.singing_mode}
              onChange={(event) => updateSection(index, { ...section, singing_mode: event.target.value })}
              aria-label="演唱方式"
            />
            <Input
              value={section.emotion}
              onChange={(event) => updateSection(index, { ...section, emotion: event.target.value })}
              aria-label="情绪基调"
            />
          </div>
          <Textarea
            value={section.suggested_roles.join("、")}
            rows={2}
            onChange={(event) => updateSection(index, { ...section, suggested_roles: splitRoleNames(event.target.value) })}
            aria-label="建议角色"
          />
          <Textarea
            value={section.dance_opportunity}
            rows={2}
            onChange={(event) => updateSection(index, { ...section, dance_opportunity: event.target.value })}
            aria-label="舞蹈留白"
          />
          <Textarea
            value={section.transition_note}
            rows={2}
            onChange={(event) => updateSection(index, { ...section, transition_note: event.target.value })}
            aria-label="衔接说明"
          />
        </FieldGroup>
      ))}
    </FieldSet>
  );

  function updateSection(index: number, nextValue: SongSection) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }
}

function DanceInterludeReadView({ values }: { values: DanceInterlude[] }) {
  if (values.length === 0) {
    return <EmptyReadable text="暂无间奏舞蹈建议。" />;
  }
  return (
    <div className="readable-grid">
      {values.map((interlude, index) => (
        <article className="readable-record" key={`dance-interlude-read-${index}`}>
          <div className="readable-record-header">
            <h4>{interlude.music_position || `间奏 ${index + 1}`}</h4>
          </div>
          <ReadableText value={interlude.suggestion} emptyText="暂无间奏建议。" />
        </article>
      ))}
    </div>
  );
}

function DanceInterludeEditor({ values, onChange }: { values: DanceInterlude[]; onChange: (values: DanceInterlude[]) => void }) {
  return (
    <FieldSet className="edit-section">
      <FieldLegend>间奏舞蹈与留白</FieldLegend>
      {values.map((interlude, index) => (
        <FieldGroup className="nested-editor" key={`dance-interlude-${index}`}>
          <Input
            value={interlude.music_position}
            onChange={(event) => updateInterlude(index, { ...interlude, music_position: event.target.value })}
            aria-label="间奏位置"
          />
          <Textarea
            value={interlude.suggestion}
            rows={2}
            onChange={(event) => updateInterlude(index, { ...interlude, suggestion: event.target.value })}
            aria-label="间奏建议"
          />
        </FieldGroup>
      ))}
    </FieldSet>
  );

  function updateInterlude(index: number, nextValue: DanceInterlude) {
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

function splitRoleNames(value: string) {
  // 同时兼容顿号、中文逗号、英文逗号和换行，方便老师快速粘贴角色列表。
  return value
    .split(/[、，,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}
