import { renderHook, act, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createInitialRun } from '@/features/chat/runtime/chatRuntime';
import { useChatRuntimeBridge } from './useChatRuntimeBridge';
import type { UseRuntimeReturn } from '@/features/chat/runtime/useRuntime';

const mocks = vi.hoisted(() => ({
  toastError: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    error: mocks.toastError,
  },
}));

describe('useChatRuntimeBridge', () => {
  beforeEach(() => {
    mocks.toastError.mockReset();
  });

  it('mirrors runtime state into workspace actions', async () => {
    const runtime: Pick<UseRuntimeReturn, 'run' | 'ingestEvent' | 'dispatchRun'> = {
      run: {
        ...createInitialRun(),
        runId: 'run-1',
        status: 'running',
        pendingActions: [{ id: 'retry-1', type: 'retry' }],
        recoverable: true,
      },
      ingestEvent: vi.fn().mockReturnValue(true),
      dispatchRun: vi.fn(),
    };

    const setActiveRun = vi.fn();
    const setSelectedRunId = vi.fn();
    const setActiveRunStatus = vi.fn();
    const setPendingActions = vi.fn();
    const setRecoveryBannerVisible = vi.fn();
    const setRunArtifactsPanelOpen = vi.fn();
    const setStreamingMessageId = vi.fn();

    renderHook(() => useChatRuntimeBridge({
      isZh: true,
      currentSessionId: 'session-1',
      currentMessageId: 'message-1',
      currentMessageIdRef: { current: 'message-1' },
      sseServiceRef: { current: null },
      runtime,
      streamState: { streamStatus: 'streaming', tokensUsed: 10, cost: 0.2 },
      confirmation: null,
      resetConfirmation: vi.fn(),
      handleSSEEvent: vi.fn(),
      dispatch: vi.fn(),
      syncStreamingMessage: vi.fn(),
      setActiveRun,
      setSelectedRunId,
      setActiveRunStatus,
      setPendingActions,
      setRecoveryBannerVisible,
      setRunArtifactsPanelOpen,
      setStreamingMessageId,
    }));

    await waitFor(() => {
      expect(setActiveRun).toHaveBeenCalledWith(runtime.run);
    });

    expect(setSelectedRunId).toHaveBeenCalledWith('run-1');
    expect(setActiveRunStatus).toHaveBeenCalledWith('running');
    expect(setPendingActions).toHaveBeenCalledWith(runtime.run.pendingActions);
    expect(setRecoveryBannerVisible).toHaveBeenCalledWith(true);
    expect(setRunArtifactsPanelOpen).toHaveBeenCalledWith(false);
    expect(setStreamingMessageId).toHaveBeenCalledWith('message-1');
  });

  it('replays confirmation streams back into stream and runtime handlers', async () => {
    const connect = vi.fn();
    const handleSSEEvent = vi.fn();
    const dispatch = vi.fn();
    const syncStreamingMessage = vi.fn();
    const runtime: Pick<UseRuntimeReturn, 'run' | 'ingestEvent' | 'dispatchRun'> = {
      run: {
        ...createInitialRun(),
        status: 'running',
      },
      ingestEvent: vi.fn().mockReturnValue(true),
      dispatchRun: vi.fn(),
    };

    const { result } = renderHook(() => useChatRuntimeBridge({
      isZh: false,
      currentSessionId: 'session-2',
      currentMessageId: 'message-2',
      currentMessageIdRef: { current: 'message-2' },
      sseServiceRef: { current: { connect } as any },
      runtime,
      streamState: { streamStatus: 'streaming', tokensUsed: 6, cost: 0.1, startedAt: 10, endedAt: 20 },
      confirmation: { confirmation_id: 'confirm-1', tool: 'write_file', params: { path: 'tmp' } },
      resetConfirmation: vi.fn(),
      handleSSEEvent,
      dispatch,
      syncStreamingMessage,
      setActiveRun: vi.fn(),
      setSelectedRunId: vi.fn(),
      setActiveRunStatus: vi.fn(),
      setPendingActions: vi.fn(),
      setRecoveryBannerVisible: vi.fn(),
      setRunArtifactsPanelOpen: vi.fn(),
      setStreamingMessageId: vi.fn(),
    }));

    await act(async () => {
      await result.current.handleConfirmation(true);
    });

    expect(connect).toHaveBeenCalledTimes(1);
    expect(connect.mock.calls[0][2]).toEqual({
      confirmation_id: 'confirm-1',
      approved: true,
      session_id: 'session-2',
    });

    const handlers = connect.mock.calls[0][1];
    act(() => {
      handlers.onEnvelope({
        event: 'message',
        message_id: 'message-2',
        data: { delta: 'hello' },
      });
    });

    expect(handleSSEEvent).toHaveBeenCalledWith(expect.objectContaining({
      message_id: 'message-2',
      event_type: 'message',
      data: { delta: 'hello' },
    }));
    expect(runtime.ingestEvent).toHaveBeenCalledWith(expect.objectContaining({
      message_id: 'message-2',
      event: 'message',
      data: { delta: 'hello' },
    }));
    expect(syncStreamingMessage).toHaveBeenCalledWith('message-2');
  });
});