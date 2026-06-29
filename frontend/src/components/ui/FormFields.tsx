import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export function TextField({
  label,
  value,
  required = true,
  onChange,
}: {
  label: string;
  value: string;
  required?: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <Field className="field">
      <FieldLabel>{label}</FieldLabel>
      <Input value={value} onChange={(event) => onChange(event.target.value)} required={required} />
    </Field>
  );
}

export function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <Field className="field">
      <FieldLabel>{label}</FieldLabel>
      <Input min={1} type="number" value={value} onChange={(event) => onChange(Number(event.target.value))} required />
    </Field>
  );
}

export function TextareaField({
  label,
  value,
  required = true,
  rows = 4,
  onChange,
}: {
  label: string;
  value: string;
  required?: boolean;
  rows?: number;
  onChange: (value: string) => void;
}) {
  return (
    <Field className="field">
      <FieldLabel>{label}</FieldLabel>
      <Textarea value={value} onChange={(event) => onChange(event.target.value)} required={required} rows={rows} />
    </Field>
  );
}
