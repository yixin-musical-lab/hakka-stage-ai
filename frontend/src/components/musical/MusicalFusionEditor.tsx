import { useState } from "react";
import { Badge } from "../ui/badge";
import { EditableSection, EmptyReadable, ModelInfoLine, ReadableList, ReadableText } from "../ui/EditableSection";
import { Field, FieldGroup, FieldLabel, FieldLegend, FieldSet } from "../ui/field";
import { NumberField, TextareaField, TextField } from "../ui/FormFields";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { ToggleGroup, ToggleGroupItem } from "../ui/toggle-group";
import type { MusicalFusionContent, MusicalFusionSegment } from "../../types";

export function MusicalFusionEditor({
  content,
  modelInfo,
  onChange,
}: {
  content: MusicalFusionContent;
  modelInfo: Record<string, unknown> | null;
  onChange: (content: MusicalFusionContent) => void;
}) {
  const [editingKey, setEditingKey] = useState<string | null>(null);

  function updateValue<Key extends keyof MusicalFusionContent>(key: Key, value: MusicalFusionContent[Key]) {
    onChange({ ...content, [key]: value });
  }

  return (
    <div className="lesson-editor readable-document">
      <EditableSection
        eyebrow="编导概况"
        title="歌舞融合总体设计"
        summary="确认剧情范围、场地、人数和本次唱跳融合目标。"
        isEditing={editingKey === "overview"}
        onToggleEdit={() => setEditingKey((current) => (current === "overview" ? null : "overview"))}
        editContent={
          <FieldGroup>
            <TextField label="方案标题" value={content.title} onChange={(value) => updateValue("title", value)} />
            <TextField label="关联剧情段落" value={content.related_scene} onChange={(value) => updateValue("related_scene", value)} />
            <TextareaField label="融合目标" value={content.fusion_goal} onChange={(value) => updateValue("fusion_goal", value)} />
            <div className="field-grid">
              <NumberField label="演员人数" value={content.actor_count} onChange={(value) => updateValue("actor_count", value)} />
              <TextField label="舞台空间" value={content.stage_space} onChange={(value) => updateValue("stage_space", value)} />
            </div>
            <TextareaField label="整体设计" rows={5} value={content.overall_design} onChange={(value) => updateValue("overall_design", value)} />
          </FieldGroup>
        }
      >
        <div className="readable-title-block">
          <h2>{content.title}</h2>
          <div className="readable-chip-row">
            <Badge variant="secondary">{content.actor_count} 人</Badge>
            <Badge variant="outline">{content.stage_space}</Badge>
          </div>
          <ReadableText value={content.related_scene} emptyText="暂无关联剧情。" />
          <ReadableText value={content.fusion_goal} emptyText="暂无融合目标。" />
          <ReadableText value={content.overall_design} emptyText="暂无整体设计。" />
        </div>
      </EditableSection>

      <EditableSection
        eyebrow="结构表"
        title="唱、跳、队形与衔接"
        summary={`${content.segments.length} 个排练段落，高潮段落已单独标记。`}
        isEditing={editingKey === "segments"}
        onToggleEdit={() => setEditingKey((current) => (current === "segments" ? null : "segments"))}
        editContent={<FusionSegmentEditor values={content.segments} onChange={(values) => updateValue("segments", values)} />}
      >
        <FusionSegmentReadView values={content.segments} />
      </EditableSection>

      <EditableSection
        eyebrow="高潮"
        title="重点段落设计"
        summary="说明唱跳爆发点以及编导需要重点检查的内容。"
        isEditing={editingKey === "highlight_summary"}
        onToggleEdit={() => setEditingKey((current) => (current === "highlight_summary" ? null : "highlight_summary"))}
        editContent={<TextareaField label="高潮设计" rows={5} value={content.highlight_summary} onChange={(value) => updateValue("highlight_summary", value)} />}
      >
        <ReadableText value={content.highlight_summary} emptyText="暂无高潮设计。" />
      </EditableSection>

      <EditableSection
        eyebrow="排练"
        title="整体排练建议"
        isEditing={editingKey === "rehearsal_notes"}
        onToggleEdit={() => setEditingKey((current) => (current === "rehearsal_notes" ? null : "rehearsal_notes"))}
        editContent={<EditableList title="排练建议" values={content.rehearsal_notes} onChange={(values) => updateValue("rehearsal_notes", values)} />}
      >
        <ReadableList values={content.rehearsal_notes} />
      </EditableSection>

      <EditableSection
        eyebrow="复核"
        title="编导确认事项"
        isEditing={editingKey === "director_review_notes"}
        onToggleEdit={() => setEditingKey((current) => (current === "director_review_notes" ? null : "director_review_notes"))}
        editContent={<EditableList title="编导确认事项" values={content.director_review_notes} onChange={(values) => updateValue("director_review_notes", values)} />}
      >
        <ReadableList values={content.director_review_notes} />
      </EditableSection>

      {modelInfo ? <ModelInfoLine modelInfo={modelInfo} /> : null}
    </div>
  );
}

function FusionSegmentReadView({ values }: { values: MusicalFusionSegment[] }) {
  if (values.length === 0) {
    return <EmptyReadable text="暂无歌舞融合段落。" />;
  }
  return (
    <div className="readable-timeline">
      {values.map((segment, index) => (
        <article className="readable-record" key={`fusion-segment-read-${index}`}>
          <div className="readable-record-header">
            <div>
              <p className="readable-record-kicker">{segment.segment_no || `段落 ${index + 1}`}</p>
              <h4>{segment.music_position || "未标注音乐位置"}</h4>
            </div>
            <div className="readable-chip-row">
              {segment.is_highlight ? <Badge>高潮段落</Badge> : <Badge variant="outline">普通段落</Badge>}
              <Badge variant="secondary">{segment.emotion || "未标注情绪"}</Badge>
            </div>
          </div>
          <ReadableText value={segment.story_content} emptyText="暂无剧情内容。" />
          <div className="readable-two-column">
            <div>
              <h5>演唱安排</h5>
              <ReadableText value={segment.singing_mode} emptyText="暂无演唱方式。" />
              <ReadableList values={segment.singing_roles} emptyText="暂无演唱角色。" />
            </div>
            <div>
              <h5>舞蹈与队形</h5>
              <ReadableText value={segment.dance_form} emptyText="暂无舞蹈形式。" />
              <ReadableText value={segment.formation_suggestion} emptyText="暂无队形建议。" />
            </div>
          </div>
          <div className="readable-two-column">
            <div>
              <h5>唱跳关系</h5>
              <ReadableText value={segment.song_dance_relationship} emptyText="暂无唱跳关系说明。" />
              <ReadableText value={segment.transition_note} emptyText="暂无衔接说明。" />
            </div>
            <div>
              <h5>排练与安全</h5>
              <ReadableText value={segment.rehearsal_tip} emptyText="暂无排练提示。" />
              <ReadableText value={segment.safety_note} emptyText="暂无安全提醒。" />
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function FusionSegmentEditor({ values, onChange }: { values: MusicalFusionSegment[]; onChange: (values: MusicalFusionSegment[]) => void }) {
  function updateSegment(index: number, nextValue: MusicalFusionSegment) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }

  return (
    <FieldSet className="edit-section">
      <FieldLegend>歌舞融合结构段落</FieldLegend>
      {values.map((segment, index) => (
        <FieldGroup className="nested-editor" key={`fusion-segment-${index}`}>
          <div className="field-grid">
            <Field>
              <FieldLabel htmlFor={`fusion-segment-no-${index}`}>段落编号</FieldLabel>
              <Input id={`fusion-segment-no-${index}`} value={segment.segment_no} onChange={(event) => updateSegment(index, { ...segment, segment_no: event.target.value })} />
            </Field>
            <Field>
              <FieldLabel htmlFor={`fusion-music-position-${index}`}>音乐位置</FieldLabel>
              <Input id={`fusion-music-position-${index}`} value={segment.music_position} onChange={(event) => updateSegment(index, { ...segment, music_position: event.target.value })} />
            </Field>
          </div>
          <Field>
            <FieldLabel htmlFor={`fusion-story-${index}`}>剧情内容</FieldLabel>
            <Textarea id={`fusion-story-${index}`} rows={3} value={segment.story_content} onChange={(event) => updateSegment(index, { ...segment, story_content: event.target.value })} />
          </Field>
          <div className="field-grid">
            <Field>
              <FieldLabel htmlFor={`fusion-singing-mode-${index}`}>演唱方式</FieldLabel>
              <Input id={`fusion-singing-mode-${index}`} value={segment.singing_mode} onChange={(event) => updateSegment(index, { ...segment, singing_mode: event.target.value })} />
            </Field>
            <Field>
              <FieldLabel htmlFor={`fusion-emotion-${index}`}>情绪</FieldLabel>
              <Input id={`fusion-emotion-${index}`} value={segment.emotion} onChange={(event) => updateSegment(index, { ...segment, emotion: event.target.value })} />
            </Field>
          </div>
          <Field>
            <FieldLabel htmlFor={`fusion-roles-${index}`}>演唱角色</FieldLabel>
            <Textarea id={`fusion-roles-${index}`} rows={2} value={segment.singing_roles.join("、")} onChange={(event) => updateSegment(index, { ...segment, singing_roles: splitItems(event.target.value) })} />
          </Field>
          <Field>
            <FieldLabel htmlFor={`fusion-dance-${index}`}>舞蹈形式</FieldLabel>
            <Textarea id={`fusion-dance-${index}`} rows={2} value={segment.dance_form} onChange={(event) => updateSegment(index, { ...segment, dance_form: event.target.value })} />
          </Field>
          <Field>
            <FieldLabel htmlFor={`fusion-formation-${index}`}>队形建议</FieldLabel>
            <Textarea id={`fusion-formation-${index}`} rows={2} value={segment.formation_suggestion} onChange={(event) => updateSegment(index, { ...segment, formation_suggestion: event.target.value })} />
          </Field>
          <Field>
            <FieldLabel htmlFor={`fusion-relationship-${index}`}>唱跳关系</FieldLabel>
            <Textarea id={`fusion-relationship-${index}`} rows={3} value={segment.song_dance_relationship} onChange={(event) => updateSegment(index, { ...segment, song_dance_relationship: event.target.value })} />
          </Field>
          <Field>
            <FieldLabel htmlFor={`fusion-transition-${index}`}>衔接说明</FieldLabel>
            <Textarea id={`fusion-transition-${index}`} rows={2} value={segment.transition_note} onChange={(event) => updateSegment(index, { ...segment, transition_note: event.target.value })} />
          </Field>
          <Field>
            <FieldLabel htmlFor={`fusion-rehearsal-${index}`}>排练提示</FieldLabel>
            <Textarea id={`fusion-rehearsal-${index}`} rows={2} value={segment.rehearsal_tip} onChange={(event) => updateSegment(index, { ...segment, rehearsal_tip: event.target.value })} />
          </Field>
          <Field>
            <FieldLabel htmlFor={`fusion-safety-${index}`}>安全提醒</FieldLabel>
            <Textarea id={`fusion-safety-${index}`} rows={2} value={segment.safety_note} onChange={(event) => updateSegment(index, { ...segment, safety_note: event.target.value })} />
          </Field>
          <Field>
            <FieldLabel id={`fusion-highlight-label-${index}`}>段落级别</FieldLabel>
            <ToggleGroup
              type="single"
              variant="outline"
              value={segment.is_highlight ? "highlight" : "normal"}
              onValueChange={(value) => {
                if (value) {
                  updateSegment(index, { ...segment, is_highlight: value === "highlight" });
                }
              }}
              aria-labelledby={`fusion-highlight-label-${index}`}
            >
              <ToggleGroupItem value="normal">普通段落</ToggleGroupItem>
              <ToggleGroupItem value="highlight">高潮段落</ToggleGroupItem>
            </ToggleGroup>
          </Field>
        </FieldGroup>
      ))}
    </FieldSet>
  );
}

function EditableList({ title, values, onChange }: { title: string; values: string[]; onChange: (values: string[]) => void }) {
  return (
    <FieldSet className="edit-section compact-section">
      <FieldLegend>{title}</FieldLegend>
      <FieldGroup>
        {values.map((value, index) => (
          <Field key={`${title}-${index}`}>
            <FieldLabel className="sr-only" htmlFor={`${title}-${index}`}>
              {title} {index + 1}
            </FieldLabel>
            <Textarea id={`${title}-${index}`} rows={2} value={value} onChange={(event) => onChange(values.map((item, itemIndex) => (itemIndex === index ? event.target.value : item)))} />
          </Field>
        ))}
      </FieldGroup>
    </FieldSet>
  );
}

function splitItems(value: string) {
  // 兼容老师从文档中粘贴的顿号、逗号和换行分隔角色列表。
  return value
    .split(/[、，,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}
