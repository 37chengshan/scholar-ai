import type { ChatMessage as SessionChatMessage } from '@/app/hooks/useSessions';
import type {
  StreamStatus,
  ToolTimelineItem as StreamToolTimelineItem,
} from '@/app/hooks/useChatStream';
import type {
  AnswerContractDto,
  AnswerQualityDto,
  ChatResponseType as SharedChatResponseType,
  EvidenceBlockDto,
} from '@scholar-ai/types';

export interface ToolTimelineItem extends StreamToolTimelineItem {}

export type ChatResponseType = SharedChatResponseType | 'system';

export interface CitationItem {
  paper_id: string;
  source_chunk_id?: string;
  source_id?: string;
  citation_jump_url?: string;
  page_num?: number;
  section_path?: string;
  anchor_text?: string;
  text_preview?: string;
  title: string;
  authors?: string[];
  year?: number;
  snippet?: string;
  page?: number;
  score?: number;
  content_type?: 'text' | 'table' | 'figure';
  chunk_id?: string;
}

export interface AnswerClaim {
  claim: string;
  support_status: 'supported' | 'partially_supported' | 'unsupported';
  supporting_source_chunk_ids: string[];
}

export type EvidenceBlock = EvidenceBlockDto;

export type AnswerQuality = AnswerQualityDto;

export interface AnswerContractPayload extends Omit<AnswerContractDto, 'claims' | 'citations' | 'evidence_blocks' | 'response_type' | 'quality'> {
  response_type: ChatResponseType;
  claims: AnswerClaim[];
  citations: CitationItem[];
  evidence_blocks: EvidenceBlock[];
  quality: AnswerQuality;
}

export interface ExtendedChatMessage extends SessionChatMessage {
  streamStatus?: StreamStatus;
  responseType?: ChatResponseType;
  reasoningBuffer?: string;
  isThinkingExpanded?: boolean;
  toolTimeline?: ToolTimelineItem[];
  citations?: CitationItem[];
  tokensUsed?: number;
  cost?: number;
  answerContract?: AnswerContractPayload;
}
