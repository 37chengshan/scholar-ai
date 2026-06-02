/**
 * useLinkedNote Hook
 *
 * Manages linked note with React Query for bidirectional sync
 * and useAutoSave for debounced persistence.
 */

import { useCallback, useEffect, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as notesApi from '@/services/notesApi';
import { useAutoSave } from '@/app/hooks/useAutoSave';
import {
  buildReadingNoteTitle,
  createEmptyEditorDocument,
  READ_WORKSPACE_NOTE_TAG,
} from '@/features/notes/ownership';
import { normalizeEditorDocument } from '@/features/notes/content';

export function useLinkedNote(
  id: string | undefined,
  paperTitle: string | undefined,
  isZh: boolean,
  linkedNoteId: string | null,
  setLinkedNoteId: (v: string | null) => void,
  linkedNoteTitle: string,
  setLinkedNoteTitle: (v: string) => void,
) {
  const queryClient = useQueryClient();

  // Fetch note content via React Query when we have a noteId
  const { data: remoteNote } = useQuery({
    queryKey: ['note', linkedNoteId],
    queryFn: () => notesApi.getNote(linkedNoteId!),
    enabled: !!linkedNoteId,
    staleTime: 30_000,
  });

  // Derive content from remote data or use empty document
  const linkedNoteContent = useMemo(() => {
    if (remoteNote) {
      return normalizeEditorDocument(remoteNote.contentDoc || remoteNote.content);
    }
    return createEmptyEditorDocument();
  }, [remoteNote]);

  // Setter that updates the React Query cache optimistically
  const setLinkedNoteContent = useCallback(
    (content: any) => {
      if (!linkedNoteId) return;
      queryClient.setQueryData(['note', linkedNoteId], (old: any) => ({
        ...old,
        contentDoc: content,
      }));
    },
    [linkedNoteId, queryClient],
  );

  // Save handler for useAutoSave
  const handleSave = useCallback(
    async (content: any) => {
      if (!id) return;
      const contentJson = JSON.stringify(content || createEmptyEditorDocument());
      const existingText = contentJson.replace(/[\s"{}\[\],:]/g, '');
      if (!existingText) return;

      if (!linkedNoteId) {
        const created = await notesApi.createNote({
          title: linkedNoteTitle || buildReadingNoteTitle(paperTitle, isZh),
          contentDoc: normalizeEditorDocument(content),
          sourceType: 'read',
          tags: [READ_WORKSPACE_NOTE_TAG],
          paperIds: [id],
        });
        setLinkedNoteId(created.id);
        setLinkedNoteTitle(created.title || linkedNoteTitle);
        queryClient.setQueryData(['note', created.id], created);
      } else {
        try {
          const updated = await notesApi.updateNote(linkedNoteId, {
            title: linkedNoteTitle || buildReadingNoteTitle(paperTitle, isZh),
            contentDoc: normalizeEditorDocument(content),
            sourceType: 'read',
            tags: [READ_WORKSPACE_NOTE_TAG],
            paperIds: [id],
          });
          queryClient.setQueryData(['note', linkedNoteId], updated);
        } catch (err: unknown) {
          // Check for 409 Conflict (concurrent edit)
          const status = (err as { response?: { status?: number } })?.response?.status;
          if (status === 409) {
            toast.warning(
              isZh
                ? '笔记在其他地方被修改，已重新加载'
                : 'Note was modified elsewhere, reloaded',
            );
            void queryClient.invalidateQueries({ queryKey: ['note', linkedNoteId] });
            return;
          }
          throw err;
        }
      }
    },
    [id, isZh, linkedNoteId, linkedNoteTitle, paperTitle, queryClient, setLinkedNoteId, setLinkedNoteTitle],
  );

  // Wire useAutoSave
  const { status: noteSaveStatus, lastSaved: noteLastSaved } = useAutoSave({
    content: linkedNoteContent,
    onSave: handleSave,
    debounceMs: 800,
    noteId: linkedNoteId || undefined,
  });

  return {
    linkedNoteContent,
    setLinkedNoteContent,
    noteSaveStatus,
    noteLastSaved,
  };
}
