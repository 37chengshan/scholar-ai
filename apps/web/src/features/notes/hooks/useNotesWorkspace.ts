import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';
import { toast } from 'sonner';

import type { NoteFolder } from '@/app/components/NoteFolderTree';
import { useNotes } from '@/hooks/useNotes';
import {
  getFolderIdFromTags,
  getPaperIdTag,
  upsertFolderTag,
} from '@/features/notes/notePresentation';
import {
  createEmptyEditorDocument,
  type ReadingSummaryProjection,
} from '@/features/notes/ownership';
import { useNotesPreferencesStore } from '@/features/notes/state/notesPreferencesStore';

import { useNotesCatalog } from './useNotesCatalog';
import { useNotesFilter } from './useNotesFilter';
import { useNotesSelection } from './useNotesSelection';
import { useNotesCrud } from './useNotesCrud';
import { useNotesSync } from './useNotesSync';

export function useNotesWorkspace(userId?: string) {
  const [searchParams, setSearchParams] = useSearchParams();
  const paperIdFilter = searchParams.get('paperId');

  const { notes, loading: notesLoading } = useNotes();

  const {
    selectedFolderId,
    tagFilter,
    setSelectedFolderId,
    setTagFilter,
  } = useNotesPreferencesStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [pendingCreateAfterFolder, setPendingCreateAfterFolder] = useState(false);

  const catalog = useNotesCatalog({ notes, paperIdFilter });

  const filter = useNotesFilter({
    notes,
    paperIdFilter,
    selectedFolderId,
    tagFilter,
    searchQuery,
    derivedSummaries: catalog.derivedSummaries,
    paperTitleMap: catalog.paperTitleMap,
  });

  const selection = useNotesSelection({
    userNotes: filter.userNotes,
    filteredNotes: filter.filteredNotes,
    derivedSummaries: catalog.derivedSummaries,
    paperTitleMap: catalog.paperTitleMap,
    paperIdFilter,
    selectedFolderId,
    setSelectedFolderId,
  });

  const crud = useNotesCrud();

  const sync = useNotesSync({
    selectedNoteId: selection.selectedNoteId,
    selectedNote: selection.selectedNote,
    editorContent: selection.editorContent,
    userId,
    onSave: useCallback(
      (content: any) => {
        if (!selection.selectedNote) return Promise.resolve();
        return crud.handleSave(selection.selectedNote, content, selectedFolderId);
      },
      [selection.selectedNote, crud.handleSave, selectedFolderId],
    ),
  });

  // Auto-select folder from note/paper context
  useEffect(() => {
    if (!paperIdFilter || notesLoading || catalog.catalogLoading || selection.folderSelectionSource === 'manual') return;

    const relatedNotes = filter.userNotes.filter(
      (note) => note.paperIds.includes(paperIdFilter) || getPaperIdTag(note.tags) === paperIdFilter,
    );
    const relatedFolderIds = relatedNotes
      .map((note) => getFolderIdFromTags(note.tags))
      .filter((folderId): folderId is string => Boolean(folderId));
    const hasFolderlessRelatedNote = relatedNotes.some((note) => getFolderIdFromTags(note.tags) === null);
    const uniqueRelatedFolderIds = Array.from(new Set(relatedFolderIds));

    if (relatedNotes.length > 0) {
      if (!hasFolderlessRelatedNote && uniqueRelatedFolderIds.length === 1) {
        const nextFolderId = uniqueRelatedFolderIds[0];
        if (selectedFolderId !== nextFolderId || selection.folderSelectionSource !== 'auto') {
          setSelectedFolderId(nextFolderId);
          selection.setFolderSelectionSource('auto');
        }
        return;
      }
      if (selectedFolderId !== null) setSelectedFolderId(null);
      if (selection.folderSelectionSource !== null) selection.setFolderSelectionSource(null);
      return;
    }

    const matchingSummary = catalog.paperCatalog.find((item) => item.id === paperIdFilter);
    if (matchingSummary?.folderId) {
      if (selectedFolderId !== matchingSummary.folderId || selection.folderSelectionSource !== 'auto') {
        setSelectedFolderId(matchingSummary.folderId);
        selection.setFolderSelectionSource('auto');
      }
      return;
    }

    if (selectedFolderId !== null) setSelectedFolderId(null);
    if (selection.folderSelectionSource !== null) selection.setFolderSelectionSource(null);
  }, [
    catalog.catalogLoading, catalog.paperCatalog, filter.userNotes, notesLoading,
    paperIdFilter, selectedFolderId, selection.folderSelectionSource,
    selection.setFolderSelectionSource, setSelectedFolderId,
  ]);

  useEffect(() => {
    if (selectedFolderId === null) return;
    if (catalog.folders.some((folder) => folder.id === selectedFolderId)) return;
    setSelectedFolderId(null);
    selection.setFolderSelectionSource(null);
  }, [catalog.folders, selectedFolderId, selection.setFolderSelectionSource, setSelectedFolderId]);

  useEffect(() => {
    if (!pendingCreateAfterFolder || !selectedFolderId) return;
    setPendingCreateAfterFolder(false);
    void handleCreateNote();
  }, [pendingCreateAfterFolder, selectedFolderId]);

  const handleCreateFolder = useCallback((name: string, parentId: string | null) => {
    const newFolder: NoteFolder & { source: 'manual' } = {
      id: `manual:${Date.now()}`, name, parentId, noteCount: 0, source: 'manual',
    };
    catalog.setManualFolders((current) => [...current, newFolder]);
    setSelectedFolderId(newFolder.id);
    selection.setFolderSelectionSource('manual');
    toast.success(`文件夹「${name}」已创建`);
  }, [catalog.setManualFolders, selection.setFolderSelectionSource, setSelectedFolderId]);

  const handleSelectFolder = useCallback((folderId: string | null) => {
    setSelectedFolderId(folderId);
    selection.setFolderSelectionSource('manual');
  }, [selection.setFolderSelectionSource, setSelectedFolderId]);

  const handleCreateNote = useCallback(async () => {
    if (!selectedFolderId) {
      setPendingCreateAfterFolder(true);
      toast.warning('请先创建或选择文件夹，再创建笔记');
      return;
    }
    await crud.handleCreateNote(selectedFolderId, paperIdFilter, catalog.paperTitleMap, selection.handleSelectNote, selection.setEditorContent);
  }, [crud.handleCreateNote, catalog.paperTitleMap, paperIdFilter, selectedFolderId, selection.handleSelectNote, selection.setEditorContent]);

  const handleDeleteNote = useCallback(async () => {
    if (!selection.deleteNoteId) return;
    await crud.handleDeleteNote(selection.deleteNoteId, selection.selectedNoteId, filter.filteredNotes, selection.handleSelectNote, () => { selection.setSelectedNoteId(null); selection.setEditorContent(null); });
    selection.setDeleteNoteId(null);
  }, [crud.handleDeleteNote, filter.filteredNotes, selection]);

  const handleCommitEditedTitle = useCallback(async () => {
    const nextTitle = selection.draftTitle.trim() || '未命名笔记';
    selection.setEditingTitle(false);
    if (!selection.selectedNote || nextTitle === selection.selectedNoteDisplayTitle) return;
    await crud.updateNote.mutateAsync({ id: selection.selectedNote.id, payload: { title: nextTitle } });
  }, [crud.updateNote, selection.draftTitle, selection.selectedNote, selection.selectedNoteDisplayTitle, selection.setEditingTitle]);

  const handleSummaryToNote = useCallback(async (summary: ReadingSummaryProjection) => {
    await crud.handleSummaryToNote(summary, selectedFolderId, selection.handleSelectNote);
  }, [crud.handleSummaryToNote, selectedFolderId, selection.handleSelectNote]);

  const handleSummaryAppendToCurrent = useCallback((summary: ReadingSummaryProjection) => {
    crud.handleSummaryAppendToCurrent(summary, selection.selectedNoteId, selection.editorContent, selection.setEditorContent);
  }, [crud.handleSummaryAppendToCurrent, selection.editorContent, selection.selectedNoteId, selection.setEditorContent]);

  const handleEditorChange = useCallback((json: any) => {
    crud.handleEditorChange(json, selection.selectedNote, selection.setEditorContent);
  }, [crud.handleEditorChange, selection.selectedNote, selection.setEditorContent]);

  const activeFilterChips = useMemo(() => {
    const chips: Array<{ key: string; label: string; onClear: () => void }> = [];
    if (paperIdFilter) {
      chips.push({ key: 'paper', label: `论文: ${catalog.paperTitleMap.get(paperIdFilter) || paperIdFilter}`, onClear: () => { const next = new URLSearchParams(searchParams); next.delete('paperId'); setSearchParams(next, { replace: true }); } });
    }
    if (selectedFolderId) {
      const folderName = catalog.folders.find((folder) => folder.id === selectedFolderId)?.name || selectedFolderId;
      chips.push({ key: 'folder', label: `文件夹: ${folderName}`, onClear: () => handleSelectFolder(null) });
    }
    if (tagFilter !== 'all') {
      chips.push({ key: 'tag', label: `标签: ${tagFilter}`, onClear: () => setTagFilter('all') });
    }
    if (searchQuery.trim()) {
      chips.push({ key: 'query', label: `关键词: ${searchQuery.trim()}`, onClear: () => setSearchQuery('') });
    }
    return chips;
  }, [catalog.folders, catalog.paperTitleMap, handleSelectFolder, paperIdFilter, searchParams, searchQuery, selectedFolderId, setSearchParams, setTagFilter, tagFilter]);

  return {
    headerProps: {
      catalogLoading: catalog.catalogLoading,
      paperIdFilter,
      paperTitle: paperIdFilter ? catalog.paperTitleMap.get(paperIdFilter) || paperIdFilter : null,
      onClearPaperFilter: () => { const next = new URLSearchParams(searchParams); next.delete('paperId'); setSearchParams(next, { replace: true }); },
    },
    sidebarProps: {
      selectedFolderId,
      selectedNoteId: selection.selectedNoteId,
      selectedSummaryPaperId: selection.selectedSummaryPaperId,
      searchQuery,
      tagFilter,
      allTags: filter.allTags,
      folders: catalog.folders,
      activeFilterChips,
      notesLoading,
      catalogLoading: catalog.catalogLoading,
      summaryItems: filter.summaryItems,
      archivedNoteItems: filter.archivedNoteItems,
      unarchivedNoteItems: filter.unarchivedNoteItems,
      onCreateNote: () => void handleCreateNote(),
      onSearchQueryChange: setSearchQuery,
      onTagFilterChange: setTagFilter,
      onSelectFolder: handleSelectFolder,
      onCreateFolder: handleCreateFolder,
      onSelectSummary: selection.handleSelectSummary,
      onSummaryAppend: handleSummaryAppendToCurrent,
      onSummaryToNote: (summary: ReadingSummaryProjection) => void handleSummaryToNote(summary),
      onSelectNote: selection.handleSelectNote,
      onDeleteNoteRequest: selection.setDeleteNoteId,
    },
    mainPanelProps: {
      selectedNote: selection.selectedNote,
      selectedSummary: selection.selectedSummary,
      selectedNoteDisplayTitle: selection.selectedNoteDisplayTitle,
      editingTitle: selection.editingTitle,
      draftTitle: selection.draftTitle,
      editorContent: selection.editorContent,
      paperIdFilter,
      paperTitleMap: catalog.paperTitleMap,
      onDraftTitleChange: selection.setDraftTitle,
      onStartEditingTitle: () => { selection.setDraftTitle(selection.selectedNoteDisplayTitle); selection.setEditingTitle(true); },
      onCommitTitle: () => { void handleCommitEditedTitle(); },
      onCancelEditingTitle: () => selection.setEditingTitle(false),
      onInsertPaperReference: () => {
        const refText = `[[pdf:${paperIdFilter}:page:1]]`;
        selection.setEditorContent({ ...(selection.editorContent || createEmptyEditorDocument()), content: [...((selection.editorContent?.content as any[]) || []), { type: 'paragraph', content: [{ type: 'text', text: refText }] }] });
        toast.success('已插入论文引用');
      },
      onEditorChange: handleEditorChange,
    },
    saveIndicatorProps: {
      selectedNoteId: selection.selectedNoteId,
      hasUnsavedChanges: sync.hasUnsavedChanges,
      retryingSave: sync.retryingSave,
      saveStatus: sync.saveStatus,
      lastSaved: sync.lastSaved,
      onRetrySave: sync.handleRetrySave,
    },
    deleteDialogProps: {
      open: !!selection.deleteNoteId,
      onOpenChange: (open: boolean) => { if (!open) selection.setDeleteNoteId(null); },
      onConfirmDelete: () => void handleDeleteNote(),
    },
  };
}
