import type { WorkflowAction, WorkflowArtifact, WorkflowRun, WorkflowScope, WorkflowTimelineEvent } from '@/features/workflow/types';

export interface WorkflowStoreState {
  scope: WorkflowScope;
  currentRun: WorkflowRun | null;
  pendingActions: WorkflowAction[];
  recoverableTasks: WorkflowAction[];
  artifacts: WorkflowArtifact[];
  timeline: WorkflowTimelineEvent[];
}
