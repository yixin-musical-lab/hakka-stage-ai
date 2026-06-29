import { Card } from "@/components/ui/card";

export function StatusItem({ label, value }: { label: string; value: string }) {
  return (
    <Card className="status-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </Card>
  );
}
