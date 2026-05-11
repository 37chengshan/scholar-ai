import { Link } from 'react-router';

import { Badge } from '@/app/components/ui/badge';
import { Button } from '@/app/components/ui/button';
import { Loader2 } from 'lucide-react';

interface NotesHeaderProps {
  catalogLoading: boolean;
  paperIdFilter: string | null;
  paperTitle: string | null;
  onClearPaperFilter: () => void;
}

export function NotesHeader({
  catalogLoading,
  paperIdFilter,
  paperTitle,
  onClearPaperFilter,
}: NotesHeaderProps) {
  return (
    <div className="magazine-toolbar sticky top-0 z-10 border-b border-border/50 bg-background/95 backdrop-blur-md">
      <div className="flex items-end justify-between gap-4 px-6 py-5">
        <div>
          <h1 className="editorial-display font-serif text-3xl font-semibold tracking-tight text-foreground">笔记</h1>
          <p className="mt-1 text-[11px] font-medium text-muted-foreground">证据沉淀与写作</p>
        </div>
        <div className="flex items-center gap-2">
          {catalogLoading ? (
            <Badge variant="outline" className="text-[9px] font-bold uppercase tracking-wider">
              <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              同步目录中
            </Badge>
          ) : null}
        </div>
      </div>
      {paperIdFilter ? (
        <div className="flex flex-wrap items-center gap-2 px-6 pb-4">
          <span className="text-xs text-muted-foreground">
            当前筛选：论文《{paperTitle || paperIdFilter}》
          </span>
          <Button asChild size="sm" variant="outline" className="h-7">
            <Link to={`/read/${paperIdFilter}?source=notes`}>回到阅读页</Link>
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-7"
            onClick={onClearPaperFilter}
          >
            清除筛选
          </Button>
        </div>
      ) : null}
    </div>
  );
}
