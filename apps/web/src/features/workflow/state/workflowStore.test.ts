import { beforeEach, describe, expect, it } from 'vitest';
import { useWorkflowStore } from '@/features/workflow/state/workflowStore';

describe('workflowStore', () => {
  beforeEach(() => {
    useWorkflowStore.setState({
      scope: {
        type: 'global',
        id: null,
        title: 'Global Workspace',
        subtitle: 'No scoped run selected',
      },
      currentRun: null,
      pendingActions: [],
      recoverableTasks: [],
      artifacts: [],
      timeline: [],
      ui: {
        showTimelineDrawer: false,
        showArtifactsDrawer: false,
        showConsole: false,
      },
    });
  });

  it('hydrates workflow payload', () => {
    useWorkflowStore.getState().hydrate({
      scope: {
        type: 'paper',
        id: 'paper-1',
        title: 'Paper Scope',
        subtitle: 'paper-1',
      },
      currentRun: {
        id: 'run-1',
        source: 'chat',
        status: 'running',
        stage: 'reasoning',
        error: null,
        nextAction: 'monitor',
        updatedAt: new Date().toISOString(),
      },
      pendingActions: [],
      recoverableTasks: [],
      artifacts: [],
      timeline: [],
    });

    const state = useWorkflowStore.getState();
    expect(state.scope.type).toBe('paper');
    expect(state.currentRun?.id).toBe('run-1');
  });

  it('toggles drawers', () => {
    useWorkflowStore.getState().setArtifactsDrawer(true);
    useWorkflowStore.getState().setTimelineDrawer(true);
    useWorkflowStore.getState().setWorkflowConsole(true);

    const state = useWorkflowStore.getState();
    expect(state.ui.showArtifactsDrawer).toBe(true);
    expect(state.ui.showTimelineDrawer).toBe(true);
    expect(state.ui.showConsole).toBe(true);
  });
});
