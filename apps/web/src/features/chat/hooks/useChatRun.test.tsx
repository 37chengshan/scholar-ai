import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { useChatRun } from './useChatRun';
import { useChatWorkspaceStore } from '@/features/chat/state/chatWorkspaceStore';

describe('useChatRun', () => {
  it('derives single_paper scope when paperId exists', () => {
    useChatWorkspaceStore.setState({
      scope: { type: 'single_paper', id: 'p-1' },
      activeRunStatus: 'running',
      selectedRunId: 'run-1',
      mode: 'rag',
    });

    const { result } = renderHook(() => useChatRun());

    expect(result.current.activeRun.scope).toBe('single_paper');
    expect(result.current.activeRun.currentPhase).toBe('executing');
    expect(result.current.activeRun.runId).toBe('run-1');
  });

  it('derives waiting_confirmation phase from run status', () => {
    useChatWorkspaceStore.setState({
      scope: { type: 'full_kb', id: 'kb-1' },
      activeRunStatus: 'waiting_confirmation',
      selectedRunId: 'run-2',
      mode: 'agent',
    });

    const { result } = renderHook(() => useChatRun());

    expect(result.current.activeRun.scope).toBe('full_kb');
    expect(result.current.activeRun.currentPhase).toBe('waiting_for_user');
    expect(result.current.activeRun.mode).toBe('agent');
  });
});
