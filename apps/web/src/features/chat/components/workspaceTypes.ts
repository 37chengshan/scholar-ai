import type { ChatMessage as SessionChatMessage } from '@/app/hooks/useSessions';
import type {
  StreamStatus,
  ToolTimelineItem as StreamToolTimelineItem,
} from '@/app/hooks/useChatStream';

export interface ToolTimelineItem extends StreamToolTimelineItem {}

export interface CitationItem {
  paper_id: string;
  title: string;
  authors?: string[];
  year?: number;
  snippet?: string;
  page?: number;
  score?: number;
  content_type?: 'text' | 'table' | 'figure';
  chunk_id?: string;
}

export interface ExtendedChatMessage extends SessionChatMessage {
  streamStatus?: StreamStatus;
  reasoningBuffer?: string;
  isThinkingExpanded?: boolean;
  toolTimeline?: ToolTimelineItem[];
  citations?: CitationItem[];
  tokensUsed?: number;
  cost?: number;
}
