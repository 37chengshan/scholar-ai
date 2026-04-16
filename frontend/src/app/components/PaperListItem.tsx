import { FileText, MoreHorizontal, BookOpen, Layers, Network, StickyNote, MessageSquare } from "lucide-react";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";

interface PaperListItemProps {
  id: string;
  title: string;
  authors: string;
  year: string;
  venue: string;
  chunkCount: number;
  parseStatus: "pending" | "processing" | "completed" | "failed";
  entityCount: number;
  onRead: () => void;
  onNotes: () => void;
  onQuery?: (paperId: string) => void;
}

const statusConfig: Record<string, { label: string; className: string }> = {
  pending: {
    label: "待解析",
    className: "status-badge status-badge--pending",
  },
  processing: {
    label: "解析中",
    className: "status-badge status-badge--processing",
  },
  completed: {
    label: "已完成",
    className: "status-badge status-badge--completed",
  },
  failed: {
    label: "失败",
    className: "status-badge status-badge--failed",
  },
};

export function PaperListItem({
  id: _id,
  title,
  authors,
  year,
  venue,
  chunkCount,
  parseStatus,
  entityCount,
  onRead,
  onNotes,
  onQuery,
}: PaperListItemProps) {
  const status = statusConfig[parseStatus];

  return (
    <Card className="group border border-border/50 bg-card hover:border-primary/30 transition-all duration-200">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-start gap-2">
              <FileText className="h-4 w-4 text-muted-foreground mt-1 flex-shrink-0" />
              <div className="min-w-0">
                <h4 className="font-semibold text-foreground leading-tight group-hover:text-primary transition-colors truncate">
                  {title}
                </h4>
                <p className="text-sm text-muted-foreground mt-1">
                  {authors} · {venue} {year}
                </p>
              </div>
            </div>

            <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
              {/* Chunk count with lucide icon */}
              <span className="stat-item">
                <Layers className="stat-item__icon" />
                <span className="stat-item__value">{chunkCount}</span>
                <span>切片</span>
              </span>

              {/* Status badge with colored dot */}
              <span className={status.className}>
                <span className="status-badge__dot" />
                {status.label}
              </span>

              {/* Entity count with lucide icon */}
              {entityCount > 0 && (
                <span className="stat-item">
                  <Network className="stat-item__icon" />
                  <span className="stat-item__value">{entityCount}</span>
                  <span>实体</span>
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <Button size="sm" variant="outline" onClick={onRead} className="gap-1.5 rounded-full">
              <BookOpen className="h-3.5 w-3.5" />
              阅读
            </Button>
            {onQuery && (
              <Button size="sm" variant="default" onClick={() => onQuery(_id)} className="gap-1.5 rounded-full">
                <MessageSquare className="h-3.5 w-3.5" />
                提问
              </Button>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="更多操作">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={onRead}>
                  <BookOpen className="mr-2 h-4 w-4" />
                  阅读
                </DropdownMenuItem>
                <DropdownMenuItem onClick={onNotes}>
                  <StickyNote className="mr-2 h-4 w-4" />
                  笔记
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="destructive">
                  删除
                </DropdownMenuItem>
                <DropdownMenuItem>
                  重新解析
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
