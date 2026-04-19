import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SSEService } from './sseService';

describe('SSEService', () => {
  let service: SSEService;

  beforeEach(() => {
    service = new SSEService();
  });

  it('surfaces backend SSE error events through onError and disconnects', () => {
    const onMessage = vi.fn();
    const onError = vi.fn();
    const onDone = vi.fn();

    (service as any).currentHandlers = { onMessage, onError, onDone };
    (service as any).abortController = new AbortController();
    (service as any).isDisconnecting = false;

    (service as any).handleEvent(
      'error',
      JSON.stringify({ message_id: 'm1', type: 'error', error: 'Agent execution failed' })
    );

    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0]).toBeInstanceOf(Error);
    expect(onError.mock.calls[0][0].message).toBe('Agent execution failed');
    expect(onMessage).not.toHaveBeenCalled();
    expect(onDone).not.toHaveBeenCalled();
    expect((service as any).abortController).toBeNull();
  });

  it('rejects business events without message_id', () => {
    const onMessage = vi.fn();
    const onError = vi.fn();
    const onDone = vi.fn();

    (service as any).currentHandlers = { onMessage, onError, onDone };
    (service as any).abortController = new AbortController();
    (service as any).isDisconnecting = false;

    (service as any).handleEvent(
      'message',
      JSON.stringify({ delta: 'hello' })
    );

    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0]).toBeInstanceOf(Error);
    expect(onError.mock.calls[0][0].message).toContain('missing message_id');
    expect(onMessage).not.toHaveBeenCalled();
    expect(onDone).not.toHaveBeenCalled();
    expect((service as any).abortController).toBeNull();
  });

  it('unwraps envelope payload and forwards flat message delta', () => {
    const onMessage = vi.fn();
    const onError = vi.fn();
    const onDone = vi.fn();

    (service as any).currentHandlers = { onMessage, onError, onDone };
    (service as any).abortController = new AbortController();
    (service as any).isDisconnecting = false;

    (service as any).handleEvent(
      'message',
      JSON.stringify({
        event: 'message',
        message_id: 'm2',
        data: { delta: 'hello world', seq: 1 },
      })
    );

    expect(onError).not.toHaveBeenCalled();
    expect(onDone).not.toHaveBeenCalled();
    expect(onMessage).toHaveBeenCalledTimes(1);

    const event = onMessage.mock.calls[0][0];
    expect(event.type).toBe('message');
    expect(event.message_id).toBe('m2');
    expect(event.content).toEqual({ delta: 'hello world', seq: 1 });
  });

  it('clears lastEventId on fresh connect', () => {
    const onMessage = vi.fn();
    const onError = vi.fn();
    const onDone = vi.fn();

    (service as any).lastEventId = 'stale-event-id';
    const startStreamingSpy = vi
      .spyOn(service as any, 'startStreaming')
      .mockResolvedValue(undefined);

    service.connect('/api/v1/chat/stream', { onMessage, onError, onDone }, { session_id: 's1' });

    expect((service as any).lastEventId).toBeNull();
    expect(startStreamingSpy).toHaveBeenCalledWith(false);
  });

  it('increments reconnect attempts across reconnect chain', () => {
    vi.useFakeTimers();

    const startStreamingSpy = vi
      .spyOn(service as any, 'startStreaming')
      .mockResolvedValue(undefined);

    (service as any).isDisconnecting = false;
    (service as any).reconnectAttempts = 0;
    (service as any).config = {
      maxReconnects: 3,
      heartbeatTimeout: 60000,
      reconnectBaseDelay: 1,
    };

    (service as any).handleReconnect();
    expect((service as any).reconnectAttempts).toBe(1);
    vi.runOnlyPendingTimers();
    expect(startStreamingSpy).toHaveBeenCalledWith(true);

    (service as any).handleReconnect();
    expect((service as any).reconnectAttempts).toBe(2);
    vi.runOnlyPendingTimers();
    expect(startStreamingSpy).toHaveBeenCalledTimes(2);

    vi.useRealTimers();
  });
});
