import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSSE } from './useSSE';
import type { SSEEvent, SSEHandlers } from '@/services/sseService';

const { disconnectMock, state } = vi.hoisted(() => ({
  disconnectMock: vi.fn(),
  state: {
    capturedHandlers: null as SSEHandlers | null,
  },
}));

vi.mock('@/services/sseService', () => ({
  sseService: {
    connect: vi.fn((_url: string, handlers: SSEHandlers) => {
      state.capturedHandlers = handlers;
    }),
    disconnect: disconnectMock,
  },
}));

describe('useSSE', () => {
  beforeEach(() => {
    state.capturedHandlers = null;
    disconnectMock.mockClear();
  });

  it('moves to waiting state on confirmation events and disconnects the current stream', () => {
    const { result } = renderHook(() => useSSE());

    act(() => {
      result.current.connect('/api/v1/chat/stream', { message: 'Delete everything' });
    });

    expect(result.current.isConnected).toBe(true);
    expect(state.capturedHandlers).not.toBeNull();

    const confirmationEvent: SSEEvent = {
      type: 'confirmation_required',
      content: {
        confirmation_id: 'confirm-123',
        tool_name: 'delete_paper',
        parameters: { paper_id: 'paper-1' },
      },
    };

    act(() => {
      state.capturedHandlers?.onMessage(confirmationEvent);
    });

    expect(result.current.isConnected).toBe(false);
    expect(result.current.confirmation).toEqual({
      confirmation_id: 'confirm-123',
      tool: 'delete_paper',
      params: { paper_id: 'paper-1' },
    });
    expect(disconnectMock).toHaveBeenCalledTimes(1);
  });
});
