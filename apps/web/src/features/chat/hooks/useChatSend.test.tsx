import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { SSEService } from '@/services/sseService';
import { useChatSend } from '@/features/chat/hooks/useChatSend';

vi.mock('@/services/chatApi', () => ({
  streamMessage: vi.fn(),
}));

describe('useChatSend', () => {
  it('adds assistant placeholder immediately before async session creation resolves', async () => {
    let resolveCreateSession: ((value: any) => void) | null = null;
    const createSession = vi.fn(() => new Promise<any>((resolve) => {
      resolveCreateSession = resolve;
    }));

    const addUserMessage = vi.fn();
    const addPlaceholderMessage = vi.fn();

    const { result } = renderHook(() => useChatSend({
      input: 'hello',
      sending: false,
      mode: 'agent',
      scope: { type: null, id: null },
      scopeLoading: false,
      currentSession: null,
      isZh: false,
      setInput: vi.fn(),
      setSending: vi.fn(),
      setAgentUIState: vi.fn(),
      setSessionTokens: vi.fn(),
      setSessionCost: vi.fn(),
      createSession,
      sendLockRef: { current: false },
      sseServiceRef: { current: null as SSEService | null },
      currentMessageIdRef: { current: '' },
      streamStateRef: { current: { streamStatus: 'idle', contentBuffer: '', reasoningBuffer: '', toolTimeline: [], citations: [], tokensUsed: 0, cost: 0 } as any },
      streamApi: {
        streamState: { streamStatus: 'idle' },
        setCurrentMessageId: vi.fn(),
        currentMessageId: null,
        startRun: vi.fn(),
        handleSSEEvent: vi.fn(),
        forceFlush: vi.fn(),
        dispatch: vi.fn(),
        getBufferedContent: vi.fn(() => ({ content: '', reasoning: '' })),
        stopRun: vi.fn(),
      } as any,
      addUserMessage,
      addPlaceholderMessage,
      rebindSessionId: vi.fn(),
      bindPlaceholderToMessageId: vi.fn(),
      syncStreamingMessage: vi.fn(),
      ingestRuntimeEvent: vi.fn(),
      markStreamError: vi.fn(),
      markStreamCancelled: vi.fn(),
      completeStreamingMessage: vi.fn(),
      removePlaceholderMessage: vi.fn(),
      clearPlaceholder: vi.fn(),
    }));

    await act(async () => {
      void result.current.handleSend();
      await Promise.resolve();
    });

    expect(addUserMessage).toHaveBeenCalledTimes(1);
    expect(addPlaceholderMessage).toHaveBeenCalledTimes(1);
    expect(createSession).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveCreateSession?.({
        id: 'session-1',
        title: 'session-1',
        status: 'active',
        messageCount: 0,
        createdAt: new Date().toISOString(),
      });
      await Promise.resolve();
    });
  });
});
