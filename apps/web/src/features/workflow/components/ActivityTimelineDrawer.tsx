import { useWorkflowTimeline, useWorkflowUiState } from '@/features/workflow/state/workflowSelectors';
import { workflowActions } from '@/features/workflow/state/workflowActions';

export function ActivityTimelineDrawer() {
  const timeline = useWorkflowTimeline();
  const ui = useWorkflowUiState();

  if (!ui.showTimelineDrawer) {
    return null;
  }

  return (
    <aside className="fixed right-0 top-14 z-40 h-[calc(100vh-3.5rem)] w-[320px] border-l border-zinc-200 bg-white p-4 shadow-lg">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Recent Activity</h3>
        <button
          className="text-xs text-zinc-500 hover:text-zinc-800"
          onClick={() => workflowActions.setTimelineDrawer(false)}
        >
          Close
        </button>
      </div>
      <div className="mt-4 space-y-3">
        {timeline.length === 0 ? (
          <p className="text-xs text-zinc-500">No workflow activity yet.</p>
        ) : (
          timeline.map((event) => (
            <div key={event.id} className="rounded border border-zinc-200 p-2">
              <div className="text-xs font-semibold text-zinc-900">{event.title}</div>
              <div className="mt-1 text-xs text-zinc-600">{event.description}</div>
              <div className="mt-1 text-[10px] text-zinc-400">{new Date(event.at).toLocaleString()}</div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
