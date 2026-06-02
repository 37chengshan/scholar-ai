/**
 * usePaperLoader Hook
 *
 * Loads paper data and initializes linked note.
 */

import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';

import * as annotationsApi from '@/services/annotationsApi';
import type { Annotation } from '@/services/annotationsApi';
import * as notesApi from '@/services/notesApi';
import * as papersApi from '@/services/papersApi';
import {
  buildReadingNoteTitle,
  createEmptyEditorDocument,
  getPrimaryReadingNoteForPaper,
} from '@/features/notes/ownership';
import { normalizeEditorDocument } from '@/features/notes/content';

export interface PaperLoaderResult {
  paper: any;
  loading: boolean;
  error: string | null;
  annotations: Annotation[];
  linkedNoteId: string | null;
  linkedNoteTitle: string;
  linkedNoteContent: any;
  setLinkedNoteContent: (v: any) => void;
  setLinkedNoteId: (v: string | null) => void;
  setLinkedNoteTitle: (v: string) => void;
  refreshAnnotations: () => Promise<void>;
}

export function usePaperLoader(
  id: string | undefined,
  isZh: boolean,
): PaperLoaderResult {
  const [paper, setPaper] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [linkedNoteId, setLinkedNoteId] = useState<string | null>(null);
  const [linkedNoteTitle, setLinkedNoteTitle] = useState('');
  const [linkedNoteContent, setLinkedNoteContent] = useState<any>(
    createEmptyEditorDocument(),
  );

  const initializeLinkedNote = useCallback(
    async (paperId: string, paperTitle: string) => {
      const noteTitle = buildReadingNoteTitle(paperTitle, isZh);
      const existingNotes = await notesApi.getNotesByPaper(paperId);
      const userNote = getPrimaryReadingNoteForPaper(existingNotes, paperId);

      if (!userNote) {
        setLinkedNoteId(null);
        setLinkedNoteTitle(noteTitle);
        setLinkedNoteContent(createEmptyEditorDocument());
        return;
      }

      setLinkedNoteId(userNote.id);
      setLinkedNoteTitle(userNote.title || noteTitle);
      setLinkedNoteContent(
        normalizeEditorDocument(userNote.contentDoc || userNote.content),
      );
    },
    [isZh],
  );

  useEffect(() => {
    let cancelled = false;

    async function loadPaper() {
      if (!id) {
        setPaper(null);
        setError(null);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const data = await papersApi.get(id);
        if (cancelled) return;
        setPaper(data);

        const annotationData = await annotationsApi.list(id);
        if (cancelled) return;
        setAnnotations(annotationData);

        await initializeLinkedNote(id, data.title || '');
      } catch (loadError: unknown) {
        if (cancelled) return;
        const errorMsg =
          (loadError as Error)?.message ||
          (isZh ? '加载论文失败' : 'Failed to load paper');
        setError(errorMsg);
        toast.error(errorMsg);
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadPaper();
    return () => {
      cancelled = true;
    };
  }, [id, initializeLinkedNote, isZh]);

  const refreshAnnotations = useCallback(async () => {
    if (!id) return;
    const data = await annotationsApi.list(id);
    setAnnotations(data);
  }, [id]);

  return {
    paper,
    loading,
    error,
    annotations,
    linkedNoteId,
    linkedNoteTitle,
    linkedNoteContent,
    setLinkedNoteContent,
    setLinkedNoteId,
    setLinkedNoteTitle,
    refreshAnnotations,
  };
}
