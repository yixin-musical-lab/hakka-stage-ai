import { useId } from "react";
import { Field, FieldLabel, FieldLegend, FieldSet } from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { LlmOptionsResponse } from "@/types";

type LlmProviderId = LlmOptionsResponse["providers"][number]["id"];
type ReasoningLevelId = LlmOptionsResponse["reasoning_levels"][number]["id"];

export function LlmSettings({
  provider,
  model,
  reasoningLevel,
  llmOptions,
  selectedModelOptions,
  onProviderChange,
  onModelChange,
  onReasoningLevelChange,
}: {
  provider: LlmProviderId;
  model: string;
  reasoningLevel: ReasoningLevelId;
  llmOptions: LlmOptionsResponse | null;
  selectedModelOptions: LlmOptionsResponse["providers"][number]["models"];
  onProviderChange: (providerId: LlmProviderId) => void;
  onModelChange: (modelId: string) => void;
  onReasoningLevelChange: (reasoningLevel: ReasoningLevelId) => void;
}) {
  const providerId = useId();
  const modelId = useId();
  const reasoningLabelId = useId();

  return (
    <FieldSet className="edit-section model-picker">
      <FieldLegend>模型设置</FieldLegend>
      <div className="field-grid">
        <Field className="field">
          <FieldLabel htmlFor={providerId}>模型供应商</FieldLabel>
          <Select value={provider} onValueChange={(value) => onProviderChange(value as LlmProviderId)}>
            <SelectTrigger id={providerId} className="w-full bg-card">
              <SelectValue placeholder="选择模型供应商" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {(llmOptions?.providers ?? []).map((item) => (
                  <SelectItem key={item.id} value={item.id} disabled={!item.configured}>
                    {item.label}
                    {item.configured ? "" : "（未配置密钥）"}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </Field>

        <Field className="field">
          <FieldLabel htmlFor={modelId}>模型</FieldLabel>
          <Select value={model} onValueChange={onModelChange}>
            <SelectTrigger id={modelId} className="w-full bg-card">
              <SelectValue placeholder="选择模型" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {selectedModelOptions.map((item) => (
                  <SelectItem key={item.id} value={item.id}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </Field>
      </div>

      <Field className="field">
        <FieldLabel id={reasoningLabelId}>推理强度</FieldLabel>
        <ToggleGroup
          aria-labelledby={reasoningLabelId}
          className="grid w-full grid-cols-3 rounded-lg border border-border bg-secondary p-1"
          type="single"
          value={reasoningLevel}
          onValueChange={(value) => {
            // Radix ToggleGroup 在再次点击当前项时会回传空值，这里保留当前选择。
            if (value) {
              onReasoningLevelChange(value as ReasoningLevelId);
            }
          }}
          variant="outline"
        >
          {(llmOptions?.reasoning_levels ?? []).map((level) => (
            <ToggleGroupItem className="h-9 min-w-0 font-black data-[state=on]:bg-card" key={level.id} title={level.description} value={level.id}>
              {level.label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </Field>
    </FieldSet>
  );
}
