import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { useChatRun } from './useChatRun';
import { useChatWorkspaceStore } from '@/features/chat/state/chatWorkspaceStore';
import { createInitialRun } from '@/features/chat/runtime/chatRuntime';

describe('useChatRun', () => {
  beforeEach(() => {
    useChatWorkspaceStore.setState({ activeRun: createInitialRun() });
  });

  it('returns the active run from workspace store', () => {
    useChatWorkspaceStore.setState({
      activeRun: {
        ...createInitialRun(),
        runId: 'run-1',
        scope: 'single_paper',
        status: 'running',
        phase: 'executing',
        currentPhase: 'executing',
        mode: 'rag',
      },
    });

    const { result } = renderHook(() => useChatRun());

    expect(result.current.activeRun.scope).toBe('single_paper');
    expect(result.current.activeRun.currentPhase).toBe('executing');
    expect(result.current.activeRun.runId).toBe('run-1');
  });

  it('preserves waiting_for_user state from runtime store', () => {
    useChatWorkspaceStore.setState({
      activeRun: {
        ...createInitialRun(),
        runId: 'run-2',
        scope: 'full_kb',
        status: 'waiting_confirmation',
        phase: 'waiting_for_user',
        currentPhase: 'waiting_for_user',
        mode: 'agent',
      },
    });

    const { result } = renderHook(() => useChatRun());

    expect(result.current.activeRun.scope).toBe('full_kb');
    expect(result.current.activeRun.currentPhase).toBe('waiting_for_user');
    expect(result.current.activeRun.mode).toBe('agent');
  });
});
