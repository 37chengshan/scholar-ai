import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ChatMessage as SessionChatMessage } from '@/app/hooks/useSessions';
import type { ChatStreamState } from '@/app/hooks/useChatStream';
import type { CitationItem, ExtendedChatMessage, ToolTimelineItem } from '@/features/chat/components/workspaceTypes';

export interface ChatRenderMessage extends ExtendedChatMessage {
  displayContent: string;
  displayReasoning: string;
  displayToolTimeline: ToolTimelineItem[];
  displayCitations: CitationItem[];
  isStreaming: boolean;
  isPlaceholder: boolean;
}

interface CompleteStreamingPayload {
  doneMessageId: string;
  fallbackMessageId: string;
  sessionId: string;
  finalContent: string;
  finalReasoning: string;
  tokensUsed: number;
  cost: number;
  toolTimeline: ToolTimelineItem[];
  citations: CitationItem[];
}

interface UseChatMessagesViewModelOptions {
  sessionMessages: SessionChatMessage[];
  streamState: ChatStreamState;
  streamingMessageId: string | null;
}

function dedupeMessages(messages: SessionChatMessage[]): ExtendedChatMessage[] {
  return Array.from(new Map(messages.map((message) => [message.id, { ...message }])).values());
}

export function useChatMessagesViewModel({
  sessionMessages,
  streamState,
  streamingMessageId,
}: UseChatMessagesViewModelOptions) {
  const [localMessages, setLocalMessages] = useState<ExtendedChatMessage[]>([]);
  const [placeholderId, setPlaceholderId] = useState<string | null>(null);

  useEffect(() => {
    if (placeholderId) {
      return;
    }
    setLocalMessages(dedupeMessages(sessionMessages));
  }, [sessionMessages, placeholderId]);

  const resetForSessionSwitch = useCallback(() => {
    setLocalMessages([]);
    setPlaceholderId(null);
  }, []);

  const addUserMessage = useCallback((message: ExtendedChatMessage) => {
    setLocalMessages((prev) => [...prev, message]);
  }, []);

  const addPlaceholderMessage = useCallback((message: ExtendedChatMessage) => {
    setLocalMessages((prev) => [...prev, message]);
    setPlaceholderId(message.id);
  }, []);

  const rebindSessionId = useCallback((fromSessionId: string, toSessionId: string) => {
    if (!fromSessionId || !toSessionId || fromSessionId === toSessionId) {
      return;
    }
    setLocalMessages((prev) => prev.map((message) => (
      message.session_id === fromSessionId
        ? { ...message, session_id: toSessionId }
        : message
    )));
  }, []);

  const bindPlaceholderToMessageId = useCallback((nextMessageId: string, previousPlaceholderId: string) => {
    setLocalMessages((prev) => prev.map((message) => (
      message.id === previousPlaceholderId
        ? { ...message, id: nextMessageId }
        : message
    )));
    setPlaceholderId(nextMessageId);
  }, []);

  const syncStreamingMessage = useCallback((messageId: string, payload: {
    content: string;
    reasoning: string;
    status: ExtendedChatMessage['streamStatus'];
    toolTimeline: ToolTimelineItem[];
    citations: CitationItem[];
  }) => {
    setLocalMessages((prev) => prev.map((message) => {
      if (message.id !== messageId) {
        return message;
      }
      return {
        ...message,
        content: payload.content,
        reasoningBuffer: payload.reasoning,
        streamStatus: payload.status,
        toolTimeline: payload.toolTimeline,
        citations: payload.citations,
      };
    }));
  }, []);

  const markStreamError = useCallback((messageId: string) => {
    setLocalMessages((prev) => prev.map((message) => (
      message.id === messageId
        ? { ...message, streamStatus: 'error' }
        : message
    )));
    setPlaceholderId(null);
  }, []);

  const markStreamCancelled = useCallback((messageId: string) => {
    setLocalMessages((prev) => prev.map((message) => (
      message.id === messageId
        ? { ...message, streamStatus: 'cancelled' }
        : message
    )));
    setPlaceholderId(null);
  }, []);

  const completeStreamingMessage = useCallback((payload: CompleteStreamingPayload) => {
    setLocalMessages((prev) => {
      const targetMessageId = payload.doneMessageId || payload.fallbackMessageId;
      let matched = false;

      const next = prev.map((message) => {
        if (message.id !== targetMessageId) {
          return message;
        }
        matched = true;
        return {
          ...message,
          id: payload.doneMessageId || message.id,
          content: payload.finalContent,
          reasoningBuffer: payload.finalReasoning,
          streamStatus: 'completed' as const,
          tokensUsed: payload.tokensUsed,
          cost: payload.cost,
          toolTimeline: payload.toolTimeline,
          citations: payload.citations,
        };
      });

      if (matched) {
        return next;
      }

      if (!payload.doneMessageId) {
        return next;
      }

      return [
        ...next,
        {
          id: payload.doneMessageId,
          session_id: payload.sessionId,
          role: 'assistant',
          content: payload.finalContent,
          created_at: new Date().toISOString(),
          reasoningBuffer: payload.finalReasoning,
          streamStatus: 'completed' as const,
          tokensUsed: payload.tokensUsed,
          cost: payload.cost,
          toolTimeline: payload.toolTimeline,
          citations: payload.citations,
        },
      ];
    });

    setPlaceholderId(null);
  }, []);

  const removePlaceholderMessage = useCallback(() => {
    setLocalMessages((prev) => prev.filter((message) => message.id !== placeholderId));
    setPlaceholderId(null);
  }, [placeholderId]);

  const clearPlaceholder = useCallback(() => {
    setPlaceholderId(null);
  }, []);

  const renderMessages = useMemo<ChatRenderMessage[]>(() => {
    return localMessages
      .filter((message) => message.role === 'user' || message.role === 'assistant')
      .map((message) => {
        const isStreaming = message.streamStatus === 'streaming';
        const isAssistant = message.role === 'assistant';
        const isPlaceholder = message.id.startsWith('placeholder-') || message.id === streamingMessageId;

        const displayContent = isStreaming && isAssistant && message.id === streamingMessageId
          ? (streamState.contentBuffer || message.content || '')
          : (message.content || '');

        const displayReasoning = isStreaming && isAssistant && message.id === streamingMessageId
          ? (streamState.reasoningBuffer || message.reasoningBuffer || '')
          : (message.reasoningBuffer || '');

        const displayToolTimeline = isStreaming && isAssistant && message.id === streamingMessageId
          ? ((streamState.toolTimeline || message.toolTimeline || []) as ToolTimelineItem[])
          : ((message.toolTimeline || []) as ToolTimelineItem[]);

        const displayCitations = isStreaming && isAssistant && message.id === streamingMessageId
          ? ((streamState.citations || message.citations || []) as CitationItem[])
          : ((message.citations || []) as CitationItem[]);

        return {
          ...message,
          displayContent,
          displayReasoning,
          displayToolTimeline,
          displayCitations,
          isStreaming,
          isPlaceholder,
        };
      });
  }, [localMessages, streamState.citations, streamState.contentBuffer, streamState.reasoningBuffer, streamState.toolTimeline, streamingMessageId]);

  return {
    renderMessages,
    placeholderId,
    addUserMessage,
    addPlaceholderMessage,
    bindPlaceholderToMessageId,
    rebindSessionId,
    syncStreamingMessage,
    markStreamError,
    markStreamCancelled,
    completeStreamingMessage,
    removePlaceholderMessage,
    clearPlaceholder,
    resetForSessionSwitch,
  };
}
