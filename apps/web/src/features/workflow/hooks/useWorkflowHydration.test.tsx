import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useWorkflowHydration } from './useWorkflowHydration';
import { useWorkflowStore } from '@/features/workflow/state/workflowStore';
import { useChatWorkspaceStore } from '@/features/chat/state/chatWorkspaceStore';
import { createInitialRun } from '@/features/chat/runtime/chatRuntime';

let mockedLocation = {
  pathname: '/chat',
  search: '',
  state: null as unknown,
};

vi.mock('react-router', async () => {
  const actual = await vi.importActual<any>('react-router');
  return {
    ...actual,
    useLocation: () => mockedLocation,
  };
});

describe('useWorkflowHydration', () => {
  beforeEach(() => {
    mockedLocation = { pathname: '/chat', search: '', state: null };
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
    useChatWorkspaceStore.setState({
      activeRun: createInitialRun(),
      scope: { type: null, id: null },
    });
  });

  it('hydrates workflow shell from active chat run on /chat', () => {
    useChatWorkspaceStore.setState({
      scope: { type: 'single_paper', id: 'paper-1', title: 'Paper One' },
      activeRun: {
        ...createInitialRun(),
        runId: 'run-1',
        scope: 'single_paper',
        status: 'running',
        phase: 'executing',
        currentPhase: 'executing',
        pendingActions: [{ id: 'retry-1', type: 'retry' }],
        recoverable: true,
        evidence: [{ sourceId: 'src-1', title: 'Evidence', textPreview: 'snippet' }],
        timeline: [{ id: 'tl-1', type: 'phase', label: 'Run started', timestamp: Date.now(), status: 'running' }],
      },
    });

    renderHook(() => useWorkflowHydration());

    const state = useWorkflowStore.getState();
    expect(state.currentRun?.id).toBe('run-1');
    expect(state.scope.type).toBe('paper');
    expect(state.pendingActions[0]?.label).toBe('RETRY');
    expect(state.recoverableTasks[0]?.label).toBe('RETRY');
    expect(state.artifacts[0]?.title).toBe('Evidence');
  });

  it('keeps fallback hydration outside chat routes', () => {
    mockedLocation = { pathname: '/search', search: '', state: null };

    renderHook(() => useWorkflowHydration());

    const state = useWorkflowStore.getState();
    expect(state.currentRun).toBeNull();
    expect(state.scope.title).toBe('Discovery Workflow');
    expect(state.timeline[0]?.title).toBe('Scope Updated');
  });
});
