export type EvidenceSourceType = 'paper' | 'note' | 'web' | 'user_upload';

export type EvidenceContentType =
  | 'text'
  | 'table'
  | 'figure'
  | 'caption'
  | 'formula'
  | 'page';

export type EvidenceSupportStatus =
  | 'supported'
  | 'partially_supported'
  | 'unsupported';

export interface EvidenceBlockDto {
  evidence_id: string;
  source_type: EvidenceSourceType;
  paper_id: string;
  source_chunk_id: string;
  page_num?: number | null;
  section_path?: string | null;
  content_type: EvidenceContentType | string;
  text: string;
  score?: number | null;
  rerank_score?: number | null;
  support_status?: EvidenceSupportStatus | null;
  citation_jump_url: string;
  user_comment?: string | null;
}

export interface EvidenceSourceDto {
  evidence_id: string;
  source_type: EvidenceSourceType;
  source_chunk_id: string;
  paper_id: string;
  page_num?: number | null;
  section_path?: string | null;
  content_type?: EvidenceContentType | string;
  anchor_text?: string;
  content?: string;
  citation_jump_url: string;
  read_url?: string;
  pdf_url?: string;
}
