import type { WorkflowStoreState } from '@/features/workflow/state/workflowStore.types';
import { useWorkflowStore } from '@/features/workflow/state/workflowStore';

export const useWorkflowScope = () => useWorkflowStore((state) => state.scope);
export const useWorkflowCurrentRun = () => useWorkflowStore((state) => state.currentRun);
export const useWorkflowPendingActions = () => useWorkflowStore((state) => state.pendingActions);
export const useWorkflowRecoverableTasks = () => useWorkflowStore((state) => state.recoverableTasks);
export const useWorkflowArtifacts = () => useWorkflowStore((state) => state.artifacts);
export const useWorkflowTimeline = () => useWorkflowStore((state) => state.timeline);
export const useWorkflowUiState = () => useWorkflowStore((state) => state.ui);

export const selectHasActiveRun = (state: WorkflowStoreState): boolean => Boolean(state.currentRun);
export const selectHasPendingActions = (state: WorkflowStoreState): boolean => state.pendingActions.length > 0;
export const selectHasRecoverableTasks = (state: WorkflowStoreState): boolean => state.recoverableTasks.length > 0;
export const selectWorkflowSurfaceVisible = (pathname: string): boolean => pathname.startsWith('/chat');
