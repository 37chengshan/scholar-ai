import type { Note } from '@/services/notesApi';

export const AI_NOTE_TAG = '__ai_note__';
export const READ_WORKSPACE_NOTE_TAG = 'read-note';
export const EVIDENCE_NOTE_TAGS = ['evidence', 'citation'] as const;

export interface EditorDocument {
  type: 'doc';
  content: Array<Record<string, unknown>>;
}

export interface ReadingSummaryProjection {
  paperId: string;
  title: string;
  readingNotes: string;
  folderId: string | null;
}

export function createEmptyEditorDocument(): EditorDocument {
  return { type: 'doc', content: [] };
}

export function buildReadingNoteTitle(paperTitle: string | null | undefined, isZh: boolean): string {
  const safeTitle = paperTitle || (isZh ? '未命名论文' : 'Untitled Paper');
  return `${safeTitle} · ${isZh ? '阅读笔记' : 'Reading Notes'}`;
}

export function isSystemAiNote(note: Pick<Note, 'tags'>): boolean {
  return note.tags.includes(AI_NOTE_TAG);
}

export function filterUserEditableNotes(notes: Note[]): Note[] {
  return notes.filter((note) => !isSystemAiNote(note));
}

export function isReadingWorkspaceNote(note: Pick<Note, 'sourceType' | 'tags'>): boolean {
  return note.sourceType === 'read' && note.tags.includes(READ_WORKSPACE_NOTE_TAG);
}

export function isEvidenceCaptureNote(note: Pick<Note, 'tags' | 'title'>): boolean {
  const normalizedTitle = note.title.trim();
  const isEvidenceTitle = /^\s*(?:evidence|claim)\s*:/i.test(normalizedTitle);
  return (
    note.tags.some((tag) => EVIDENCE_NOTE_TAGS.includes(tag as (typeof EVIDENCE_NOTE_TAGS)[number]))
    || isEvidenceTitle
  );
}

export function getPrimaryUserNoteForPaper(notes: Note[], paperId: string): Note | null {
  return (
    filterUserEditableNotes(notes).find((note) => note.paperIds.includes(paperId)) ||
    null
  );
}

export function getPrimaryReadingNoteForPaper(notes: Note[], paperId: string): Note | null {
  const editable = filterUserEditableNotes(notes).filter(
    (note) => note.paperIds.includes(paperId) && !isEvidenceCaptureNote(note),
  );
  return editable.find((note) => isReadingWorkspaceNote(note)) || null;
}
