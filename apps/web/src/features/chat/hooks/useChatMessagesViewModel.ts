import { useMemo } from 'react';
import { ChatMessage as SessionChatMessage } from '@/app/hooks/useSessions';
import { StreamStatus } from '@/app/hooks/useChatStream';

interface ChatMessageViewModel extends SessionChatMessage {
  isStreaming: boolean;
  isAssistant: boolean;
  displayContent: string;
}

export function useChatMessagesViewModel(
  messages: SessionChatMessage[],
  streamStatus?: StreamStatus
): ChatMessageViewModel[] {
  return useMemo(
    () => messages.map((message) => ({
      ...message,
      isStreaming: message.role === 'assistant' && streamStatus === 'streaming',
      isAssistant: message.role === 'assistant',
      displayContent: message.content || '',
    })),
    [messages, streamStatus]
  );
}
