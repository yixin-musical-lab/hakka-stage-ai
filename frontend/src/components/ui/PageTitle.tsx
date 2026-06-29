import type { ReactNode } from "react";
import { Card } from "@/components/ui/card";

export function PageTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <Card asChild className="page-title">
      <section>
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p className="intro">{description}</p>
        </div>
        {action ? <div className="page-action">{action}</div> : null}
      </section>
    </Card>
  );
}
