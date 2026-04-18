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
});
