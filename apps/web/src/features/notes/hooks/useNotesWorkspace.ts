import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';
import { toast } from 'sonner';

import { useAutoSave } from '@/app/hooks/useAutoSave';
import type { NoteFolder } from '@/app/components/NoteFolderTree';
import { useNotes, useCreateNote, useDeleteNote, useUpdateNote } from '@/hooks/useNotes';
import type { Note } from '@/services/notesApi';
import { kbApi } from '@/services/kbApi';
import * as papersApi from '@/services/papersApi';
import {
  extractEditorPlainText,
  normalizeEditorDocument,
} from '@/features/notes/content';
import {
  buildNoteDisplayTitle,
  buildPaperDisplayTitle,
  buildSummaryDisplayTitle,
  getDisplayTags,
  getFolderIdFromTags,
  getPaperIdTag,
  getPaperTitleTag,
  humanizeNotePreview,
  humanizeSummaryPreview,
  PAPER_TAG_PREFIX,
  upsertFolderTag,
} from '@/features/notes/notePresentation';
import {
  createEmptyEditorDocument,
  filterUserEditableNotes,
  getPrimaryReadingNoteForPaper,
  isEvidenceCaptureNote,
  type ReadingSummaryProjection,
} from '@/features/notes/ownership';
import { useNotesPreferencesStore } from '@/features/notes/state/notesPreferencesStore';

const MANUAL_FOLDERS_STORAGE_KEY = 'notes-manual-folders-v1';
const UNARCHIVED_FOLDER_ID = '__unarchived__';

type FolderSource = 'kb' | 'manual';
type FolderSelectionSource = 'auto' | 'manual';

interface NotesFolder extends NoteFolder {
  source: FolderSource;
}

interface PaperCatalogItem {
  id: string;
  title: string;
  readingNotes: string | null;
  folderId: string | null;
}

function formatDate(dateStr: string) {
  const date = new Date(dateStr);
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function useNotesWorkspace() {
  const [searchParams, setSearchParams] = useSearchParams();
  const paperIdFilter = searchParams.get('paperId');
  const noteIdQuery = searchParams.get('noteId');

  const { notes, loading: notesLoading } = useNotes();
  const createNote = useCreateNote();
  const updateNote = useUpdateNote();
  const deleteNote = useDeleteNote();

  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [selectedSummaryPaperId, setSelectedSummaryPaperId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteNoteId, setDeleteNoteId] = useState<string | null>(null);
  const [editorContent, setEditorContent] = useState<any>(null);
  const [folderSelectionSource, setFolderSelectionSource] = useState<FolderSelectionSource | null>(null);
  const [pendingCreateAfterFolder, setPendingCreateAfterFolder] = useState(false);
  const [retryingSave, setRetryingSave] = useState(false);
  const [editingTitle, setEditingTitle] = useState(false);
  const [draftTitle, setDraftTitle] = useState('');
  const {
    selectedFolderId,
    tagFilter,
    setSelectedFolderId,
    setTagFilter,
  } = useNotesPreferencesStore();

  const [kbFolders, setKbFolders] = useState<NotesFolder[]>([]);
  const [manualFolders, setManualFolders] = useState<NotesFolder[]>([]);
  const [paperCatalog, setPaperCatalog] = useState<PaperCatalogItem[]>([]);
  const [paperTitleMap, setPaperTitleMap] = useState<Map<string, string>>(new Map());
  const [hydratedPaperIds, setHydratedPaperIds] = useState<Set<string>>(new Set());
  const [catalogLoading, setCatalogLoading] = useState(false);

  const userNotes = useMemo(() => filterUserEditableNotes(notes), [notes]);
  const selectedNote = useMemo(
    () => userNotes.find((note) => note.id === selectedNoteId) || null,
    [selectedNoteId, userNotes],
  );

  useEffect(() => {
    try {
      const raw = localStorage.getItem(MANUAL_FOLDERS_STORAGE_KEY);
      if (!raw) {
        return;
      }
      const parsed = JSON.parse(raw) as NotesFolder[];
      if (!Array.isArray(parsed)) {
        return;
      }
      const nextManualFolders = parsed.filter((item) => item.source === 'manual');
      setManualFolders((current) => {
        const currentSerialized = JSON.stringify(current);
        const nextSerialized = JSON.stringify(nextManualFolders);
        return currentSerialized === nextSerialized ? current : nextManualFolders;
      });
    } catch {
      // Ignore malformed local storage data.
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(MANUAL_FOLDERS_STORAGE_KEY, JSON.stringify(manualFolders));
  }, [manualFolders]);

  useEffect(() => {
    async function loadCatalog() {
      try {
        setCatalogLoading(true);

        const kbList = await kbApi.list({ limit: 100, offset: 0 });
        const knowledgeBases = kbList.knowledgeBases || [];
        const kbFolderList: NotesFolder[] = knowledgeBases.map((kb) => ({
          id: `kb:${kb.id}`,
          name: kb.name,
          parentId: null,
          noteCount: 0,
          source: 'kb',
        }));

        const papersResponse = await papersApi.list({ page: 1, limit: 200, sortBy: 'updatedAt' });
        const papers = papersResponse.data.papers || [];
        const nextTitleMap = new Map<string, string>();
        const nextCatalog: PaperCatalogItem[] = papers.map((paper) => {
          const resolvedTitle = buildSummaryDisplayTitle(paper.title, paper.readingNotes);
          nextTitleMap.set(paper.id, buildPaperDisplayTitle(paper.title));

          const normalized = paper as typeof paper & {
            readingNotes?: string | null;
            knowledgeBaseId?: string | null;
          };
          const folderId = normalized.knowledgeBaseId ? `kb:${normalized.knowledgeBaseId}` : null;

          return {
            id: paper.id,
            title: resolvedTitle,
            readingNotes: normalized.readingNotes || null,
            folderId,
          };
        });

        setKbFolders(kbFolderList);
        setPaperCatalog(nextCatalog);
        setPaperTitleMap(nextTitleMap);
      } catch {
        toast.error('加载知识库与论文目录失败');
      } finally {
        setCatalogLoading(false);
      }
    }

    void loadCatalog();
  }, []);

  useEffect(() => {
    if (!paperIdFilter) {
      return;
    }
    const targetPaperId = paperIdFilter;

    if (paperTitleMap.has(targetPaperId) || hydratedPaperIds.has(targetPaperId)) {
      return;
    }

    let cancelled = false;

    async function hydrateMissingPaperMetadata() {
      try {
        const paper = await papersApi.get(targetPaperId);
        if (cancelled) {
          return;
        }

        const resolvedTitle = buildSummaryDisplayTitle(paper.title, paper.readingNotes);
        setPaperTitleMap((current) => {
          const next = new Map(current);
          next.set(paper.id, resolvedTitle);
          return next;
        });

        setPaperCatalog((current) => {
          if (current.some((item) => item.id === paper.id)) {
            return current.map((item) =>
              item.id === paper.id
                ? {
                    ...item,
                    title: resolvedTitle,
                    readingNotes: paper.readingNotes || item.readingNotes,
                    folderId: paper.knowledgeBaseId ? `kb:${paper.knowledgeBaseId}` : item.folderId,
                  }
                : item,
            );
          }

          return [
            ...current,
            {
              id: paper.id,
              title: resolvedTitle,
              readingNotes: paper.readingNotes || null,
              folderId: paper.knowledgeBaseId ? `kb:${paper.knowledgeBaseId}` : null,
            },
          ];
        });
      } catch {
        // Keep the page usable even when the detail lookup fails.
      } finally {
        if (!cancelled) {
          setHydratedPaperIds((current) => new Set(current).add(targetPaperId));
        }
      }
    }

    void hydrateMissingPaperMetadata();

    return () => {
      cancelled = true;
    };
  }, [hydratedPaperIds, paperIdFilter, paperTitleMap]);

  const derivedSummaries = useMemo<ReadingSummaryProjection[]>(() => {
    let summaries = paperCatalog
      .filter((paper) => paper.readingNotes && paper.readingNotes.trim().length > 0)
      .map((paper) => ({
        paperId: paper.id,
        title: buildSummaryDisplayTitle(paper.title, paper.readingNotes),
        readingNotes: paper.readingNotes || '',
        folderId: paper.folderId,
      }));

    if (paperIdFilter) {
      summaries = summaries.filter((summary) => summary.paperId === paperIdFilter);
    }

    if (selectedFolderId !== null) {
      summaries = summaries.filter((summary) => summary.folderId === selectedFolderId);
    }

    if (searchQuery.trim()) {
      const normalizedQuery = searchQuery.trim().toLowerCase();
      summaries = summaries.filter(
        (summary) =>
          summary.title.toLowerCase().includes(normalizedQuery)
          || summary.readingNotes.toLowerCase().includes(normalizedQuery),
      );
    }

    return summaries;
  }, [paperCatalog, paperIdFilter, searchQuery, selectedFolderId]);

  const selectedSummary = useMemo(
    () => derivedSummaries.find((summary) => summary.paperId === selectedSummaryPaperId) || null,
    [derivedSummaries, selectedSummaryPaperId],
  );

  const notePreviewText = useCallback((note: Note) => {
    const preview = humanizeNotePreview(extractEditorPlainText(note.contentDoc || note.content, 80));
    if (preview !== '暂无正文') {
      return preview;
    }
    if (isEvidenceCaptureNote(note)) {
      const evidenceText = note.linkedEvidence
        ?.map((item) => humanizeNotePreview(String(item?.text || '')))
        .find((text) => text && text !== '暂无正文');
      if (evidenceText) {
        return evidenceText;
      }
    }
    return preview;
  }, []);

  const folderCounts = useMemo(() => {
    const counts = new Map<string, number>();
    userNotes.forEach((note) => {
      const folderId = getFolderIdFromTags(note.tags);
      if (folderId) {
        counts.set(folderId, (counts.get(folderId) || 0) + 1);
      }
    });
    derivedSummaries.forEach((summary) => {
      if (summary.folderId) {
        counts.set(summary.folderId, (counts.get(summary.folderId) || 0) + 1);
      }
    });
    return counts;
  }, [derivedSummaries, userNotes]);

  const folders = useMemo<NotesFolder[]>(() => {
    const merged = [...kbFolders, ...manualFolders];
    const mapped = merged
      .map((folder) => ({
        ...folder,
        noteCount: folderCounts.get(folder.id) || 0,
      }))
      .filter((folder) => folder.noteCount > 0 || folder.source !== 'kb');
    const unarchivedCount = userNotes.filter((note) => getFolderIdFromTags(note.tags) === null).length;

    return [
      {
        id: UNARCHIVED_FOLDER_ID,
        name: '未归档',
        parentId: null,
        noteCount: unarchivedCount,
        source: 'manual',
      },
      ...mapped,
    ];
  }, [folderCounts, kbFolders, manualFolders, userNotes]);

  useEffect(() => {
    if (selectedFolderId === null) {
      return;
    }
    if (folders.some((folder) => folder.id === selectedFolderId)) {
      return;
    }
    setSelectedFolderId(null);
    setFolderSelectionSource(null);
  }, [folders, selectedFolderId, setSelectedFolderId]);

  useEffect(() => {
    if (!paperIdFilter || notesLoading || catalogLoading || folderSelectionSource === 'manual') {
      return;
    }

    const relatedNotes = userNotes.filter(
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
        if (selectedFolderId !== nextFolderId || folderSelectionSource !== 'auto') {
          setSelectedFolderId(nextFolderId);
          setFolderSelectionSource('auto');
        }
        return;
      }

      if (selectedFolderId !== null) {
        setSelectedFolderId(null);
      }
      if (folderSelectionSource !== null) {
        setFolderSelectionSource(null);
      }
      return;
    }

    const matchingSummary = paperCatalog.find((item) => item.id === paperIdFilter);
    if (matchingSummary?.folderId) {
      if (selectedFolderId !== matchingSummary.folderId || folderSelectionSource !== 'auto') {
        setSelectedFolderId(matchingSummary.folderId);
        setFolderSelectionSource('auto');
      }
      return;
    }

    if (selectedFolderId !== null) {
      setSelectedFolderId(null);
    }
    if (folderSelectionSource !== null) {
      setFolderSelectionSource(null);
    }
  }, [
    catalogLoading,
    folderSelectionSource,
    notesLoading,
    paperCatalog,
    paperIdFilter,
    selectedFolderId,
    setSelectedFolderId,
    userNotes,
  ]);

  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    userNotes.forEach((note) => getDisplayTags(note.tags).forEach((tag) => tagSet.add(tag)));
    return Array.from(tagSet).sort();
  }, [userNotes]);

  const filteredNotes = useMemo(() => {
    let result = userNotes;

    if (paperIdFilter) {
      result = result.filter(
        (note) => note.paperIds.includes(paperIdFilter) || getPaperIdTag(note.tags) === paperIdFilter,
      );
    }

    if (selectedFolderId !== null) {
      if (selectedFolderId === UNARCHIVED_FOLDER_ID) {
        result = result.filter((note) => getFolderIdFromTags(note.tags) === null);
      } else {
        result = result.filter((note) => getFolderIdFromTags(note.tags) === selectedFolderId);
      }
    }

    if (tagFilter !== 'all') {
      result = result.filter((note) => getDisplayTags(note.tags).includes(tagFilter));
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (note) =>
          note.title.toLowerCase().includes(query)
          || extractEditorPlainText(note.contentDoc || note.content).toLowerCase().includes(query),
      );
    }

    return result;
  }, [paperIdFilter, searchQuery, selectedFolderId, tagFilter, userNotes]);

  const archivedNotes = useMemo(
    () => filteredNotes.filter((note) => getFolderIdFromTags(note.tags) !== null),
    [filteredNotes],
  );
  const unarchivedNotes = useMemo(
    () => filteredNotes.filter((note) => getFolderIdFromTags(note.tags) === null),
    [filteredNotes],
  );

  const handleSave = useCallback(async (content: any) => {
    if (!selectedNoteId) {
      return;
    }
    const note = userNotes.find((candidate) => candidate.id === selectedNoteId);
    if (!note) {
      return;
    }

    const folderId = getFolderIdFromTags(note.tags) || selectedFolderId;
    const nextTags = folderId ? upsertFolderTag(note.tags, folderId) : note.tags;

    await updateNote.mutateAsync({
      id: selectedNoteId,
      payload: {
        contentDoc: normalizeEditorDocument(content),
        title: note.title || '未命名笔记',
        tags: nextTags,
        paperIds: note.paperIds,
      },
    });
  }, [selectedFolderId, selectedNoteId, updateNote, userNotes]);

  const { status: saveStatus, lastSaved, retrySave } = useAutoSave({
    content: editorContent,
    onSave: handleSave,
    debounceMs: 1000,
    noteId: selectedNoteId || undefined,
  });

  const hasUnsavedChanges = useMemo(() => {
    if (!selectedNote || !editorContent) {
      return false;
    }
    const currentContent = JSON.stringify(normalizeEditorDocument(selectedNote.contentDoc || selectedNote.content));
    return JSON.stringify(editorContent) !== currentContent;
  }, [editorContent, selectedNote]);

  const selectedNoteDisplayTitle = useMemo(
    () => (selectedNote ? buildNoteDisplayTitle(selectedNote, paperTitleMap) : ''),
    [paperTitleMap, selectedNote],
  );

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

  useEffect(() => {
    if (userNotes.length === 0 && derivedSummaries.length === 0) {
      return;
    }
    if (selectedNoteId && userNotes.some((note) => note.id === selectedNoteId)) {
      return;
    }
    if (selectedSummaryPaperId && derivedSummaries.some((summary) => summary.paperId === selectedSummaryPaperId)) {
      return;
    }

    if (noteIdQuery) {
      const target = userNotes.find((note) => note.id === noteIdQuery);
      if (target) {
        handleSelectNote(target, 'auto');
        return;
      }
    }

    if (!paperIdFilter) {
      return;
    }

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

  const handleCreateNote = useCallback(async () => {
    if (!selectedFolderId) {
      setPendingCreateAfterFolder(true);
      toast.warning('请先创建或选择文件夹，再创建笔记');
      return;
    }

    try {
      const baseTags = upsertFolderTag([], selectedFolderId);
      const payloadTags = paperIdFilter ? [...baseTags, `${PAPER_TAG_PREFIX}${paperIdFilter}`] : baseTags;
      const paperTitle = paperIdFilter ? paperTitleMap.get(paperIdFilter) : null;
      const nextTitle = paperTitle ? `《${paperTitle}》阅读笔记` : '未命名笔记';
      const newNote = await createNote.mutateAsync({
        title: nextTitle,
        contentDoc: createEmptyEditorDocument(),
        sourceType: 'manual',
        tags: payloadTags,
        paperIds: paperIdFilter ? [paperIdFilter] : [],
      });

      toast.success('笔记已创建');
      handleSelectNote(newNote);
      setEditorContent(createEmptyEditorDocument());

      const nextParams = new URLSearchParams(searchParams);
      nextParams.set('noteId', newNote.id);
      setSearchParams(nextParams, { replace: true });
    } catch {
      toast.error('创建笔记失败');
    }
  }, [createNote, handleSelectNote, paperIdFilter, paperTitleMap, searchParams, selectedFolderId, setSearchParams]);

  useEffect(() => {
    if (!pendingCreateAfterFolder || !selectedFolderId) {
      return;
    }
    setPendingCreateAfterFolder(false);
    void handleCreateNote();
  }, [handleCreateNote, pendingCreateAfterFolder, selectedFolderId]);

  const handleDeleteNote = useCallback(async () => {
    if (!deleteNoteId) {
      return;
    }
    try {
      await deleteNote.mutateAsync(deleteNoteId);
      toast.success('删除成功');
      if (selectedNoteId === deleteNoteId) {
        const remaining = filteredNotes.filter((note) => note.id !== deleteNoteId);
        const nextNote = remaining[0];
        if (nextNote) {
          handleSelectNote(nextNote);
        } else {
          setSelectedNoteId(null);
          setEditorContent(null);
        }
      }
      setDeleteNoteId(null);
    } catch {
      toast.error('删除失败');
    }
  }, [deleteNote, deleteNoteId, filteredNotes, handleSelectNote, selectedNoteId]);

  const handleCreateFolder = useCallback((name: string, parentId: string | null) => {
    const newFolder: NotesFolder = {
      id: `manual:${Date.now()}`,
      name,
      parentId,
      noteCount: 0,
      source: 'manual',
    };
    setManualFolders((current) => [...current, newFolder]);
    setSelectedFolderId(newFolder.id);
    setFolderSelectionSource('manual');
    toast.success(`文件夹「${name}」已创建`);
  }, [setSelectedFolderId]);

  const handleSelectFolder = useCallback((folderId: string | null) => {
    setSelectedFolderId(folderId);
    setFolderSelectionSource('manual');
  }, [setSelectedFolderId]);

  const handleEditorChange = useCallback((json: any) => {
    setEditorContent(json);

    if (!selectedNote || selectedNote.title !== '未命名笔记') {
      return;
    }

    const textParts: string[] = [];
    const walk = (nodes: any[]) => {
      nodes.forEach((node) => {
        if (node?.text) {
          textParts.push(node.text);
        }
        if (Array.isArray(node?.content)) {
          walk(node.content);
        }
      });
    };

    if (Array.isArray(json?.content)) {
      walk(json.content);
    }

    const firstLine = textParts.join(' ').trim().split('\n')[0]?.trim();
    if (!firstLine) {
      return;
    }

    const generatedTitle = firstLine.slice(0, 48) || '未命名笔记';
    if (generatedTitle === selectedNote.title) {
      return;
    }

    void updateNote.mutateAsync({
      id: selectedNote.id,
      payload: { title: generatedTitle },
    });
  }, [selectedNote, updateNote]);

  const handleRetrySave = useCallback(async () => {
    setRetryingSave(true);
    try {
      retrySave();
    } finally {
      window.setTimeout(() => setRetryingSave(false), 400);
    }
  }, [retrySave]);

  const handleSummaryToNote = useCallback(async (summary: ReadingSummaryProjection) => {
    const targetFolderId = selectedFolderId || summary.folderId;
    if (!targetFolderId) {
      setPendingCreateAfterFolder(true);
      toast.warning('请先选择文件夹，再将系统摘要转为笔记');
      return;
    }

    try {
      const newNote = await createNote.mutateAsync({
        title: `${summary.title} · 摘要笔记`,
        contentDoc: normalizeEditorDocument(summary.readingNotes),
        sourceType: 'manual',
        tags: upsertFolderTag([], targetFolderId),
        paperIds: [summary.paperId],
      });
      handleSelectNote(newNote);
      toast.success('已转为用户笔记');
    } catch {
      toast.error('转换失败');
    }
  }, [createNote, handleSelectNote, selectedFolderId]);

  const handleSummaryAppendToCurrent = useCallback((summary: ReadingSummaryProjection) => {
    if (!selectedNoteId || !editorContent) {
      toast.warning('请先选中一条用户笔记');
      return;
    }

    const summaryDoc = normalizeEditorDocument(summary.readingNotes);
    const next = {
      ...(editorContent || createEmptyEditorDocument()),
      content: [
        ...((editorContent?.content as any[]) || []),
        {
          type: 'paragraph',
          content: [{ type: 'text', text: `【系统摘要】${summary.title}` }],
        },
        ...summaryDoc.content,
      ],
    };
    setEditorContent(next);
    toast.success('摘要内容已加入当前笔记');
  }, [editorContent, selectedNoteId]);

  const activeFilterChips = useMemo(() => {
    const chips: Array<{ key: string; label: string; onClear: () => void }> = [];
    if (paperIdFilter) {
      chips.push({
        key: 'paper',
        label: `论文: ${paperTitleMap.get(paperIdFilter) || paperIdFilter}`,
        onClear: () => {
          const next = new URLSearchParams(searchParams);
          next.delete('paperId');
          setSearchParams(next, { replace: true });
        },
      });
    }
    if (selectedFolderId) {
      const folderName = folders.find((folder) => folder.id === selectedFolderId)?.name || selectedFolderId;
      chips.push({
        key: 'folder',
        label: `文件夹: ${folderName}`,
        onClear: () => handleSelectFolder(null),
      });
    }
    if (tagFilter !== 'all') {
      chips.push({
        key: 'tag',
        label: `标签: ${tagFilter}`,
        onClear: () => setTagFilter('all'),
      });
    }
    if (searchQuery.trim()) {
      chips.push({
        key: 'query',
        label: `关键词: ${searchQuery.trim()}`,
        onClear: () => setSearchQuery(''),
      });
    }
    return chips;
  }, [folders, handleSelectFolder, paperIdFilter, paperTitleMap, searchParams, searchQuery, selectedFolderId, setSearchParams, setTagFilter, tagFilter]);

  const summaryItems = useMemo(
    () => derivedSummaries.map((summary) => ({
      summary,
      title: summary.title,
      preview: humanizeSummaryPreview(summary.readingNotes),
    })),
    [derivedSummaries],
  );

  const archivedNoteItems = useMemo(
    () => archivedNotes.map((note) => {
      const displayTags = getDisplayTags(note.tags);
      const primaryPaperId = note.paperIds[0] || getPaperIdTag(note.tags);
      const paperLabel =
        (primaryPaperId && paperTitleMap.get(primaryPaperId))
        || getPaperTitleTag(note.tags);

      return {
        note,
        displayTitle: buildNoteDisplayTitle(note, paperTitleMap),
        preview: notePreviewText(note),
        paperLabel,
        displayTag: displayTags[0] || null,
        updatedAtLabel: formatDate(note.updatedAt),
      };
    }),
    [archivedNotes, notePreviewText, paperTitleMap],
  );

  const unarchivedNoteItems = useMemo(
    () => unarchivedNotes.map((note) => ({
      note,
      displayTitle: buildNoteDisplayTitle(note, paperTitleMap),
      preview: notePreviewText(note),
      paperLabel: null,
      displayTag: null,
      updatedAtLabel: formatDate(note.updatedAt),
    })),
    [notePreviewText, paperTitleMap, unarchivedNotes],
  );

  const handleCommitEditedTitle = useCallback(async () => {
    const nextTitle = draftTitle.trim() || '未命名笔记';
    setEditingTitle(false);
    if (!selectedNote || nextTitle === selectedNoteDisplayTitle) {
      return;
    }

    await updateNote.mutateAsync({
      id: selectedNote.id,
      payload: { title: nextTitle },
    });
  }, [draftTitle, selectedNote, selectedNoteDisplayTitle, updateNote]);

  return {
    headerProps: {
      catalogLoading,
      paperIdFilter,
      paperTitle: paperIdFilter ? paperTitleMap.get(paperIdFilter) || paperIdFilter : null,
      onClearPaperFilter: () => {
        const next = new URLSearchParams(searchParams);
        next.delete('paperId');
        setSearchParams(next, { replace: true });
      },
    },
    sidebarProps: {
      selectedFolderId,
      selectedNoteId,
      selectedSummaryPaperId,
      searchQuery,
      tagFilter,
      allTags,
      folders,
      activeFilterChips,
      notesLoading,
      catalogLoading,
      summaryItems,
      archivedNoteItems,
      unarchivedNoteItems,
      onCreateNote: () => void handleCreateNote(),
      onSearchQueryChange: setSearchQuery,
      onTagFilterChange: setTagFilter,
      onSelectFolder: handleSelectFolder,
      onCreateFolder: handleCreateFolder,
      onSelectSummary: handleSelectSummary,
      onSummaryAppend: handleSummaryAppendToCurrent,
      onSummaryToNote: (summary: ReadingSummaryProjection) => void handleSummaryToNote(summary),
      onSelectNote: handleSelectNote,
      onDeleteNoteRequest: setDeleteNoteId,
    },
    mainPanelProps: {
      selectedNote,
      selectedSummary,
      selectedNoteDisplayTitle,
      editingTitle,
      draftTitle,
      editorContent,
      paperIdFilter,
      paperTitleMap,
      onDraftTitleChange: setDraftTitle,
      onStartEditingTitle: () => {
        setDraftTitle(selectedNoteDisplayTitle);
        setEditingTitle(true);
      },
      onCommitTitle: () => {
        void handleCommitEditedTitle();
      },
      onCancelEditingTitle: () => setEditingTitle(false),
      onInsertPaperReference: () => {
        const refText = `[[pdf:${paperIdFilter}:page:1]]`;
        setEditorContent({
          ...(editorContent || createEmptyEditorDocument()),
          content: [
            ...((editorContent?.content as any[]) || []),
            { type: 'paragraph', content: [{ type: 'text', text: refText }] },
          ],
        });
        toast.success('已插入论文引用');
      },
      onEditorChange: handleEditorChange,
    },
    saveIndicatorProps: {
      selectedNoteId,
      hasUnsavedChanges,
      retryingSave,
      saveStatus,
      lastSaved,
      onRetrySave: handleRetrySave,
    },
    deleteDialogProps: {
      open: !!deleteNoteId,
      onOpenChange: (open: boolean) => {
        if (!open) {
          setDeleteNoteId(null);
        }
      },
      onConfirmDelete: () => void handleDeleteNote(),
    },
  };
}
