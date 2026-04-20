import { useWorkflowStore } from '@/features/workflow/state/workflowStore';
import type { WorkflowHydratedPayload } from '@/features/workflow/types';

export const workflowActions = {
  hydrate(payload: WorkflowHydratedPayload): void {
    useWorkflowStore.getState().hydrate(payload);
  },
  setArtifactsDrawer(show: boolean): void {
    useWorkflowStore.getState().setArtifactsDrawer(show);
  },
  setTimelineDrawer(show: boolean): void {
    useWorkflowStore.getState().setTimelineDrawer(show);
  },
  clearRun(): void {
    useWorkflowStore.getState().clearWorkflowRun();
  },
};
