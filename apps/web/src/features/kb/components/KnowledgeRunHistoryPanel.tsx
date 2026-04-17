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
      <div className="bg-white border-2 border-zinc-900 p-8 text-center text-zinc-600 font-medium shadow-[8px_8px_0px_0px_rgba(24,24,27,1)]">
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
          className="w-full text-left bg-white border-2 border-zinc-200 hover:border-primary transition-colors p-4 shadow-[4px_4px_0px_0px_rgba(24,24,27,0.2)]"
        >
          <div className="flex items-center gap-3">
            <MessageSquare className="w-4 h-4 text-primary" />
            <div className="font-semibold text-zinc-900 truncate">{run.title}</div>
          </div>
          <div className="text-xs text-zinc-500 mt-2">run_id: {run.id}</div>
          {run.updatedAt ? <div className="text-xs text-zinc-400">updated: {run.updatedAt}</div> : null}
        </button>
      ))}
    </div>
  );
}
