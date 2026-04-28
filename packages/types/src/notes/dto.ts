import type { EvidenceBlockDto } from '../evidence/dto';

export type NoteSourceType =
  | 'manual'
  | 'chat'
  | 'read'
  | 'search'
  | 'compare'
  | 'review';

export interface EditorDocumentDto {
  type: 'doc';
  content: Array<Record<string, unknown>>;
}

export interface NoteDto {
  id: string;
  userId: string;
  title: string;
  content: string;
  contentDoc: EditorDocumentDto;
  linkedEvidence: EvidenceBlockDto[];
  sourceType: NoteSourceType;
  tags: string[];
  paperIds: string[];
  createdAt: string;
  updatedAt: string;
}

export interface CreateNoteDto {
  title: string;
  content?: string;
  contentDoc?: EditorDocumentDto;
  linkedEvidence?: EvidenceBlockDto[];
  sourceType?: NoteSourceType;
  tags?: string[];
  paperIds?: string[];
}

export interface UpdateNoteDto {
  title?: string;
  content?: string;
  contentDoc?: EditorDocumentDto;
  linkedEvidence?: EvidenceBlockDto[];
  sourceType?: NoteSourceType;
  tags?: string[];
  paperIds?: string[];
}

export interface SaveEvidenceNoteRequestDto {
  claim: string;
  evidence_block: EvidenceBlockDto;
  target_note_id?: string;
  surface: Exclude<NoteSourceType, 'manual'>;
  user_comment?: string;
}
