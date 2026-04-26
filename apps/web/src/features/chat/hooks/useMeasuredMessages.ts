import { useMemo } from 'react';
import { DEFAULT_TEXT_FONT, measureText } from '@/lib/text-layout';
import type { ChatRenderMessage } from '@/features/chat/hooks/useChatMessagesViewModel';

export function useMeasuredMessages(messages: ChatRenderMessage[]) {
  return useMemo(() => {
    const heightMap: Record<string, number> = {};

    messages.forEach((message) => {
      const width = message.role === 'assistant' ? 640 : 420;
      const content = message.displayContent || '';
      const measured = measureText({
        text: content,
        width,
        font: DEFAULT_TEXT_FONT,
        whiteSpace: 'pre-wrap',
      });
      const base = message.role === 'assistant' ? 74 : 52;
      const citationsBlock = (message.displayCitations?.length || 0) > 0 ? 18 : 0;
      heightMap[message.id] = Math.ceil(measured.height + base + citationsBlock);
    });

    return heightMap;
  }, [messages]);
}
