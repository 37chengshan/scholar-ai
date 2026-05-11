import { useCallback, type MutableRefObject } from 'react';

import type { ChatStreamState } from '@/app/hooks/useChatStream';
import type { CitationItem, ToolTimelineItem } from '@/features/chat/components/workspaceTypes';

interface UseChatStreamingSyncOptions {
  getBufferedContent: () => { content: string; reasoning: string };
  patchStreamingMessage: (messageId: string, payload: {
    content: string;
    reasoning: string;
    status: ChatStreamState['streamStatus'];
    toolTimeline: ToolTimelineItem[];
    citations: CitationItem[];
  }) => void;
  streamStateRef: MutableRefObject<ChatStreamState>;
}

const safeToolTimeline = (toolTimeline?: ToolTimelineItem[]) => (toolTimeline ?? []).filter(Boolean);
const safeCitations = (citations?: CitationItem[]) => (citations ?? []).filter(Boolean);

export function useChatStreamingSync({
  getBufferedContent,
  patchStreamingMessage,
  streamStateRef,
}: UseChatStreamingSyncOptions) {
  return useCallback((messageId: string) => {
    if (!messageId) {
      return;
    }

    const buffered = getBufferedContent();
    patchStreamingMessage(messageId, {
      content: buffered.content,
      reasoning: buffered.reasoning,
      status: streamStateRef.current.streamStatus,
      toolTimeline: safeToolTimeline(streamStateRef.current.toolTimeline).map((timelineItem) => ({
        id: timelineItem.id,
        tool: timelineItem.tool,
        label: timelineItem.label,
        status: timelineItem.status,
        startedAt: timelineItem.startedAt,
        completedAt: timelineItem.completedAt,
        duration: timelineItem.duration,
        summary: timelineItem.summary,
      })),
      citations: safeCitations(streamStateRef.current.citations).map((citation) => ({
        paper_id: citation.paper_id,
        source_id: citation.source_id,
        page_num: citation.page_num,
        section_path: citation.section_path,
        anchor_text: citation.anchor_text,
        text_preview: citation.text_preview,
        title: citation.title,
        authors: citation.authors,
        year: citation.year,
        snippet: citation.snippet,
        page: citation.page,
        score: citation.score,
        content_type: citation.content_type,
      })),
    });
  }, [getBufferedContent, patchStreamingMessage, streamStateRef]);
}
