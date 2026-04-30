import type { EvidenceBlockDto } from '../evidence/dto';
import type { CompareMatrixDto } from '../compare/dto';

export type ChatResponseType =
  | 'general'
  | 'rag'
  | 'compare'
  | 'review'
  | 'reading'
  | 'abstain'
  | 'error';

export interface AnswerClaimDto {
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

export interface AnswerCitationDto {
  paper_id: string;
  source_chunk_id: string;
  source_id?: string;
  page_num?: number | null;
  section_path?: string | null;
  title: string;
  authors?: string[];
  year?: number;
  anchor_text?: string;
  quote_text?: string;
  source_offset_start?: number | null;
  source_offset_end?: number | null;
  text_preview?: string;
  snippet?: string;
  page?: number;
  score?: number | null;
  content_type?: string;
  chunk_id?: string;
  citation_jump_url?: string;
}

export interface AnswerQualityDto {
  citation_coverage?: number;
  unsupported_claim_rate?: number;
  answer_evidence_consistency?: number;
  fallback_used?: boolean;
  fallback_reason?: string | null;
}

export interface AnswerContractDto {
  response_type: ChatResponseType;
  answer_mode: 'full' | 'partial' | 'abstain';
  answer?: string;
  claims: AnswerClaimDto[];
  citations: AnswerCitationDto[];
  evidence_blocks: EvidenceBlockDto[];
  quality: AnswerQualityDto;
  trace_id: string;
  run_id: string;
  retrieval_trace_id?: string;
  error_state?: string | null;
  trace?: Record<string, unknown>;
  compare_matrix?: CompareMatrixDto | null;
}
