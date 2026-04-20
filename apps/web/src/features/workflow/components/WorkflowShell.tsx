import { ActiveScopeBanner } from '@/features/workflow/components/ActiveScopeBanner';
import { CurrentRunBar } from '@/features/workflow/components/CurrentRunBar';
import { PendingActionsPanel } from '@/features/workflow/components/PendingActionsPanel';
import { RecoverableTasksPanel } from '@/features/workflow/components/RecoverableTasksPanel';
import { ActivityTimelineDrawer } from '@/features/workflow/components/ActivityTimelineDrawer';
import { ArtifactsDrawer } from '@/features/workflow/components/ArtifactsDrawer';
import { workflowActions } from '@/features/workflow/state/workflowActions';
import { useWorkflowHydration } from '@/features/workflow/hooks/useWorkflowHydration';

export function WorkflowShell() {
  useWorkflowHydration();

  return (
    <>
      <div className="border-b border-zinc-200 bg-zinc-100/70 px-4 py-3">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-600">Workflow Console</h2>
            <div className="flex items-center gap-2">
              <button
                onClick={() => workflowActions.setArtifactsDrawer(true)}
                className="rounded border border-zinc-300 bg-white px-2 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-zinc-700 hover:bg-zinc-50"
              >
                Artifacts
              </button>
              <button
                onClick={() => workflowActions.setTimelineDrawer(true)}
                className="rounded border border-zinc-300 bg-white px-2 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-zinc-700 hover:bg-zinc-50"
              >
                Activity
              </button>
            </div>
          </div>

          <ActiveScopeBanner />
          <CurrentRunBar />

          <div className="grid gap-3 lg:grid-cols-2">
            <PendingActionsPanel />
            <RecoverableTasksPanel />
          </div>
        </div>
      </div>

      <ArtifactsDrawer />
      <ActivityTimelineDrawer />
    </>
  );
}
