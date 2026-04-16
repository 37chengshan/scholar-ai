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
      className="group relative flex flex-col bg-white border-2 border-zinc-900 hover:border-primary transition-all shadow-[8px_8px_0px_0px_rgba(24,24,27,1)] hover:shadow-[12px_12px_0px_0px_rgba(211,84,0,1)] rounded-none overflow-hidden cursor-pointer"
      onClick={(e) => {
        if ((e.target as HTMLElement).closest("button")) return;
        onEnter();
      }}
      role="link"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onEnter(); } }}
    >
      {/* Top accent bar */}
      <div className={`card-accent ${config.accent}`} />

      <CardHeader className="pb-2 pt-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            {/* Category icon — circular background */}
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-zinc-100 flex items-center justify-center group-hover:bg-orange-100 transition-colors">
              <Icon className="h-5 w-5 text-zinc-600 group-hover:text-primary transition-colors" />
            </div>
            <div className="min-w-0">
              <h3 className="font-serif text-lg font-semibold leading-tight text-zinc-900 group-hover:text-primary transition-colors truncate">
                {name}
              </h3>
              {category && (
                <span className="inline-flex px-2 py-1 bg-zinc-100 text-zinc-600 text-xs font-bold uppercase tracking-wider border border-zinc-300 mt-1.5">
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
                className="h-8 w-8 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-orange-100"
                onClick={(e) => e.stopPropagation()}
                aria-label="更多操作"
              >
                <MoreHorizontal className="h-4 w-4 text-zinc-400 group-hover:text-zinc-900" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-[160px] bg-white border-2 border-zinc-900 shadow-[4px_4px_0px_0px_rgba(24,24,27,1)]">
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onEdit(); }} className="flex items-center gap-2 px-3 py-2 text-sm font-bold uppercase cursor-pointer outline-none hover:bg-orange-100 hover:text-primary">
                <Pencil className="h-4 w-4" /> 编辑
              </DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onImport(); }} className="flex items-center gap-2 px-3 py-2 text-sm font-bold uppercase cursor-pointer outline-none hover:bg-orange-100 hover:text-primary">
                <Download className="h-4 w-4" /> 导入论文
              </DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); }} className="flex items-center gap-2 px-3 py-2 text-sm font-bold uppercase cursor-pointer outline-none hover:bg-orange-100 hover:text-primary">
                <Copy className="h-4 w-4" /> 复制
              </DropdownMenuItem>
              <DropdownMenuSeparator className="h-px bg-zinc-200" />
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); }} className="flex items-center gap-2 px-3 py-2 text-sm font-bold uppercase cursor-pointer outline-none hover:bg-orange-100 hover:text-primary">
                <Network className="h-4 w-4" /> 构建图谱
              </DropdownMenuItem>
              <DropdownMenuSeparator className="h-px bg-zinc-200" />
              <DropdownMenuItem
                variant="destructive"
                onClick={(e) => { e.stopPropagation(); onDelete(); }}
                className="flex items-center gap-2 px-3 py-2 text-sm font-bold uppercase cursor-pointer outline-none hover:bg-red-50 text-red-600"
              >
                <Trash2 className="h-4 w-4" /> 删除
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>

      <CardContent className="pb-4 pt-0">
        <p className="text-sm text-zinc-600 font-medium line-clamp-2 leading-relaxed">
          {description}
        </p>
      </CardContent>

      {/* Bottom divider + stats */}
      <div className="px-6 pb-4 pt-0 border-t-2 border-zinc-900 mt-auto">
        <div className="flex items-center gap-x-4 gap-y-1.5 py-2.5 text-xs">
          <span className="flex items-center gap-1.5 text-zinc-600">
            <FileText className="w-3.5 h-3.5 opacity-50" />
            <span className="font-bold text-zinc-900">{paperCount}</span>
            <span>论文</span>
          </span>
          <span className="flex items-center gap-1.5 text-zinc-600">
            <Layers className="w-3.5 h-3.5 opacity-50" />
            <span className="font-bold text-zinc-900">{formatCount(chunkCount)}</span>
            <span>切片</span>
          </span>
          {entityCount > 0 ? (
            <span className="flex items-center gap-1.5 text-zinc-600">
              <Network className="w-3.5 h-3.5 opacity-50" />
              <span className="font-bold text-zinc-900">{formatCount(entityCount)}</span>
              <span>实体</span>
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-zinc-400">
              <Network className="w-3.5 h-3.5" />
              <span>未构建图谱</span>
            </span>
          )}
        </div>
        <p className="text-xs text-zinc-400 font-medium">
          {formatDate(updatedAt)} 更新
        </p>
      </div>
    </Card>
  );
}