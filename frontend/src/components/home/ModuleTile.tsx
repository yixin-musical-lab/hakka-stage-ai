import { Link } from "react-router";
import { Badge } from "../ui/badge";
import { Card } from "../ui/card";

export function ModuleTile({
  title,
  status,
  description,
  to,
}: {
  title: string;
  status: string;
  description: string;
  to?: string;
}) {
  const content = (
    <>
      <Badge variant={status === "已接入" ? "default" : "secondary"}>{status}</Badge>
      <h3>{title}</h3>
      <p>{description}</p>
    </>
  );

  if (to) {
    return (
      <Card asChild className="module-tile interactive">
        <Link to={to}>{content}</Link>
      </Card>
    );
  }

  return (
    <Card asChild className="module-tile">
      <article>{content}</article>
    </Card>
  );
}
