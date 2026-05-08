import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useWorkflowHydration } from './useWorkflowHydration';
import { useWorkflowStore } from '@/features/workflow/state/workflowStore';
import { useChatWorkspaceStore } from '@/features/chat/state/chatWorkspaceStore';
import { createInitialRun } from '@/features/chat/runtime/chatRuntime';
import { persistChatHandoff } from '@/features/chat/chatHandoff';

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
    window.sessionStorage.clear();
    mockedLocation = { pathname: '/chat', search: '', state: null };
    useWorkflowStore.setState({
      scope: {
        type: 'global',
        id: null,
        title: '研究工作区',
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
    expect(state.pendingActions[0]?.label).toBe('Retry');
    expect(state.recoverableTasks[0]?.label).toBe('Retry');
    expect(state.artifacts[0]?.title).toBe('Evidence');
  });

  it('keeps fallback hydration outside chat routes', () => {
    mockedLocation = { pathname: '/search', search: '', state: null };

    renderHook(() => useWorkflowHydration());

    const state = useWorkflowStore.getState();
    expect(state.currentRun).toBeNull();
    expect(state.scope.title).toBe('检索工作区');
    expect(state.timeline[0]?.title).toBe('范围已更新');
  });

  it('hydrates a durable handoff as a waiting workflow when there is no active run', () => {
    mockedLocation = { pathname: '/chat', search: '?kbId=kb-1&handoff=1', state: null };
    persistChatHandoff(
      { kbId: 'kb-1' },
      {
        origin: 'review',
        promptDraft: 'Continue from the review evidence.',
        evidence: [{ paperId: 'paper-1' }],
        returnTo: '/knowledge-bases/kb-1?tab=review&runId=run-1',
      },
    );

    renderHook(() => useWorkflowHydration());

    const state = useWorkflowStore.getState();
    expect(state.currentRun?.status).toBe('waiting');
    expect(state.currentRun?.stage).toBe('ready_to_continue');
    expect(state.pendingActions.map((action) => action.label)).toEqual(['继续提问', '返回来源页面']);
    expect(state.artifacts[0]?.title).toBe('已准备好的追问');
    expect(state.timeline[0]?.title).toBe('已恢复追问上下文');
  });
});
