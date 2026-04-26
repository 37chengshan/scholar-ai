import type { ChatMessage as SessionChatMessage } from '@/app/hooks/useSessions';
import type {
  StreamStatus,
  ToolTimelineItem as StreamToolTimelineItem,
} from '@/app/hooks/useChatStream';

export interface ToolTimelineItem extends StreamToolTimelineItem {}

export interface CitationItem {
  paper_id: string;
  source_chunk_id?: string;
  source_id?: string;
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

export interface EvidenceBlock {
  source_chunk_id: string;
  paper_id: string;
  page_num?: number | null;
  section_path?: string | null;
  content_type: 'text' | 'table' | 'figure' | 'caption' | 'page' | string;
  content: string;
  quality_score?: number;
}

export interface AnswerQuality {
  citation_coverage?: number;
  unsupported_claim_rate?: number;
  answer_evidence_consistency?: number;
  fallback_used?: boolean;
  fallback_reason?: string | null;
}

export interface AnswerContractPayload {
  answer_mode: 'full' | 'partial' | 'abstain';
  answer?: string;
  claims: AnswerClaim[];
  citations: CitationItem[];
  evidence_blocks: EvidenceBlock[];
  quality: AnswerQuality;
  retrieval_trace_id?: string;
  error_state?: string | null;
  trace?: Record<string, unknown>;
}

export interface ExtendedChatMessage extends SessionChatMessage {
  streamStatus?: StreamStatus;
  reasoningBuffer?: string;
  isThinkingExpanded?: boolean;
  toolTimeline?: ToolTimelineItem[];
  citations?: CitationItem[];
  tokensUsed?: number;
  cost?: number;
  answerContract?: AnswerContractPayload;
}
