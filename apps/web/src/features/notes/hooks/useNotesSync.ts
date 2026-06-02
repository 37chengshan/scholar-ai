import { useCallback, useMemo, useState } from 'react';

import { useAutoSave } from '@/app/hooks/useAutoSave';
import type { Note } from '@/services/notesApi';
import {
  normalizeEditorDocument,
} from '@/features/notes/content';

export interface UseNotesSyncParams {
  selectedNoteId: string | null;
  selectedNote: Note | null;
  editorContent: any;
  userId?: string;
  onSave: (content: any) => Promise<void>;
}

export interface UseNotesSyncReturn {
  saveStatus: 'idle' | 'saving' | 'saved' | 'error';
  lastSaved: Date | null;
  hasUnsavedChanges: boolean;
  retryingSave: boolean;
  handleRetrySave: () => Promise<void>;
}

export function useNotesSync({
  selectedNoteId,
  selectedNote,
  editorContent,
  userId,
  onSave,
}: UseNotesSyncParams): UseNotesSyncReturn {
  const [retryingSave, setRetryingSave] = useState(false);

  const { status: saveStatus, lastSaved, retrySave } = useAutoSave({
    content: editorContent,
    onSave,
    debounceMs: 1000,
    noteId: selectedNoteId || undefined,
    userId,
  });

  const hasUnsavedChanges = useMemo(() => {
    if (!selectedNote || !editorContent) return false;
    const currentContent = JSON.stringify(normalizeEditorDocument(selectedNote.contentDoc || selectedNote.content));
    return JSON.stringify(editorContent) !== currentContent;
  }, [editorContent, selectedNote]);

  const handleRetrySave = useCallback(async () => {
    setRetryingSave(true);
    try {
      retrySave();
    } finally {
      window.setTimeout(() => setRetryingSave(false), 400);
    }
  }, [retrySave]);

  return {
    saveStatus,
    lastSaved,
    hasUnsavedChanges,
    retryingSave,
    handleRetrySave,
  };
}
