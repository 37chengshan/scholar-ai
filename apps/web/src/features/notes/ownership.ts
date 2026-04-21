import type { Note } from '@/services/notesApi';

export const AI_NOTE_TAG = '__ai_note__';

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

export function getPrimaryUserNoteForPaper(notes: Note[], paperId: string): Note | null {
  return (
    filterUserEditableNotes(notes).find((note) => note.paperIds.includes(paperId)) ||
    null
  );
}