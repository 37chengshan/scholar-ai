import { useCallback } from 'react';
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import { toast } from 'sonner';
import { streamMessage as streamChatMessage } from '@/services/chatApi';
import { SSEService, SSEEventEnvelope } from '@/services/sseService';
import type { ChatSession } from '@/app/hooks/useSessions';
import type { ChatStreamState, TaskType } from '@/app/hooks/useChatStream';
import type {
  AnswerContractPayload,
  ChatResponseType,
  CitationItem,
  EvidenceBlock,
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
  comparePaperIds?: string[];
  scopeLoading: boolean;
  currentSession: ChatSession | null;
  forceNewSessionForNextSend?: boolean;
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
    responseType?: ChatResponseType;
    answerContract?: AnswerContractPayload;
  }) => void;
  removePlaceholderMessage: () => void;
  clearPlaceholder: () => void;
  onSessionCreated?: (sessionId: string) => void;
}

export function useChatSend({
  input,
  sending,
  mode,
  scope,
  comparePaperIds,
  scopeLoading,
  currentSession,
  forceNewSessionForNextSend = false,
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
  onSessionCreated,
}: UseChatSendOptions) {
  const normalizeAnswerContract = useCallback((payload: Record<string, unknown> | undefined, fallbackContent: string, fallbackCitations: CitationItem[]): AnswerContractPayload | undefined => {
    if (!payload) {
      return undefined;
    }

    const responseType = payload.response_type ? String(payload.response_type) as ChatResponseType : undefined;
    if (responseType && !['rag', 'reading', 'compare', 'review', 'abstain'].includes(responseType)) {
      return undefined;
    }

    const citationsRaw = Array.isArray(payload.citations) ? payload.citations : fallbackCitations;
    const evidenceRaw = Array.isArray(payload.evidence_blocks) ? payload.evidence_blocks : [];
    const hasRagSignal = (
      payload.answer_mode !== undefined
      || payload.retrieval_trace_id !== undefined
      || citationsRaw.length > 0
      || evidenceRaw.length > 0
    );

    if (!hasRagSignal) {
      return undefined;
    }

    const citations = citationsRaw.map((item) => {
      const row = item as Record<string, unknown>;
      return {
        paper_id: String(row.paper_id || ''),
        source_chunk_id: row.source_chunk_id ? String(row.source_chunk_id) : undefined,
        source_id: row.source_id
          ? String(row.source_id)
          : row.source_chunk_id
            ? String(row.source_chunk_id)
            : undefined,
        citation_jump_url: row.citation_jump_url ? String(row.citation_jump_url) : undefined,
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
    const quality = (payload.quality as Record<string, unknown> | undefined) || {};
    const answerMode = (payload.answer_mode as 'full' | 'partial' | 'abstain' | undefined)
      || (citationsRaw.length > 0 ? 'partial' : 'abstain');
    const compareMatrix = payload.compare_matrix && typeof payload.compare_matrix === 'object'
      ? payload.compare_matrix as AnswerContractPayload['compare_matrix']
      : undefined;

    return {
      response_type: responseType || 'rag',
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
          evidence_id: String(row.evidence_id || row.source_chunk_id || ''),
          source_type: String(row.source_type || 'paper') as EvidenceBlock['source_type'],
          paper_id: String(row.paper_id || ''),
          source_chunk_id: String(row.source_chunk_id || ''),
          page_num: typeof row.page_num === 'number' ? row.page_num : null,
          section_path: row.section_path ? String(row.section_path) : null,
          content_type: String(row.content_type || 'text'),
          text: String(row.text || row.content || ''),
          score: typeof row.score === 'number' ? row.score : undefined,
          rerank_score: typeof row.rerank_score === 'number' ? row.rerank_score : undefined,
          support_status: row.support_status
            ? String(row.support_status) as EvidenceBlock['support_status']
            : undefined,
          citation_jump_url: String(row.citation_jump_url || ''),
          user_comment: row.user_comment ? String(row.user_comment) : undefined,
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
      trace_id: payload.trace_id ? String(payload.trace_id) : String(payload.retrieval_trace_id || ''),
      run_id: payload.run_id ? String(payload.run_id) : '',
      retrieval_trace_id: payload.retrieval_trace_id ? String(payload.retrieval_trace_id) : undefined,
      error_state: payload.error_state ? String(payload.error_state) : null,
      trace: (payload.trace as Record<string, unknown> | undefined) || undefined,
      compare_matrix: compareMatrix,
    };
  }, []);

  const releaseSendState = useCallback(() => {
    clearPlaceholder();
    currentMessageIdRef.current = '';
    streamApi.setCurrentMessageId(null);
    setAgentUIState('DONE');
    setSending(false);
    sendLockRef.current = false;
  }, [clearPlaceholder, currentMessageIdRef, sendLockRef, setAgentUIState, setSending, streamApi]);

  const ensureSessionForSend = useCallback(async (title: string): Promise<string | null> => {
    if (!forceNewSessionForNextSend && currentSession?.id) {
      return currentSession.id;
    }

    const newSession = await createSession(title.substring(0, 50));
    if (!newSession?.id) {
      return null;
    }

    onSessionCreated?.(newSession.id);
    return newSession.id;
  }, [createSession, currentSession?.id, forceNewSessionForNextSend, onSessionCreated]);

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

      const sessionIdFromServer = await ensureSessionForSend(input.trim());
      if (!sessionIdFromServer) {
        removePlaceholderMessage();
        releaseSendState();
        return;
      }
      sessionId = sessionIdFromServer;
      rebindSessionId(pendingSessionId, sessionId);

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
          ...(comparePaperIds && comparePaperIds.length > 0
            ? { paper_ids: comparePaperIds }
            : {}),
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
            const responseType = ((data?.response_type as ChatResponseType | undefined)
              || (answerContract ? 'rag' : 'general'));

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
              responseType,
              answerContract,
            });

            setSessionTokens((prev) => prev + tokensUsed);
            setSessionCost((prev) => prev + cost);

            releaseSendState();
          },
        },
      });
    } catch (error) {
      toast.error(isZh ? '发送消息失败' : 'Failed to send message');
      removePlaceholderMessage();
      releaseSendState();
    }
  }, [
    input,
    streamApi,
    sending,
    sendLockRef,
    scope,
    comparePaperIds,
    scopeLoading,
    setSending,
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
    normalizeAnswerContract,
    ensureSessionForSend,
    releaseSendState,
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
    releaseSendState();
  }, [
    sseServiceRef,
    streamApi,
    markStreamCancelled,
    removePlaceholderMessage,
    releaseSendState,
  ]);

  return {
    handleSend,
    handleStop,
  };
}
