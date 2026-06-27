import { Link } from "react-router";

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
      <span className={status === "已接入" ? "module-status live" : "module-status"}>{status}</span>
      <h3>{title}</h3>
      <p>{description}</p>
    </>
  );

  if (to) {
    return (
      <Link className="module-tile interactive" to={to}>
        {content}
      </Link>
    );
  }

  return <article className="module-tile">{content}</article>;
}
