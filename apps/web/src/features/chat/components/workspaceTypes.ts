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
  quote_text?: string;
  source_offset_start?: number;
  source_offset_end?: number;
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
  claim_id?: string;
  claim_text?: string;
  claim_type?: string;
  claim: string;
  support_status: 'supported' | 'weakly_supported' | 'partially_supported' | 'unsupported';
  support_score?: number;
  supporting_source_chunk_ids: string[];
  repairable?: boolean;
  repair_hint?: string;
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
