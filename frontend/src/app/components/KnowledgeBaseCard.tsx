import { MoreHorizontal, Download, Pencil, Copy, Trash2, Network, Brain, FileText, Eye, TrendingUp, BookOpen, Layers } from "lucide-react";
import { Card, CardContent, CardHeader } from "../components/ui/card";
import { Button } from "../components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";

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

const categoryConfig: Record<string, { icon: typeof Brain; accent: string; label: string }> = {
  "人工智能": { icon: Brain, accent: "card-accent--ai", label: "AI" },
  "自然语言处理": { icon: FileText, accent: "card-accent--nlp", label: "NLP" },
  "计算机视觉": { icon: Eye, accent: "card-accent--cv", label: "CV" },
  "机器学习": { icon: TrendingUp, accent: "card-accent--ml", label: "ML" },
  "其他": { icon: BookOpen, accent: "card-accent--other", label: "Other" },
};

function formatCount(count: number): string {
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}k`;
  }
  return String(count);
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const month = date.getMonth() + 1;
  const day = date.getDate();
  return `${month}月${day}日`;
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
  const config = category ? (categoryConfig[category] || categoryConfig["其他"]) : categoryConfig["其他"];
  const Icon = config.icon;

  return (
    <Card
      data-kb-id={id}
      className="group relative flex flex-col bg-paper-1 border border-border/50 rounded-xl overflow-hidden transition-all duration-300 hover:shadow-paper-hover hover:-translate-y-1 hover:border-primary/20 cursor-pointer"
      onClick={(e) => {
        if ((e.target as HTMLElement).closest("button")) return;
        onEnter();
      }}
      role="link"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') onEnter(); }}
    >
      {/* Top accent bar */}
      <div className={`card-accent ${config.accent}`} />

      <CardHeader className="pb-2 pt-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            {/* Category icon — circular background */}
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-muted/60 flex items-center justify-center group-hover:bg-primary/10 transition-colors">
              <Icon className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
            <div className="min-w-0">
              <h3 className="font-serif text-lg font-semibold leading-tight text-foreground group-hover:text-primary transition-colors truncate">
                {name}
              </h3>
              {category && (
                <span className="category-chip mt-1.5 inline-flex">
                  {config.label} · {category}
                </span>
              )}
            </div>
          </div>

          {/* More actions — hidden until hover */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={(e) => e.stopPropagation()}
                aria-label="更多操作"
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onEdit(); }}>
                <Pencil className="mr-2 h-4 w-4" />
                编辑
              </DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onImport(); }}>
                <Download className="mr-2 h-4 w-4" />
                添加论文
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

      <CardContent className="pb-4 pt-0">
        <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
          {description}
        </p>
      </CardContent>

      {/* Bottom divider + stats */}
      <div className="px-6 pb-4 pt-0 border-t border-rule/50 mt-auto">
        <div className="flex items-center gap-x-4 gap-y-1.5 py-2.5 text-xs">
          <span className="stat-item">
            <FileText className="stat-item__icon" />
            <span className="stat-item__value">{paperCount}</span>
            <span>论文</span>
          </span>
          <span className="stat-item">
            <Layers className="stat-item__icon" />
            <span className="stat-item__value">{formatCount(chunkCount)}</span>
            <span>切片</span>
          </span>
          {entityCount > 0 ? (
            <span className="stat-item">
              <Network className="stat-item__icon" />
              <span className="stat-item__value">{formatCount(entityCount)}</span>
              <span>实体</span>
            </span>
          ) : (
            <span className="stat-item text-muted-foreground/50">
              <Network className="stat-item__icon" />
              <span>未构建图谱</span>
            </span>
          )}
        </div>
        <p className="text-xs text-muted-foreground/50">
          {formatDate(updatedAt)} 更新
        </p>
      </div>
    </Card>
  );
}
