import { MoreHorizontal, ArrowRight, Download, Pencil, Copy, Trash2, Network } from "lucide-react";
import { Card, CardContent, CardFooter, CardHeader } from "../components/ui/card";
import { Button } from "../components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import { Badge } from "../components/ui/badge";

interface KnowledgeBaseCardProps {
  id: string;
  name: string;
  description: string;
  paperCount: number;
  chunkCount: number;
  entityCount: number;
  updatedAt: string;
  category?: string;
  onEnter: () => void;
  onImport: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

const categoryIcons: Record<string, string> = {
  "人工智能": "🤖",
  "自然语言处理": "📝",
  "计算机视觉": "👁️",
  "机器学习": "📊",
  "其他": "📚",
};

function formatCount(count: number): string {
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}k`;
  }
  return String(count);
}

export function KnowledgeBaseCard({
  id,
  name,
  description,
  paperCount,
  chunkCount,
  entityCount,
  updatedAt,
  category,
  onEnter,
  onImport,
  onEdit,
  onDelete,
}: KnowledgeBaseCardProps) {
  const icon = category ? (categoryIcons[category] || "🧠") : "🧠";

  return (
    <Card
      data-kb-id={id}
      className="group relative flex flex-col gap-0 border border-border/50 bg-card transition-all duration-300 hover:shadow-lg hover:border-primary/30 cursor-pointer"
      style={{
        boxShadow: "var(--card-shadow, 0 1px 3px rgba(0,0,0,0.06))",
      }}
      onClick={(e) => {
        // Don't navigate if clicking action buttons
        if ((e.target as HTMLElement).closest("button")) return;
        onEnter();
      }}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-start gap-3 min-w-0">
            <span className="text-2xl flex-shrink-0 mt-0.5">{icon}</span>
            <div className="min-w-0">
              <h3 className="text-lg font-semibold leading-tight text-foreground group-hover:text-primary transition-colors truncate">
                {name}
              </h3>
              {category && (
                <Badge variant="secondary" className="mt-1.5 text-xs">
                  {category}
                </Badge>
              )}
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 flex-shrink-0"
                onClick={(e) => e.stopPropagation()}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onEdit(); }}>
                <Pencil className="mr-2 h-4 w-4" />
                编辑
              </DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); }}>
                <Copy className="mr-2 h-4 w-4" />
                复制
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); }}>
                <Network className="mr-2 h-4 w-4" />
                构建图谱
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                variant="destructive"
                onClick={(e) => { e.stopPropagation(); onDelete(); }}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                删除
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>

      <CardContent className="pb-3 pt-0">
        <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
          {description}
        </p>

        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            📄 {paperCount} 篇论文
          </span>
          <span className="flex items-center gap-1">
            🔍 {formatCount(chunkCount)} 切片
          </span>
          {entityCount > 0 ? (
            <span className="flex items-center gap-1">
              🕸️ {formatCount(entityCount)} 实体
            </span>
          ) : (
            <span className="flex items-center gap-1 text-muted-foreground/60">
              🕸️ 未构建图谱
            </span>
          )}
        </div>

        <p className="mt-3 text-xs text-muted-foreground/60">
          {updatedAt} 更新
        </p>
      </CardContent>

      <CardFooter className="pt-0 pb-4 px-6 flex items-center gap-2 border-t border-border/30">
        <Button
          size="sm"
          onClick={(e) => { e.stopPropagation(); onEnter(); }}
          className="flex-1"
        >
          <ArrowRight className="mr-1 h-3.5 w-3.5" />
          进入
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={(e) => { e.stopPropagation(); onImport(); }}
        >
          <Download className="mr-1 h-3.5 w-3.5" />
          导入
        </Button>
      </CardFooter>
    </Card>
  );
}
