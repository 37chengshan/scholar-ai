import { resolveWorkflowCopy } from '@/features/workflow/resolvers/workflowResolvers';
import { useWorkflowPendingActions } from '@/features/workflow/state/workflowSelectors';

export function PendingActionsPanel() {
  const actions = useWorkflowPendingActions();

  return (
    <section className="rounded-md border border-zinc-200 bg-white p-3">
      <h3 className="text-[10px] font-bold uppercase tracking-[0.16em] text-zinc-500">{resolveWorkflowCopy('pending')}</h3>
      <div className="mt-3 space-y-2">
        {actions.length === 0 ? (
          <p className="text-xs text-zinc-500">No pending actions in current scope.</p>
        ) : (
          actions.map((action) => (
            <div key={action.id} className="rounded border border-zinc-200 px-3 py-2">
              <div className="text-xs font-semibold text-zinc-900">{action.label}</div>
              <div className="mt-1 text-xs text-zinc-600">{action.description}</div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
