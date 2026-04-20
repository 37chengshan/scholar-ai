import { create } from 'zustand';
import type { WorkflowAction, WorkflowArtifact, WorkflowHydratedPayload, WorkflowRun, WorkflowScope, WorkflowTimelineEvent } from '@/features/workflow/types';

interface WorkflowUiState {
  showTimelineDrawer: boolean;
  showArtifactsDrawer: boolean;
}

interface WorkflowStoreState {
  scope: WorkflowScope;
  currentRun: WorkflowRun | null;
  pendingActions: WorkflowAction[];
  recoverableTasks: WorkflowAction[];
  artifacts: WorkflowArtifact[];
  timeline: WorkflowTimelineEvent[];
  ui: WorkflowUiState;
  hydrate: (payload: WorkflowHydratedPayload) => void;
  setTimelineDrawer: (show: boolean) => void;
  setArtifactsDrawer: (show: boolean) => void;
  clearWorkflowRun: () => void;
}

const defaultScope: WorkflowScope = {
  type: 'global',
  id: null,
  title: 'Global Workspace',
  subtitle: 'No scoped run selected',
};

export const useWorkflowStore = create<WorkflowStoreState>((set) => ({
  scope: defaultScope,
  currentRun: null,
  pendingActions: [],
  recoverableTasks: [],
  artifacts: [],
  timeline: [],
  ui: {
    showTimelineDrawer: false,
    showArtifactsDrawer: false,
  },
  hydrate: (payload) =>
    set({
      scope: payload.scope,
      currentRun: payload.currentRun,
      pendingActions: payload.pendingActions,
      recoverableTasks: payload.recoverableTasks,
      artifacts: payload.artifacts,
      timeline: payload.timeline,
    }),
  setTimelineDrawer: (show) =>
    set((state) => ({
      ui: {
        ...state.ui,
        showTimelineDrawer: show,
      },
    })),
  setArtifactsDrawer: (show) =>
    set((state) => ({
      ui: {
        ...state.ui,
        showArtifactsDrawer: show,
      },
    })),
  clearWorkflowRun: () =>
    set({
      currentRun: null,
      pendingActions: [],
      recoverableTasks: [],
    }),
}));
