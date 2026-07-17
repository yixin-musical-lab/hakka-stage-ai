import type { ReactNode } from "react";
import {
  ClipboardCheck,
  Clock,
  Cpu,
  Download,
  Eye,
  FileText,
  Layers,
  MessageSquare,
  Music,
  Trash2,
  Users,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router";
import { Button } from "../ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "../ui/card";
import { formatDateTime } from "../../lib/format";

export type LibraryRecordKind = "interaction" | "script" | "song" | "fusion" | "role" | "review";

type LibraryRecordCardProps = {
  kind: LibraryRecordKind;
  title: string;
  badges: ReactNode;
  summaryLabel: string;
  summary: ReactNode;
  updatedAt: string;
  provider: string | null;
  model: string | null;
  reasoningLevel: string | null;
  viewTo: string;
  viewLabel: string;
  deleting: boolean;
  onDownload: () => void;
  onDelete: () => void;
};

type LibraryKindConfig = {
  label: string;
  icon: LucideIcon;
};

// 六类资料共用卡片骨架，但保留各自的图标和色彩标识，方便老师快速辨认当前业务阶段。
const libraryKindConfig: Record<LibraryRecordKind, LibraryKindConfig> = {
  interaction: { label: "课堂执行", icon: MessageSquare },
  script: { label: "剧本创编", icon: FileText },
  song: { label: "唱段适配", icon: Music },
  fusion: { label: "歌舞编排", icon: Layers },
  role: { label: "角色训练", icon: Users },
  review: { label: "现场复盘", icon: ClipboardCheck },
};

export function LibraryRecordCard({
  kind,
  title,
  badges,
  summaryLabel,
  summary,
  updatedAt,
  provider,
  model,
  reasoningLevel,
  viewTo,
  viewLabel,
  deleting,
  onDownload,
  onDelete,
}: LibraryRecordCardProps) {
  const { icon: KindIcon, label: kindLabel } = libraryKindConfig[kind];
  const modelLabel = model
    ? `${provider ?? "model"} / ${model}${reasoningLevel ? ` / ${reasoningLevel}` : ""}`
    : null;

  return (
    <Card asChild className="library-card" data-library-kind={kind}>
      <article>
        <CardHeader>
          <div className="library-card-identity">
            <span className="library-card-marker" aria-hidden="true">
              <KindIcon />
            </span>
            <div className="library-card-identity-copy">
              <span className="library-card-kicker">{kindLabel}</span>
              <div className="readable-chip-row">{badges}</div>
            </div>
          </div>
          <CardTitle>
            <h2>{title}</h2>
          </CardTitle>
        </CardHeader>

        <CardContent>
          <div className="library-card-summary">
            <span>{summaryLabel}</span>
            <p>{summary}</p>
          </div>
          <div className="library-card-meta">
            <span>
              <Clock aria-hidden="true" />
              更新于 {formatDateTime(updatedAt)}
            </span>
            {modelLabel ? (
              <span>
                <Cpu aria-hidden="true" />
                {modelLabel}
              </span>
            ) : null}
          </div>
        </CardContent>

        <CardFooter className="library-record-actions">
          <Button asChild size="sm">
            <Link to={viewTo}>
              <Eye data-icon="inline-start" />
              {viewLabel}
            </Link>
          </Button>
          <Button size="sm" variant="outline" type="button" onClick={onDownload}>
            <Download data-icon="inline-start" />
            导出 Markdown
          </Button>
          <Button size="sm" variant="destructive" type="button" disabled={deleting} onClick={onDelete}>
            <Trash2 data-icon="inline-start" />
            {deleting ? "删除中" : "删除"}
          </Button>
        </CardFooter>
      </article>
    </Card>
  );
}
