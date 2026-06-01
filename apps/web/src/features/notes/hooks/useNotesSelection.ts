import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';

import type { Note } from '@/services/notesApi';
import {
  normalizeEditorDocument,
} from '@/features/notes/content';
import {
  buildNoteDisplayTitle,
  getFolderIdFromTags,
  getPaperIdTag,
} from '@/features/notes/notePresentation';
import {
  getPrimaryReadingNoteForPaper,
  type ReadingSummaryProjection,
} from '@/features/notes/ownership';

type FolderSelectionSource = 'auto' | 'manual';

export interface UseNotesSelectionParams {
  userNotes: Note[];
  filteredNotes: Note[];
  derivedSummaries: ReadingSummaryProjection[];
  paperTitleMap: Map<string, string>;
  paperIdFilter: string | null;
  selectedFolderId: string | null;
  setSelectedFolderId: (folderId: string | null) => void;
}

export interface UseNotesSelectionReturn {
  selectedNoteId: string | null;
  selectedSummaryPaperId: string | null;
  selectedNote: Note | null;
  selectedSummary: ReadingSummaryProjection | null;
  selectedNoteDisplayTitle: string;
  editorContent: any;
  editingTitle: boolean;
  draftTitle: string;
  hasUnsavedChanges: boolean;
  deleteNoteId: string | null;
  folderSelectionSource: FolderSelectionSource | null;
  setEditorContent: React.Dispatch<React.SetStateAction<any>>;
  setEditingTitle: React.Dispatch<React.SetStateAction<boolean>>;
  setDraftTitle: React.Dispatch<React.SetStateAction<string>>;
  setDeleteNoteId: React.Dispatch<React.SetStateAction<string | null>>;
  setFolderSelectionSource: React.Dispatch<React.SetStateAction<FolderSelectionSource | null>>;
  setSelectedNoteId: React.Dispatch<React.SetStateAction<string | null>>;
  handleSelectNote: (note: Note, selectionSource?: FolderSelectionSource | null) => void;
  handleSelectSummary: (summary: ReadingSummaryProjection, selectionSource?: FolderSelectionSource | null) => void;
}

export function useNotesSelection({
  userNotes,
  filteredNotes,
  derivedSummaries,
  paperTitleMap,
  paperIdFilter,
  selectedFolderId,
  setSelectedFolderId,
}: UseNotesSelectionParams): UseNotesSelectionReturn {
  const [searchParams, setSearchParams] = useSearchParams();
  const noteIdQuery = searchParams.get('noteId');

  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [selectedSummaryPaperId, setSelectedSummaryPaperId] = useState<string | null>(null);
  const [editorContent, setEditorContent] = useState<any>(null);
  const [editingTitle, setEditingTitle] = useState(false);
  const [draftTitle, setDraftTitle] = useState('');
  const [deleteNoteId, setDeleteNoteId] = useState<string | null>(null);
  const [folderSelectionSource, setFolderSelectionSource] = useState<FolderSelectionSource | null>(null);

  const selectedNote = useMemo(
    () => userNotes.find((note) => note.id === selectedNoteId) || null,
    [selectedNoteId, userNotes],
  );

  const selectedSummary = useMemo(
    () => derivedSummaries.find((summary) => summary.paperId === selectedSummaryPaperId) || null,
    [derivedSummaries, selectedSummaryPaperId],
  );

  const selectedNoteDisplayTitle = useMemo(
    () => (selectedNote ? buildNoteDisplayTitle(selectedNote, paperTitleMap) : ''),
    [paperTitleMap, selectedNote],
  );

  const hasUnsavedChanges = useMemo(() => {
    if (!selectedNote || !editorContent) return false;
    const currentContent = JSON.stringify(normalizeEditorDocument(selectedNote.contentDoc || selectedNote.content));
    return JSON.stringify(editorContent) !== currentContent;
  }, [editorContent, selectedNote]);

  const handleSelectNote = useCallback((note: Note, selectionSource: FolderSelectionSource | null = 'manual') => {
    setSelectedSummaryPaperId(null);
    setSelectedNoteId((current) => (current === note.id ? current : note.id));

    const folderId = getFolderIdFromTags(note.tags);
    if (folderId) {
      setSelectedFolderId(folderId);
      setFolderSelectionSource(selectionSource);
    } else {
      setSelectedFolderId(null);
      setFolderSelectionSource(null);
    }

    const nextContent = normalizeEditorDocument(note.contentDoc || note.content);
    setEditorContent((current: any) => {
      const currentSerialized = current ? JSON.stringify(current) : null;
      const nextSerialized = JSON.stringify(nextContent);
      return currentSerialized === nextSerialized ? current : nextContent;
    });
  }, [setSelectedFolderId]);

  const handleSelectSummary = useCallback((summary: ReadingSummaryProjection, selectionSource: FolderSelectionSource | null = 'manual') => {
    setSelectedNoteId(null);
    setSelectedSummaryPaperId((current) => (current === summary.paperId ? current : summary.paperId));
    setEditorContent((current: any) => (current === null ? current : null));

    if (summary.folderId) {
      setSelectedFolderId(summary.folderId);
      setFolderSelectionSource(selectionSource);
    } else {
      setSelectedFolderId(null);
      setFolderSelectionSource(null);
    }

    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('noteId');
    nextParams.set('paperId', summary.paperId);
    if (nextParams.toString() !== searchParams.toString()) {
      setSearchParams(nextParams, { replace: true });
    }
  }, [searchParams, setSearchParams, setSelectedFolderId]);

  // Auto-select first note when no selection exists
  useEffect(() => {
    if (userNotes.length === 0 && derivedSummaries.length === 0) return;
    if (selectedNoteId && userNotes.some((note) => note.id === selectedNoteId)) return;
    if (selectedSummaryPaperId && derivedSummaries.some((summary) => summary.paperId === selectedSummaryPaperId)) return;

    if (noteIdQuery) {
      const target = userNotes.find((note) => note.id === noteIdQuery);
      if (target) {
        handleSelectNote(target, 'auto');
        return;
      }
    }

    if (!paperIdFilter) return;

    const related = getPrimaryReadingNoteForPaper(userNotes, paperIdFilter)
      || userNotes.find(
        (note) => note.paperIds.includes(paperIdFilter) || getPaperIdTag(note.tags) === paperIdFilter,
      );
    if (related) {
      handleSelectNote(related, 'auto');
      return;
    }

    const summary = derivedSummaries.find((item) => item.paperId === paperIdFilter);
    if (summary) {
      handleSelectSummary(summary, 'auto');
    }
  }, [
    derivedSummaries,
    handleSelectNote,
    handleSelectSummary,
    noteIdQuery,
    paperIdFilter,
    selectedNoteId,
    selectedSummaryPaperId,
    userNotes,
  ]);

  return {
    selectedNoteId,
    selectedSummaryPaperId,
    selectedNote,
    selectedSummary,
    selectedNoteDisplayTitle,
    editorContent,
    editingTitle,
    draftTitle,
    hasUnsavedChanges,
    deleteNoteId,
    folderSelectionSource,
    setEditorContent,
    setEditingTitle,
    setDraftTitle,
    setDeleteNoteId,
    setFolderSelectionSource,
    setSelectedNoteId,
    handleSelectNote,
    handleSelectSummary,
  };
}
