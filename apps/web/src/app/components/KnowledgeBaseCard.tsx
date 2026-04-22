import { MoreHorizontal, Download, Pencil, Trash2, FileText, Eye, TrendingUp, BookOpen, Layers, Brain } from "lucide-react";
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

const categoryConfig: Record<string, { icon: typeof Brain; label: string }> = {
  "人工智能": { icon: Brain, label: "AI" },
  "自然语言处理": { icon: FileText, label: "NLP" },
  "计算机视觉": { icon: Eye, label: "CV" },
  "机器学习": { icon: TrendingUp, label: "ML" },
  "其他": { icon: BookOpen, label: "Other" },
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
      className="group relative flex flex-col bg-paper border border-ink/10 hover:border-ink/30 transition-colors duration-300 rounded-none overflow-hidden cursor-pointer"
      onClick={(e) => {
        if ((e.target as HTMLElement).closest("button")) return;
        onEnter();
      }}
      role="link"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onEnter(); } }}
    >
      <div className="absolute left-0 top-0 h-full w-[3px] bg-transparent group-hover:bg-primary/70 transition-colors" />

      <CardHeader className="pb-2 pt-4 pl-5 pr-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <div className="flex-shrink-0 w-9 h-9 border border-border/70 bg-paper-2 flex items-center justify-center group-hover:border-primary/40 transition-colors">
              <Icon className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
            <div className="min-w-0">
              <h3 className="font-serif text-base font-semibold leading-tight text-foreground group-hover:text-primary transition-colors truncate">
                {name}
              </h3>
              {category && (
                <span className="mt-1.5 inline-flex border border-border/70 bg-paper-2 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
                  {config.label} · {category}
                </span>
              )}
            </div>
          </div>

          {/* More actions — visible on hover */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-muted"
                onClick={(e) => e.stopPropagation()}
                aria-label="更多操作"
              >
                <MoreHorizontal className="h-4 w-4 text-muted-foreground group-hover:text-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-[160px] bg-paper-1 border border-border shadow-none rounded-none">
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onEdit(); }} className="flex items-center gap-2 px-3 py-2 text-xs font-bold uppercase tracking-[0.12em] cursor-pointer outline-none hover:bg-muted hover:text-primary">
                <Pencil className="h-4 w-4" /> 编辑信息
              </DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onImport(); }} className="flex items-center gap-2 px-3 py-2 text-xs font-bold uppercase tracking-[0.12em] cursor-pointer outline-none hover:bg-muted hover:text-primary">
                <Download className="h-4 w-4" /> 导入论文
              </DropdownMenuItem>
              <DropdownMenuSeparator className="h-px bg-border" />
              <DropdownMenuItem
                variant="destructive"
                onClick={(e) => { e.stopPropagation(); onDelete(); }}
                className="flex items-center gap-2 px-3 py-2 text-xs font-bold uppercase tracking-[0.12em] cursor-pointer outline-none hover:bg-red-50 text-red-600"
              >
                <Trash2 className="h-4 w-4" /> 删除知识库
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>

      <CardContent className="pb-3 pt-0 pl-5 pr-4">
        <p className="text-sm text-muted-foreground font-medium line-clamp-2 leading-relaxed">
          {description}
        </p>
      </CardContent>

      {/* Bottom divider + stats */}
      <div className="px-5 pb-3 pt-3 border-t border-ink/10 mt-auto bg-muted/5 group-hover:bg-muted/10 transition-colors duration-300">
        <div className="flex items-center justify-between text-xs text-ink/70">
          <div className="flex items-center gap-x-4 gap-y-1.5 font-sans tracking-wide">
            <span className="flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 opacity-60" />
              <span className="font-semibold text-ink">{paperCount}</span>
            </span>
            <span className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 opacity-60" />
              <span className="font-semibold text-ink">{formatCount(chunkCount)}</span>
            </span>
          </div>
          <span className="font-mono text-[10px] tracking-widest uppercase opacity-50">
            {formatDate(updatedAt)}
          </span>
        </div>
      </div>
    </Card>
  );
}
