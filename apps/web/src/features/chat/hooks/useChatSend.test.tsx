import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { SSEService } from '@/services/sseService';
import { useChatSend } from '@/features/chat/hooks/useChatSend';
import { streamMessage } from '@/services/chatApi';

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

  it('notifies caller when first send creates a real session', async () => {
    const onSessionCreated = vi.fn();
    const createSession = vi.fn().mockResolvedValue({
      id: 'session-1',
      title: 'session-1',
      status: 'active',
      messageCount: 0,
      createdAt: new Date().toISOString(),
    });

    const streamMessageMock = vi.mocked(streamMessage);
    streamMessageMock.mockImplementation(({ handlers }: any) => {
      handlers.onDone?.({
        finish_reason: 'stop',
        response_type: 'general',
      });
    });

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
      addUserMessage: vi.fn(),
      addPlaceholderMessage: vi.fn(),
      rebindSessionId: vi.fn(),
      bindPlaceholderToMessageId: vi.fn(),
      syncStreamingMessage: vi.fn(),
      ingestRuntimeEvent: vi.fn(),
      markStreamError: vi.fn(),
      markStreamCancelled: vi.fn(),
      completeStreamingMessage: vi.fn(),
      removePlaceholderMessage: vi.fn(),
      clearPlaceholder: vi.fn(),
      onSessionCreated,
    }));

    await act(async () => {
      await result.current.handleSend();
    });

    expect(createSession).toHaveBeenCalledTimes(1);
    expect(onSessionCreated).toHaveBeenCalledWith('session-1');
  });

  it('maps canonical citation source_chunk_id into source_id fallback', async () => {
    const completeStreamingMessage = vi.fn();
    const createSession = vi.fn().mockResolvedValue({
      id: 'session-1',
      title: 'session-1',
      status: 'active',
      messageCount: 0,
      createdAt: new Date().toISOString(),
    });

    const streamMessageMock = vi.mocked(streamMessage);
    streamMessageMock.mockImplementation(({ handlers }: any) => {
      handlers.onDone?.({
        finish_reason: 'stop',
        response_type: 'rag',
        answer_mode: 'partial',
        answer: 'answer',
        citations: [
          {
            paper_id: 'paper-1',
            source_chunk_id: 'chunk-1',
            page_num: 3,
            citation_jump_url: '/read/paper-1?page=3&source=chat&source_id=chunk-1',
          },
        ],
      });
    });

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
      addUserMessage: vi.fn(),
      addPlaceholderMessage: vi.fn(),
      rebindSessionId: vi.fn(),
      bindPlaceholderToMessageId: vi.fn(),
      syncStreamingMessage: vi.fn(),
      ingestRuntimeEvent: vi.fn(),
      markStreamError: vi.fn(),
      markStreamCancelled: vi.fn(),
      completeStreamingMessage,
      removePlaceholderMessage: vi.fn(),
      clearPlaceholder: vi.fn(),
    }));

    await act(async () => {
      await result.current.handleSend();
    });

    expect(completeStreamingMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        answerContract: expect.objectContaining({
          citations: [
            expect.objectContaining({
              source_chunk_id: 'chunk-1',
              source_id: 'chunk-1',
              citation_jump_url: '/read/paper-1?page=3&source=chat&source_id=chunk-1',
            }),
          ],
        }),
      }),
    );
  });

  it('preserves compare_matrix when normalizing compare responses', async () => {
    const completeStreamingMessage = vi.fn();
    const createSession = vi.fn().mockResolvedValue({
      id: 'session-1',
      title: 'session-1',
      status: 'active',
      messageCount: 0,
      createdAt: new Date().toISOString(),
    });

    const streamMessageMock = vi.mocked(streamMessage);
    streamMessageMock.mockImplementation(({ handlers }: any) => {
      handlers.onDone?.({
        finish_reason: 'stop',
        response_type: 'compare',
        answer_mode: 'partial',
        answer: '',
        compare_matrix: {
          paper_ids: ['paper-1', 'paper-2'],
          dimensions: [{ id: 'method', label: 'Method' }],
          rows: [],
          summary: '',
          cross_paper_insights: [],
        },
        citations: [],
        evidence_blocks: [],
      });
    });

    const { result } = renderHook(() => useChatSend({
      input: 'compare these papers',
      sending: false,
      mode: 'rag',
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
      addUserMessage: vi.fn(),
      addPlaceholderMessage: vi.fn(),
      rebindSessionId: vi.fn(),
      bindPlaceholderToMessageId: vi.fn(),
      syncStreamingMessage: vi.fn(),
      ingestRuntimeEvent: vi.fn(),
      markStreamError: vi.fn(),
      markStreamCancelled: vi.fn(),
      completeStreamingMessage,
      removePlaceholderMessage: vi.fn(),
      clearPlaceholder: vi.fn(),
    }));

    await act(async () => {
      await result.current.handleSend();
    });

    expect(completeStreamingMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        answerContract: expect.objectContaining({
          response_type: 'compare',
          compare_matrix: expect.objectContaining({
            paper_ids: ['paper-1', 'paper-2'],
          }),
        }),
      }),
    );
  });

  it('passes compare paper ids through chat context for follow-up questions', async () => {
    const createSession = vi.fn().mockResolvedValue({
      id: 'session-1',
      title: 'session-1',
      status: 'active',
      messageCount: 0,
      createdAt: new Date().toISOString(),
    });

    const streamMessageMock = vi.mocked(streamMessage);
    streamMessageMock.mockImplementation(({ handlers }: any) => {
      handlers.onDone?.({
        finish_reason: 'stop',
        response_type: 'general',
      });
    });

    const { result } = renderHook(() => useChatSend({
      input: 'compare these findings',
      sending: false,
      mode: 'rag',
      scope: { type: null, id: null },
      comparePaperIds: ['p-001', 'p-002'],
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
      addUserMessage: vi.fn(),
      addPlaceholderMessage: vi.fn(),
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
      await result.current.handleSend();
    });

    expect(streamMessageMock).toHaveBeenCalledWith(
      expect.objectContaining({
        context: expect.objectContaining({
          auto_confirm: false,
          paper_ids: ['p-001', 'p-002'],
        }),
      }),
    );
  });
});
