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
    expect(onSessionCreated).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'session-1',
      }),
    );
  });

  it('persists single-paper scope metadata when creating a new session on first send', async () => {
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
      mode: 'rag',
      scope: { type: 'single_paper', id: 'paper-1', title: 'Paper One' },
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

    expect(createSession).toHaveBeenCalledWith(
      'hello',
      expect.objectContaining({
        scopeType: 'single_paper',
        paperId: 'paper-1',
        title: 'Paper One',
      }),
    );
  });

  it('persists compare scope metadata when creating a new comparison session', async () => {
    const createSession = vi.fn().mockResolvedValue({
      id: 'session-compare',
      title: 'session-compare',
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
      input: 'compare this',
      sending: false,
      mode: 'rag',
      scope: { type: null, id: null },
      comparePaperIds: ['paper-1', 'paper-2'],
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

    expect(createSession).toHaveBeenCalledWith(
      'compare this',
      expect.objectContaining({
        scopeType: 'compare',
        paperIds: ['paper-1', 'paper-2'],
      }),
    );
  });

  it('forwards compare handoff evidence into stream context', async () => {
    const createSession = vi.fn().mockResolvedValue({
      id: 'session-compare',
      title: 'session-compare',
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
      input: 'compare this',
      sending: false,
      mode: 'rag',
      scope: { type: null, id: null },
      comparePaperIds: ['paper-1', 'paper-2'],
      handoffEvidence: [
        {
          handoffId: 'paper-1::results::chunk-1::shared finding',
          paperId: 'paper-1',
          sourceChunkId: 'chunk-1',
          pageNum: 3,
          claim: 'Shared finding',
          dimensionId: 'results',
          sectionPath: 'results',
          contentType: 'text',
          text: 'Paper one reports the finding.',
          citationJumpUrl: '/read/paper-1?page=3&source=chat&source_id=chunk-1',
          title: 'Paper One',
        },
      ],
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

    expect(streamMessageMock).toHaveBeenCalledWith(expect.objectContaining({
      context: expect.objectContaining({
        paper_ids: ['paper-1', 'paper-2'],
        handoff_evidence: [
          expect.objectContaining({
            handoff_id: 'paper-1::results::chunk-1::shared finding',
            paper_id: 'paper-1',
            source_chunk_id: 'chunk-1',
            page_num: 3,
            claim: 'Shared finding',
            dimension_id: 'results',
            section_path: 'results',
            content_type: 'text',
            text: 'Paper one reports the finding.',
            citation_jump_url: '/read/paper-1?page=3&source=chat&source_id=chunk-1',
            title: 'Paper One',
          }),
        ],
      }),
    }));
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
        finalContent: 'answer',
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

  it('falls back to done.answer when no message delta was streamed', async () => {
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
        response_type: 'general',
        answer: 'final answer from done payload',
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
        finalContent: 'final answer from done payload',
      }),
    );
  });

  it('syncs streamed content into the placeholder message during SSE envelopes', async () => {
    const syncStreamingMessage = vi.fn();
    const createSession = vi.fn().mockResolvedValue({
      id: 'session-1',
      title: 'session-1',
      status: 'active',
      messageCount: 0,
      createdAt: new Date().toISOString(),
    });

    const streamMessageMock = vi.mocked(streamMessage);
    streamMessageMock.mockImplementation(({ handlers }: any) => {
      handlers.onEnvelope?.({
        event: 'session_start',
        message_id: 'assistant-1',
        data: {
          session_id: 'session-1',
          task_type: 'compare',
        },
      });
      handlers.onEnvelope?.({
        event: 'message',
        message_id: 'assistant-1',
        data: {
          delta: 'streamed answer',
        },
      });
      handlers.onDone?.({
        finish_reason: 'stop',
        response_type: 'general',
        answer: 'streamed answer',
      });
    });

    const { result } = renderHook(() => useChatSend({
      input: 'hello',
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
      streamStateRef: {
        current: {
          streamStatus: 'streaming',
          contentBuffer: '',
          reasoningBuffer: '',
          toolTimeline: [],
          citations: [],
          tokensUsed: 0,
          cost: 0,
        } as any,
      },
      streamApi: {
        streamState: { streamStatus: 'idle' },
        setCurrentMessageId: vi.fn(),
        currentMessageId: null,
        startRun: vi.fn(),
        handleSSEEvent: vi.fn(),
        forceFlush: vi.fn(),
        dispatch: vi.fn(),
        getBufferedContent: vi.fn(() => ({ content: 'streamed answer', reasoning: '' })),
        stopRun: vi.fn(),
      } as any,
      addUserMessage: vi.fn(),
      addPlaceholderMessage: vi.fn(),
      rebindSessionId: vi.fn(),
      bindPlaceholderToMessageId: vi.fn(),
      syncStreamingMessage,
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

    expect(syncStreamingMessage).toHaveBeenCalledWith(
      'assistant-1',
      expect.objectContaining({
        content: 'streamed answer',
        reasoning: '',
        status: 'streaming',
        toolTimeline: [],
        citations: [],
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
        scope: expect.objectContaining({
          type: 'compare',
          paper_ids: ['p-001', 'p-002'],
        }),
        context: expect.objectContaining({
          auto_confirm: false,
          paper_ids: ['p-001', 'p-002'],
        }),
      }),
    );
  });

  it('forces a fresh session when handoff requires new session even if currentSession exists', async () => {
    const createSession = vi.fn().mockResolvedValue({
      id: 'session-new',
      title: 'session-new',
      status: 'active',
      messageCount: 0,
      createdAt: new Date().toISOString(),
    });
    const addUserMessage = vi.fn();
    const addPlaceholderMessage = vi.fn();
    const rebindSessionId = vi.fn();

    const streamMessageMock = vi.mocked(streamMessage);
    streamMessageMock.mockImplementation(({ handlers }: any) => {
      handlers.onDone?.({
        finish_reason: 'stop',
        response_type: 'general',
      });
    });

    const { result } = renderHook(() => useChatSend({
      input: 'fresh compare follow-up',
      sending: false,
      mode: 'rag',
      scope: { type: 'compare', id: 'p-001,p-002', title: 'Compare' },
      comparePaperIds: ['p-001', 'p-002'],
      scopeLoading: false,
      currentSession: {
        id: 'session-old',
        title: 'old',
        status: 'active',
        messageCount: 12,
        createdAt: new Date().toISOString(),
      },
      forceNewSessionForNextSend: true,
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
      rebindSessionId,
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

    expect(createSession).toHaveBeenCalledTimes(1);
    expect(addUserMessage).toHaveBeenCalledWith(expect.objectContaining({
      session_id: expect.stringMatching(/^pending-session-/),
    }));
    expect(addPlaceholderMessage).toHaveBeenCalledWith(expect.objectContaining({
      session_id: expect.stringMatching(/^pending-session-/),
    }));
    expect(rebindSessionId).toHaveBeenCalledWith(
      expect.stringMatching(/^pending-session-/),
      'session-new',
    );
    expect(streamMessageMock).toHaveBeenCalledWith(
      expect.objectContaining({
        sessionId: 'session-new',
      }),
    );
  });
});
