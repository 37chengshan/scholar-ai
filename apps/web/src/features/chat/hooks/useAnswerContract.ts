import { useMemo } from 'react';
import type { AnswerContractPayload } from '@/features/chat/components/workspaceTypes';
import type { ChatRenderMessage } from '@/features/chat/hooks/useChatMessagesViewModel';

export function useAnswerContract(message: ChatRenderMessage): AnswerContractPayload | null {
  return useMemo(() => {
    if (message.answerContract) {
      return message.answerContract;
    }

    if (message.role !== 'assistant') {
      return null;
    }

    const citations = message.displayCitations || [];
    if (!message.displayContent && citations.length === 0) {
      return null;
    }

    return {
      answer_mode: citations.length > 0 ? 'partial' : 'abstain',
      answer: message.displayContent,
      claims: [],
      citations,
      evidence_blocks: citations.map((citation) => ({
        source_chunk_id: citation.source_chunk_id || citation.chunk_id || citation.source_id || '',
        paper_id: citation.paper_id,
        page_num: citation.page_num || citation.page || null,
        section_path: citation.section_path || null,
        content_type: citation.content_type || 'text',
        content: citation.text_preview || citation.snippet || citation.anchor_text || '',
      })),
      quality: {
        fallback_used: false,
      },
      retrieval_trace_id: undefined,
      error_state: null,
    };
  }, [message.answerContract, message.displayCitations, message.displayContent, message.role]);
}
