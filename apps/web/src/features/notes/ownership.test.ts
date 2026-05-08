import { describe, expect, it } from 'vitest';
import type { Note } from '@/services/notesApi';
import {
  AI_NOTE_TAG,
  EVIDENCE_NOTE_TAGS,
  READ_WORKSPACE_NOTE_TAG,
  buildReadingNoteTitle,
  filterUserEditableNotes,
  getPrimaryReadingNoteForPaper,
  getPrimaryUserNoteForPaper,
  isEvidenceCaptureNote,
  isReadingWorkspaceNote,
  isSystemAiNote,
} from './ownership';

function buildNote(overrides: Partial<Note>): Note {
  return {
    id: 'note-1',
    userId: 'user-1',
    title: 'note',
    content: 'content',
    contentDoc: { type: 'doc', content: [] },
    linkedEvidence: [],
    sourceType: 'manual',
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

  it('recognizes read-surface notes explicitly', () => {
    expect(isReadingWorkspaceNote(buildNote({ sourceType: 'read', tags: [READ_WORKSPACE_NOTE_TAG] }))).toBe(true);
    expect(isReadingWorkspaceNote(buildNote({ sourceType: 'read' }))).toBe(false);
    expect(isReadingWorkspaceNote(buildNote({ tags: [READ_WORKSPACE_NOTE_TAG] }))).toBe(false);
    expect(isReadingWorkspaceNote(buildNote({ sourceType: 'compare' }))).toBe(false);
  });

  it('recognizes evidence capture notes separately from reading notes', () => {
    expect(isEvidenceCaptureNote(buildNote({ tags: [...EVIDENCE_NOTE_TAGS] }))).toBe(true);
    expect(isEvidenceCaptureNote(buildNote({ title: 'Evidence: snippet' }))).toBe(true);
    expect(isEvidenceCaptureNote(buildNote({ title: 'Claim: snippet' }))).toBe(true);
    expect(isEvidenceCaptureNote(buildNote({ title: '  claim: snippet' }))).toBe(true);
    expect(isEvidenceCaptureNote(buildNote({ title: 'Regular note' }))).toBe(false);
  });

  it('prefers only read-surface notes for the reading workspace', () => {
    const notes = [
      buildNote({ id: 'compare-note', sourceType: 'compare', paperIds: ['paper-1'] }),
      buildNote({ id: 'manual-note', sourceType: 'manual', paperIds: ['paper-1'] }),
      buildNote({ id: 'evidence-note', sourceType: 'read', tags: ['evidence'], paperIds: ['paper-1'] }),
      buildNote({ id: 'read-note', sourceType: 'read', tags: [READ_WORKSPACE_NOTE_TAG], paperIds: ['paper-1'] }),
    ];

    expect(getPrimaryReadingNoteForPaper(notes, 'paper-1')?.id).toBe('read-note');
  });

  it('builds localized reading note titles', () => {
    expect(buildReadingNoteTitle('Paper', false)).toBe('Paper · Reading Notes');
    expect(buildReadingNoteTitle('', true)).toBe('未命名论文 · 阅读笔记');
  });
});
