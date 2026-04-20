import { resolveWorkflowCopy } from '@/features/workflow/resolvers/workflowResolvers';
import { useWorkflowRecoverableTasks } from '@/features/workflow/state/workflowSelectors';

export function RecoverableTasksPanel() {
  const tasks = useWorkflowRecoverableTasks();

  return (
    <section className="rounded-md border border-zinc-200 bg-white p-3">
      <h3 className="text-[10px] font-bold uppercase tracking-[0.16em] text-zinc-500">{resolveWorkflowCopy('recoverable')}</h3>
      <div className="mt-3 space-y-2">
        {tasks.length === 0 ? (
          <p className="text-xs text-zinc-500">No recoverable tasks.</p>
        ) : (
          tasks.map((task) => (
            <div key={task.id} className="rounded border border-rose-200 bg-rose-50 px-3 py-2">
              <div className="text-xs font-semibold text-rose-700">{task.label}</div>
              <div className="mt-1 text-xs text-rose-600">{task.description}</div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
