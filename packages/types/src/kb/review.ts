import type { EvidenceBlockDto } from '../evidence/dto';

export type ReviewDraftStatus = 'idle' | 'running' | 'completed' | 'failed' | 'partial';
export type ReviewErrorState =
  | 'insufficient_evidence'
  | 'graph_unavailable'
  | 'validation_failed'
  | 'writer_failed'
  | 'partial_draft';

export interface ReviewOutlineSectionDto {
  title: string;
  intent: string;
  supporting_paper_ids: string[];
  seed_evidence: EvidenceBlockDto[];
}

export interface ReviewOutlineDocDto {
  research_question: string;
  themes: string[];
  sections: ReviewOutlineSectionDto[];
}

export interface ReviewDraftParagraphDto {
  paragraph_id: string;
  text: string;
  citations: Array<Record<string, unknown>>;
  evidence_blocks: EvidenceBlockDto[];
  claim_verification?: Array<{
    claim_id: string;
    claim_text: string;
    claim_type?: string;
    support_status: 'supported' | 'weakly_supported' | 'partially_supported' | 'unsupported';
    support_score?: number;
    supporting_evidence_ids?: string[];
    repairable?: boolean;
    repair_hint?: string;
  }>;
  citation_coverage_status: 'covered' | 'insufficient';
}

export interface ReviewDraftSectionDto {
  heading: string;
  paragraphs: ReviewDraftParagraphDto[];
  omitted_reason?: string | null;
}

export interface ReviewDraftDocDto {
  sections: ReviewDraftSectionDto[];
}

export interface ReviewDraftQualityDto {
  citation_coverage: number;
  unsupported_paragraph_rate: number;
  graph_assist_used: boolean;
  fallback_used: boolean;
}

export interface ReviewDraftDto {
  id: string;
  knowledgeBaseId: string;
  title: string;
  status: ReviewDraftStatus;
  sourcePaperIds: string[];
  outlineDoc: ReviewOutlineDocDto;
  draftDoc: ReviewDraftDocDto;
  quality: ReviewDraftQualityDto;
  traceId: string;
  runId: string;
  errorState?: ReviewErrorState | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateReviewDraftRequestDto {
  paper_ids?: string[];
  mode: 'outline_and_draft';
  question?: string;
  target_review_draft_id?: string;
}

export interface ReviewClaimRepairRequestDto {
  paragraph_id: string;
  claim_id: string;
}

export interface ReviewRunSummaryDto {
  id: string;
  knowledgeBaseId: string;
  reviewDraftId?: string | null;
  status: string;
  scope: string;
  traceId: string;
  errorState?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ReviewRunDetailDto extends ReviewRunSummaryDto {
  inputPayload: Record<string, unknown>;
  steps: Array<Record<string, unknown>>;
  toolEvents: Array<Record<string, unknown>>;
  artifacts: Array<Record<string, unknown>>;
  evidence: Array<Record<string, unknown>>;
  recoveryActions: Array<Record<string, unknown>>;
}
