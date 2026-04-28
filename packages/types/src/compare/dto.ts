import type { EvidenceBlockDto } from '../evidence/dto';

// ---------------------------------------------------------------------------
// Phase 4 Compare Matrix – canonical contract types
// ---------------------------------------------------------------------------

export interface CompareDimensionDto {
  id: string;
  label: string;
}

export type CompareCellSupportStatus =
  | 'supported'
  | 'partially_supported'
  | 'unsupported'
  | 'not_enough_evidence';

export interface CompareCellDto {
  dimension_id: string;
  content: string;
  support_status: CompareCellSupportStatus;
  evidence_blocks: EvidenceBlockDto[];
}

export interface CompareRowDto {
  paper_id: string;
  title: string;
  year?: number | null;
  cells: CompareCellDto[];
}

export interface CrossPaperInsightDto {
  claim: string;
  supporting_paper_ids: string[];
  evidence_blocks: EvidenceBlockDto[];
}

export interface CompareMatrixDto {
  paper_ids: string[];
  dimensions: CompareDimensionDto[];
  rows: CompareRowDto[];
  summary: string;
  cross_paper_insights: CrossPaperInsightDto[];
}
