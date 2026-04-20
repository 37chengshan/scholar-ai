import { useCallback } from 'react';
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import { toast } from 'sonner';
import { streamMessage as streamChatMessage } from '@/services/chatApi';
import { SSEService, SSEEventEnvelope } from '@/services/sseService';
import type { ChatSession } from '@/app/hooks/useSessions';
import type { ChatStreamState, TaskType } from '@/app/hooks/useChatStream';
import type {
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
  bindPlaceholderToMessageId: (nextMessageId: string, previousPlaceholderId: string) => void;
  syncStreamingMessage: (messageId: string) => void;
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
  bindPlaceholderToMessageId,
  syncStreamingMessage,
  markStreamError,
  markStreamCancelled,
  completeStreamingMessage,
  removePlaceholderMessage,
  clearPlaceholder,
}: UseChatSendOptions) {
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
      let sessionId = currentSession?.id;

      if (!sessionId) {
        const newSession = await createSession(input.trim().substring(0, 50));
        if (!newSession) {
          setSending(false);
          sendLockRef.current = false;
          return;
        }
        sessionId = newSession.id;
      }

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
    sseServiceRef,
    currentMessageIdRef,
    streamStateRef,
    bindPlaceholderToMessageId,
    syncStreamingMessage,
    markStreamError,
    setAgentUIState,
    completeStreamingMessage,
    setSessionTokens,
    setSessionCost,
    removePlaceholderMessage,
    clearPlaceholder,
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
