import { useCallback } from 'react';
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import { toast } from 'sonner';
import { streamMessage as streamChatMessage } from '@/services/chatApi';
import { SSEService, SSEEventEnvelope } from '@/services/sseService';
import type { ChatSession } from '@/app/hooks/useSessions';
import type { ChatStreamState, TaskType } from '@/app/hooks/useChatStream';
import type {
  AnswerContractPayload,
  CitationItem,
  ExtendedChatMessage,
  ToolTimelineItem,
} from '@/features/chat/components/workspaceTypes';
import type { AgentUIState } from '@/app/components/AgentStateSidebar';
import type { ScopeType } from '@/app/components/ScopeBanner';
import type { useChatStreaming } from '@/features/chat/hooks/useChatStreaming';

interface ChatScope {
  type: ScopeType;
  id: string | null;
  title?: string;
  errorMessage?: string;
}

interface UseChatSendOptions {
  input: string;
  sending: boolean;
  mode: 'auto' | 'rag' | 'agent';
  scope: ChatScope;
  scopeLoading: boolean;
  currentSession: ChatSession | null;
  isZh: boolean;
  setInput: (value: string) => void;
  setSending: (sending: boolean) => void;
  setAgentUIState: (state: AgentUIState) => void;
  setSessionTokens: Dispatch<SetStateAction<number>>;
  setSessionCost: Dispatch<SetStateAction<number>>;
  createSession: (title?: string) => Promise<ChatSession | null>;
  sendLockRef: MutableRefObject<boolean>;
  sseServiceRef: MutableRefObject<SSEService | null>;
  currentMessageIdRef: MutableRefObject<string>;
  streamStateRef: MutableRefObject<ChatStreamState>;
  streamApi: ReturnType<typeof useChatStreaming>;
  addUserMessage: (message: ExtendedChatMessage) => void;
  addPlaceholderMessage: (message: ExtendedChatMessage) => void;
  rebindSessionId: (fromSessionId: string, toSessionId: string) => void;
  bindPlaceholderToMessageId: (nextMessageId: string, previousPlaceholderId: string) => void;
  syncStreamingMessage: (messageId: string) => void;
  ingestRuntimeEvent?: (event: SSEEventEnvelope) => void;
  markStreamError: (messageId: string) => void;
  markStreamCancelled: (messageId: string) => void;
  completeStreamingMessage: (payload: {
    doneMessageId: string;
    fallbackMessageId: string;
    sessionId: string;
    finalContent: string;
    finalReasoning: string;
    tokensUsed: number;
    cost: number;
    toolTimeline: ToolTimelineItem[];
    citations: CitationItem[];
    answerContract?: AnswerContractPayload;
  }) => void;
  removePlaceholderMessage: () => void;
  clearPlaceholder: () => void;
}

export function useChatSend({
  input,
  sending,
  mode,
  scope,
  scopeLoading,
  currentSession,
  isZh,
  setInput,
  setSending,
  setAgentUIState,
  setSessionTokens,
  setSessionCost,
  createSession,
  sendLockRef,
  sseServiceRef,
  currentMessageIdRef,
  streamStateRef,
  streamApi,
  addUserMessage,
  addPlaceholderMessage,
  rebindSessionId,
  bindPlaceholderToMessageId,
  syncStreamingMessage,
  ingestRuntimeEvent,
  markStreamError,
  markStreamCancelled,
  completeStreamingMessage,
  removePlaceholderMessage,
  clearPlaceholder,
}: UseChatSendOptions) {
  const normalizeAnswerContract = useCallback((payload: Record<string, unknown> | undefined, fallbackContent: string, fallbackCitations: CitationItem[]): AnswerContractPayload | undefined => {
    if (!payload) {
      return undefined;
    }

    const citationsRaw = Array.isArray(payload.citations) ? payload.citations : fallbackCitations;
    const citations = citationsRaw.map((item) => {
      const row = item as Record<string, unknown>;
      return {
        paper_id: String(row.paper_id || ''),
        source_chunk_id: row.source_chunk_id ? String(row.source_chunk_id) : undefined,
        source_id: row.source_id ? String(row.source_id) : undefined,
        page_num: typeof row.page_num === 'number' ? row.page_num : undefined,
        section_path: row.section_path ? String(row.section_path) : undefined,
        anchor_text: row.anchor_text ? String(row.anchor_text) : undefined,
        text_preview: row.text_preview ? String(row.text_preview) : undefined,
        title: String(row.title || row.paper_title || 'source'),
        authors: Array.isArray(row.authors) ? row.authors.map((a) => String(a)) : undefined,
        year: typeof row.year === 'number' ? row.year : undefined,
        snippet: row.snippet ? String(row.snippet) : undefined,
        page: typeof row.page === 'number' ? row.page : undefined,
        score: typeof row.score === 'number' ? row.score : undefined,
        content_type: (row.content_type as CitationItem['content_type']) || 'text',
        chunk_id: row.chunk_id ? String(row.chunk_id) : undefined,
      } as CitationItem;
    });

    const claimsRaw = Array.isArray(payload.claims) ? payload.claims : [];
    const evidenceRaw = Array.isArray(payload.evidence_blocks) ? payload.evidence_blocks : [];
    const quality = (payload.quality as Record<string, unknown> | undefined) || {};
    const answerMode = (payload.answer_mode as 'full' | 'partial' | 'abstain' | undefined) || 'partial';

    return {
      answer_mode: answerMode,
      answer: String(payload.answer || fallbackContent || ''),
      claims: claimsRaw.map((item) => {
        const row = item as Record<string, unknown>;
        return {
          claim: String(row.claim || ''),
          support_status: (row.support_status as 'supported' | 'partially_supported' | 'unsupported') || 'unsupported',
          supporting_source_chunk_ids: Array.isArray(row.supporting_source_chunk_ids)
            ? row.supporting_source_chunk_ids.map((id) => String(id))
            : [],
        };
      }),
      citations,
      evidence_blocks: evidenceRaw.map((item) => {
        const row = item as Record<string, unknown>;
        return {
          source_chunk_id: String(row.source_chunk_id || ''),
          paper_id: String(row.paper_id || ''),
          page_num: typeof row.page_num === 'number' ? row.page_num : null,
          section_path: row.section_path ? String(row.section_path) : null,
          content_type: String(row.content_type || 'text'),
          content: String(row.content || ''),
          quality_score: typeof row.quality_score === 'number' ? row.quality_score : undefined,
        };
      }),
      quality: {
        citation_coverage: typeof quality.citation_coverage === 'number' ? quality.citation_coverage : undefined,
        unsupported_claim_rate: typeof quality.unsupported_claim_rate === 'number' ? quality.unsupported_claim_rate : undefined,
        answer_evidence_consistency:
          typeof quality.answer_evidence_consistency === 'number' ? quality.answer_evidence_consistency : undefined,
        fallback_used: Boolean(quality.fallback_used),
        fallback_reason: quality.fallback_reason ? String(quality.fallback_reason) : null,
      },
      retrieval_trace_id: payload.retrieval_trace_id ? String(payload.retrieval_trace_id) : undefined,
      error_state: payload.error_state ? String(payload.error_state) : null,
      trace: (payload.trace as Record<string, unknown> | undefined) || undefined,
    };
  }, []);

  const handleSend = useCallback(async () => {
    if (
      !input.trim()
      || scopeLoading
      || streamApi.streamState.streamStatus === 'streaming'
      || sending
      || sendLockRef.current
    ) {
      if (scopeLoading) {
        toast.message(isZh ? '正在校验作用域，请稍候' : 'Validating scope, please wait');
      }
      return;
    }

    if (scope.type === 'error') {
      toast.error(scope.errorMessage || '当前作用域无效');
      return;
    }

    setSending(true);
    sendLockRef.current = true;

    try {
      const pendingSessionId = `pending-session-${Date.now()}`;
      let sessionId = currentSession?.id || pendingSessionId;

      const userMessage: ExtendedChatMessage = {
        id: `user-${Date.now()}`,
        session_id: sessionId,
        role: 'user',
        content: input.trim(),
        created_at: new Date().toISOString(),
      };

      addUserMessage(userMessage);

      const placeholderMessageId = `placeholder-${Date.now()}`;
      const placeholderMessage: ExtendedChatMessage = {
        id: placeholderMessageId,
        session_id: sessionId,
        role: 'assistant',
        content: mode === 'agent'
          ? (isZh ? '正在分析...' : 'Analyzing...')
          : (isZh ? '正在检索...' : 'Retrieving...'),
        created_at: new Date().toISOString(),
        streamStatus: 'streaming',
        reasoningBuffer: '',
        isThinkingExpanded: true,
        toolTimeline: [],
        citations: [],
      };

      addPlaceholderMessage(placeholderMessage);
      streamApi.setCurrentMessageId(null);
      currentMessageIdRef.current = '';

      setInput('');

      if (!currentSession?.id) {
        const newSession = await createSession(input.trim().substring(0, 50));
        if (!newSession) {
          removePlaceholderMessage();
          clearPlaceholder();
          setSending(false);
          sendLockRef.current = false;
          return;
        }
        sessionId = newSession.id;
        rebindSessionId(pendingSessionId, sessionId);
      }

      if (!sseServiceRef.current) {
        sseServiceRef.current = new SSEService();
      }

      const streamScope =
        scope.type === 'single_paper' && scope.id
          ? {
              type: 'paper' as const,
              paper_id: scope.id,
            }
          : scope.type === 'full_kb' && scope.id
            ? {
                type: 'knowledge_base' as const,
                knowledge_base_id: scope.id,
              }
            : {
                type: 'general' as const,
              };

      streamChatMessage({
        sessionId,
        message: input.trim(),
        mode,
        scope: streamScope,
        context: {
          auto_confirm: false,
        },
        streamService: sseServiceRef.current,
        handlers: {
          onEnvelope: (event: SSEEventEnvelope) => {
            const eventType = event.event || '';
            const eventMessageId = event.message_id || '';
            const eventData = (event.data ?? {}) as Record<string, unknown>;

            if (eventType === 'session_start' && eventMessageId) {
              streamApi.setCurrentMessageId(eventMessageId);
              currentMessageIdRef.current = eventMessageId;

              const nextSessionId = (eventData.session_id as string) || '';
              const taskType = ((eventData.task_type as TaskType) || 'general') as TaskType;
              streamApi.startRun(nextSessionId, taskType, eventMessageId);
              bindPlaceholderToMessageId(eventMessageId, placeholderMessageId);
              return;
            }

            if (!eventMessageId && eventType !== 'heartbeat') {
              return;
            }

            if (
              eventMessageId
              && currentMessageIdRef.current
              && eventMessageId !== currentMessageIdRef.current
            ) {
              return;
            }

            ingestRuntimeEvent?.(event);

            streamApi.handleSSEEvent({
              message_id: eventMessageId,
              event_type: eventType,
              data: eventData,
              timestamp: Date.now(),
            });
            syncStreamingMessage(currentMessageIdRef.current || eventMessageId);
          },
          onError: (error: Error) => {
            streamApi.forceFlush();
            streamApi.dispatch({
              type: 'ERROR',
              code: 'STREAM_ERROR',
              message: error.message,
            });

            const targetMessageId = currentMessageIdRef.current || streamApi.currentMessageId;
            if (targetMessageId) {
              markStreamError(targetMessageId);
            } else {
              removePlaceholderMessage();
            }
            clearPlaceholder();
            currentMessageIdRef.current = '';
            streamApi.setCurrentMessageId(null);
            setAgentUIState('DONE');
            setSending(false);
            sendLockRef.current = false;
          },
          onDone: (data) => {
            const latestState = streamStateRef.current;
            const finalBuffered = streamApi.getBufferedContent();
            const tokensUsed = data?.tokens_used ?? latestState.tokensUsed;
            const cost = data?.cost ?? latestState.cost;
            const durationMs = data?.total_time_ms || 0;

            streamApi.forceFlush();
            streamApi.dispatch({
              type: 'STREAM_COMPLETE',
              tokensUsed,
              cost,
              durationMs,
            });

            const doneMsgId = currentMessageIdRef.current || streamApi.currentMessageId || '';
            const finalContent = finalBuffered.content || latestState.contentBuffer;
            const finalReasoning = finalBuffered.reasoning || latestState.reasoningBuffer;
            const answerContract = normalizeAnswerContract(
              data as unknown as Record<string, unknown>,
              finalContent,
              latestState.citations,
            );

            completeStreamingMessage({
              doneMessageId: doneMsgId,
              fallbackMessageId: placeholderMessageId,
              sessionId: sessionId || currentSession?.id || '',
              finalContent,
              finalReasoning,
              tokensUsed,
              cost,
              toolTimeline: latestState.toolTimeline,
              citations: latestState.citations,
              answerContract,
            });

            setSessionTokens((prev) => prev + tokensUsed);
            setSessionCost((prev) => prev + cost);

            clearPlaceholder();
            currentMessageIdRef.current = '';
            streamApi.setCurrentMessageId(null);
            setAgentUIState('DONE');
            setSending(false);
            sendLockRef.current = false;
          },
        },
      });
    } catch (error) {
      toast.error(isZh ? '发送消息失败' : 'Failed to send message');
      removePlaceholderMessage();
      clearPlaceholder();
      currentMessageIdRef.current = '';
      streamApi.setCurrentMessageId(null);
      setSending(false);
      sendLockRef.current = false;
    }
  }, [
    input,
    streamApi,
    sending,
    sendLockRef,
    scope,
    scopeLoading,
    setSending,
    currentSession,
    createSession,
    addUserMessage,
    mode,
    isZh,
    addPlaceholderMessage,
    setInput,
    rebindSessionId,
    sseServiceRef,
    currentMessageIdRef,
    streamStateRef,
    bindPlaceholderToMessageId,
    syncStreamingMessage,
    ingestRuntimeEvent,
    markStreamError,
    setAgentUIState,
    completeStreamingMessage,
    setSessionTokens,
    setSessionCost,
    removePlaceholderMessage,
    clearPlaceholder,
    normalizeAnswerContract,
  ]);

  const handleStop = useCallback(() => {
    if (!sseServiceRef.current) {
      return;
    }

    sseServiceRef.current.disconnect();
    streamApi.stopRun('User stopped');
    streamApi.forceFlush();

    const targetMessageId = currentMessageIdRef.current || streamApi.currentMessageId;
    if (targetMessageId) {
      markStreamCancelled(targetMessageId);
    } else {
      removePlaceholderMessage();
    }
    clearPlaceholder();
    currentMessageIdRef.current = '';
    streamApi.setCurrentMessageId(null);
    setAgentUIState('DONE');
    setSending(false);
    sendLockRef.current = false;
  }, [
    sseServiceRef,
    streamApi,
    markStreamCancelled,
    currentMessageIdRef,
    removePlaceholderMessage,
    clearPlaceholder,
    setAgentUIState,
    setSending,
    sendLockRef,
  ]);

  return {
    handleSend,
    handleStop,
  };
}
