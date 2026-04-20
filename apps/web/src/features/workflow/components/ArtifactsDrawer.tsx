import { useWorkflowArtifacts, useWorkflowUiState } from '@/features/workflow/state/workflowSelectors';
import { workflowActions } from '@/features/workflow/state/workflowActions';

export function ArtifactsDrawer() {
  const artifacts = useWorkflowArtifacts();
  const ui = useWorkflowUiState();

  if (!ui.showArtifactsDrawer) {
    return null;
  }

  return (
    <aside className="fixed right-[320px] top-14 z-40 h-[calc(100vh-3.5rem)] w-[320px] border-l border-zinc-200 bg-white p-4 shadow-lg">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Artifacts & Evidence</h3>
        <button
          className="text-xs text-zinc-500 hover:text-zinc-800"
          onClick={() => workflowActions.setArtifactsDrawer(false)}
        >
          Close
        </button>
      </div>
      <div className="mt-4 space-y-3">
        {artifacts.length === 0 ? (
          <p className="text-xs text-zinc-500">No artifacts available in this scope.</p>
        ) : (
          artifacts.map((artifact) => (
            <div key={artifact.id} className="rounded border border-zinc-200 p-2">
              <div className="text-xs font-semibold text-zinc-900">{artifact.title}</div>
              <div className="mt-1 text-xs text-zinc-600">{artifact.context || artifact.kind}</div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
