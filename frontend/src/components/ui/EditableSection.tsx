import type { ReactNode } from "react";
import { Button } from "./button";

type EditableSectionProps = {
  eyebrow?: string;
  title: string;
  summary?: string;
  isEditing: boolean;
  onToggleEdit: () => void;
  children: ReactNode;
  editContent: ReactNode;
};

// 详情页统一使用“阅读态优先”的区块容器：
// 默认展示排版后的内容，只有点击编辑时才把当前模块切换成表单。
export function EditableSection({
  eyebrow,
  title,
  summary,
  isEditing,
  onToggleEdit,
  children,
  editContent,
}: EditableSectionProps) {
  return (
    <section className={`readable-section${isEditing ? " is-editing" : ""}`}>
      <header className="readable-section-header">
        <div>
          {eyebrow ? <p className="readable-section-eyebrow">{eyebrow}</p> : null}
          <h3>{title}</h3>
          {summary ? <p className="readable-section-summary">{summary}</p> : null}
        </div>
        <Button type="button" variant={isEditing ? "secondary" : "outline"} size="sm" onClick={onToggleEdit}>
          {isEditing ? "完成编辑" : "编辑"}
        </Button>
      </header>
      <div className={isEditing ? "readable-section-edit" : "readable-section-content"}>{isEditing ? editContent : children}</div>
    </section>
  );
}

export function EmptyReadable({ text = "暂无内容。" }: { text?: string }) {
  return <p className="readable-empty">{text}</p>;
}

export function ReadableText({ value, emptyText = "暂无内容。" }: { value?: string; emptyText?: string }) {
  return value?.trim() ? <p className="readable-text">{value}</p> : <EmptyReadable text={emptyText} />;
}

export function ReadableList({ values, emptyText = "暂无内容。" }: { values: string[]; emptyText?: string }) {
  const visibleValues = values.filter((value) => value.trim());
  if (visibleValues.length === 0) {
    return <EmptyReadable text={emptyText} />;
  }
  return (
    <ul className="readable-list">
      {visibleValues.map((value, index) => (
        <li key={`${value}-${index}`}>{value}</li>
      ))}
    </ul>
  );
}

export function ModelInfoLine({
  modelInfo,
  label = "模型",
}: {
  modelInfo: Record<string, unknown>;
  label?: string;
}) {
  return (
    <p className="model-info">
      {label}：{String(modelInfo.provider)} / {String(modelInfo.model)} / {String(modelInfo.prompt_version)}
      {modelInfo.reasoning_level ? ` / ${String(modelInfo.reasoning_level)}` : ""}
    </p>
  );
}
