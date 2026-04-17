import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import { useChatStream } from './useChatStream';

const telemetrySpy = vi.fn();

vi.mock('@/lib/observability/telemetry', () => ({
  trackStreamEvent: (...args: unknown[]) => telemetrySpy(...args),
}));

describe('useChatStream observability', () => {
  beforeEach(() => {
    telemetrySpy.mockReset();
  });

  it('tracks stream_started on session_start', () => {
    const { result } = renderHook(() => useChatStream());

    act(() => {
      result.current.handleSSEEvent({
        message_id: 'm1',
        event_type: 'session_start',
        data: { session_id: 's1', task_type: 'general' },
      });
    });

    expect(telemetrySpy).toHaveBeenCalledWith(
      expect.objectContaining({ event: 'stream_started', sessionId: 's1', messageId: 'm1' })
    );
  });

  it('tracks stale event ignored when message_id mismatches', () => {
    const { result } = renderHook(() => useChatStream());

    act(() => {
      result.current.handleSSEEvent({
        message_id: 'm1',
        event_type: 'session_start',
        data: { session_id: 's1', task_type: 'general' },
      });
    });

    act(() => {
      result.current.handleSSEEvent({
        message_id: 'm2',
        event_type: 'message',
        data: { delta: 'hello' },
      });
    });

    expect(telemetrySpy).toHaveBeenCalledWith(
      expect.objectContaining({ event: 'stale_event_ignored', expectedMessageId: 'm1', receivedMessageId: 'm2' })
    );
  });
});
