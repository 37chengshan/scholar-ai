import { Loader2, MessageSquare } from 'lucide-react';
import type { KnowledgeRunSummary } from '@/features/kb/types/workspace';

interface KnowledgeRunHistoryPanelProps {
  runs: KnowledgeRunSummary[];
  loading: boolean;
  onOpenRun: (runId: string) => void;
}

export function KnowledgeRunHistoryPanel({ runs, loading, onOpenRun }: KnowledgeRunHistoryPanelProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="border border-border/80 bg-paper-1 p-8 text-center font-medium text-muted-foreground">
        暂无可用 Run 历史。
      </div>
    );
  }

  return (
    <div className="space-y-3 max-w-4xl">
      {runs.map((run) => (
        <button
          key={run.id}
          type="button"
          onClick={() => onOpenRun(run.id)}
          className="w-full border border-border/80 bg-paper-1 p-4 text-left transition-colors hover:border-primary/50 hover:bg-primary/[0.03]"
        >
          <div className="flex items-center gap-3">
            <MessageSquare className="w-4 h-4 text-primary" />
            <div className="truncate font-semibold text-foreground">{run.title}</div>
          </div>
          <div className="mt-2 text-xs text-muted-foreground">run_id: {run.id}</div>
          {run.updatedAt ? <div className="text-xs text-muted-foreground/70">updated: {run.updatedAt}</div> : null}
        </button>
      ))}
    </div>
  );
}
