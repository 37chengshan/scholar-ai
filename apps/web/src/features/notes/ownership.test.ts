import { describe, expect, it } from 'vitest';
import type { Note } from '@/services/notesApi';
import {
  AI_NOTE_TAG,
  buildReadingNoteTitle,
  filterUserEditableNotes,
  getPrimaryUserNoteForPaper,
  isSystemAiNote,
} from './ownership';

function buildNote(overrides: Partial<Note>): Note {
  return {
    id: 'note-1',
    userId: 'user-1',
    title: 'note',
    content: 'content',
    tags: [],
    paperIds: [],
    createdAt: '2026-04-21T00:00:00.000Z',
    updatedAt: '2026-04-21T00:00:00.000Z',
    ...overrides,
  };
}

describe('notes ownership helpers', () => {
  it('filters system AI notes out of editable note lists', () => {
    const notes = [
      buildNote({ id: 'user-note', paperIds: ['paper-1'] }),
      buildNote({ id: 'ai-note', tags: [AI_NOTE_TAG], paperIds: ['paper-1'] }),
    ];

    expect(filterUserEditableNotes(notes).map((note) => note.id)).toEqual(['user-note']);
    expect(isSystemAiNote(notes[1])).toBe(true);
  });

  it('prefers the user-editable note for a paper', () => {
    const notes = [
      buildNote({ id: 'ai-note', tags: [AI_NOTE_TAG], paperIds: ['paper-1'] }),
      buildNote({ id: 'user-note', paperIds: ['paper-1'] }),
    ];

    expect(getPrimaryUserNoteForPaper(notes, 'paper-1')?.id).toBe('user-note');
  });

  it('builds localized reading note titles', () => {
    expect(buildReadingNoteTitle('Paper', false)).toBe('Paper · Reading Notes');
    expect(buildReadingNoteTitle('', true)).toBe('未命名论文 · 阅读笔记');
  });
});