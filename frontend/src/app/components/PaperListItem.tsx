import { FileText, MoreHorizontal, BookOpen, StickyNote } from "lucide-react";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
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
}

const statusConfig: Record<
  string,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline"; color: string }
> = {
  pending: {
    label: "待解析",
    variant: "secondary",
    color: "bg-gray-100 text-gray-600",
  },
  processing: {
    label: "解析中",
    variant: "outline",
    color: "bg-yellow-50 text-yellow-700 border-yellow-200",
  },
  completed: {
    label: "已完成",
    variant: "default",
    color: "bg-green-50 text-green-700 border-green-200",
  },
  failed: {
    label: "失败",
    variant: "destructive",
    color: "bg-red-50 text-red-700 border-red-200",
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
              <span className="flex items-center gap-1">
                📊 {chunkCount} 切片
              </span>
              <Badge
                variant={status.variant as any}
                className={`text-xs ${status.color}`}
              >
                {parseStatus === "processing" && (
                  <span className="mr-1 inline-block h-2 w-2 animate-pulse rounded-full bg-yellow-500" />
                )}
                {status.label}
              </Badge>
              {entityCount > 0 && (
                <span className="flex items-center gap-1">
                  🕸️ {entityCount} 实体
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <Button size="sm" variant="outline" onClick={onRead} className="gap-1.5">
              <BookOpen className="h-3.5 w-3.5" />
              阅读
            </Button>
            <Button size="sm" variant="ghost" onClick={onNotes} className="gap-1.5">
              <StickyNote className="h-3.5 w-3.5" />
              笔记
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
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
