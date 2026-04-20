import { resolveStatusBadge } from '@/features/workflow/resolvers/workflowResolvers';
import { useWorkflowCurrentRun } from '@/features/workflow/state/workflowSelectors';

const badgeClassByTone = {
  default: 'bg-blue-100 text-blue-700 border-blue-200',
  success: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  warning: 'bg-amber-100 text-amber-700 border-amber-200',
  danger: 'bg-rose-100 text-rose-700 border-rose-200',
  muted: 'bg-zinc-100 text-zinc-600 border-zinc-200',
} as const;

export function CurrentRunBar() {
  const run = useWorkflowCurrentRun();

  if (!run) {
    return (
      <div className="rounded-md border border-dashed border-zinc-300 px-4 py-3 text-xs text-zinc-500">
        No active run. Start from Chat, Search import, or Library actions.
      </div>
    );
  }

  const badge = resolveStatusBadge(run.status);

  return (
    <div className="rounded-md border border-zinc-200 bg-white px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold tracking-[0.12em] ${badgeClassByTone[badge.tone]}`}>
          {badge.label}
        </span>
        <span className="text-xs font-semibold text-zinc-900">Run #{run.id}</span>
        <span className="text-xs text-zinc-500">{run.stage}</span>
      </div>
      {run.nextAction ? <div className="mt-2 text-xs text-zinc-600">Next: {run.nextAction}</div> : null}
      {run.error ? <div className="mt-2 text-xs text-rose-600">Error: {run.error}</div> : null}
    </div>
  );
}
