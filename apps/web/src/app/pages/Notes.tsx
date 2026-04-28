/**
 * Notes Page — Folder-first note management
 *
 * Improvements:
 * - Folder-first workflow: must choose/create folder before creating notes
 * - KB folders are auto-generated from knowledge bases
 * - AI reading notes are synchronized into notes list and placed in KB folders
 * - Read page and Notes page are linked via query params (paperId/noteId)
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import type { ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router';
import { useNotes, useCreateNote, useUpdateNote, useDeleteNote } from '@/hooks/useNotes';
import type { Note } from '@/services/notesApi';
import { NotesEditor } from '@/app/components/NotesEditor';
import { useAutoSave } from '@/app/hooks/useAutoSave';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import { Badge } from '@/app/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/app/components/ui/select';
import { NoteFolderTree } from '@/app/components/NoteFolderTree';
import type { NoteFolder } from '@/app/components/NoteFolderTree';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/app/components/ui/alert-dialog';
import {
  FileText,
  Plus,
  Search,
  Trash2,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Clock,
  FolderOpen,
  Sparkles,
} from 'lucide-react';
import { toast } from 'sonner';
import { clsx } from 'clsx';
import { kbApi } from '@/services/kbApi';
import * as papersApi from '@/services/papersApi';
import {
  createEmptyEditorDocument,
  filterUserEditableNotes,
  type ReadingSummaryProjection,
} from '@/features/notes/ownership';
import {
  extractEditorPlainText,
  normalizeEditorDocument,
} from '@/features/notes/content';
import { LinkedEvidenceList } from '@/features/notes/components/LinkedEvidenceList';

const MANUAL_FOLDERS_STORAGE_KEY = 'notes-manual-folders-v1';
const FOLDER_TAG_PREFIX = 'folder:';
const PAPER_TAG_PREFIX = 'paper:';
const PAPER_TITLE_TAG_PREFIX = 'paper-title:';
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

function highlightText(text: string, query: string): ReactNode {
  if (!query.trim()) return text;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escaped})`, 'gi');
  const parts = text.split(regex);

  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <mark key={i} className="bg-yellow-200 text-inherit rounded px-0.5">
        {part}
      </mark>
    ) : (
      part
    ),
  );
}

function decodeTagValue(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function getFolderIdFromTags(tags: string[]): string | null {
  const folderTag = tags.find((tag) => tag.startsWith(FOLDER_TAG_PREFIX));
  return folderTag ? folderTag.slice(FOLDER_TAG_PREFIX.length) : null;
}

function upsertFolderTag(tags: string[], folderId: string): string[] {
  const withoutFolder = tags.filter((tag) => !tag.startsWith(FOLDER_TAG_PREFIX));
  return [...withoutFolder, `${FOLDER_TAG_PREFIX}${folderId}`];
}

function getDisplayTags(tags: string[]): string[] {
  return tags.filter(
    (tag) =>
      !tag.startsWith(FOLDER_TAG_PREFIX) &&
      !tag.startsWith(PAPER_TAG_PREFIX) &&
      !tag.startsWith(PAPER_TITLE_TAG_PREFIX),
  );
}

function getPaperTitleTag(tags: string[]): string | null {
  const paperTitleTag = tags.find((tag) => tag.startsWith(PAPER_TITLE_TAG_PREFIX));
  if (!paperTitleTag) {
    return null;
  }
  return decodeTagValue(paperTitleTag.slice(PAPER_TITLE_TAG_PREFIX.length));
}

function getPaperIdTag(tags: string[]): string | null {
  const paperTag = tags.find((tag) => tag.startsWith(PAPER_TAG_PREFIX));
  return paperTag ? paperTag.slice(PAPER_TAG_PREFIX.length) : null;
}

/**
 * Internal component that uses Router hooks
 * Extracted to ensure Router context is available
 */
function NotesContent() {
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
  const [tagFilter, setTagFilter] = useState<string>('all');
  const [deleteNoteId, setDeleteNoteId] = useState<string | null>(null);
  const [editorContent, setEditorContent] = useState<any>(null);
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [folderSelectionSource, setFolderSelectionSource] = useState<FolderSelectionSource | null>(null);
  const [pendingCreateAfterFolder, setPendingCreateAfterFolder] = useState(false);
  const [retryingSave, setRetryingSave] = useState(false);
  const [editingTitle, setEditingTitle] = useState(false);
  const [draftTitle, setDraftTitle] = useState('');

  const [kbFolders, setKbFolders] = useState<NotesFolder[]>([]);
  const [manualFolders, setManualFolders] = useState<NotesFolder[]>([]);
  const [paperCatalog, setPaperCatalog] = useState<PaperCatalogItem[]>([]);
  const [paperTitleMap, setPaperTitleMap] = useState<Map<string, string>>(new Map());

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
      if (Array.isArray(parsed)) {
        setManualFolders(parsed.filter((item) => item.source === 'manual'));
      }
    } catch {
      // Ignore malformed local storage data.
    }
  }, [selectedNote, updateNote]);

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

        const paperToKbFolder = new Map<string, string>();
        await Promise.all(
          knowledgeBases.map(async (kb) => {
            try {
              const paperResponse = await kbApi.listPapers(kb.id);
              (paperResponse.papers || []).forEach((paper) => {
                paperToKbFolder.set(paper.id, `kb:${kb.id}`);
              });
            } catch {
              // Keep best-effort mapping only.
            }
          }),
        );

        const papersResponse = await papersApi.list({ page: 1, limit: 200, sortBy: 'updatedAt' });
        const papers = papersResponse.data.papers || [];

        const nextTitleMap = new Map<string, string>();
        const nextCatalog: PaperCatalogItem[] = papers.map((paper) => {
          nextTitleMap.set(paper.id, paper.title || 'Untitled Paper');

          const normalized = paper as typeof paper & {
            readingNotes?: string | null;
            knowledgeBaseId?: string | null;
          };

          const folderId =
            (normalized.knowledgeBaseId ? `kb:${normalized.knowledgeBaseId}` : null) ||
            paperToKbFolder.get(paper.id) ||
            null;

          return {
            id: paper.id,
            title: paper.title || 'Untitled Paper',
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

    loadCatalog();
  }, []);

  const derivedSummaries = useMemo<ReadingSummaryProjection[]>(() => {
    let summaries = paperCatalog
      .filter((paper) => paper.readingNotes && paper.readingNotes.trim().length > 0)
      .map((paper) => ({
        paperId: paper.id,
        title: paper.title,
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
          summary.title.toLowerCase().includes(normalizedQuery) ||
          summary.readingNotes.toLowerCase().includes(normalizedQuery),
      );
    }

    return summaries;
  }, [paperCatalog, paperIdFilter, searchQuery, selectedFolderId]);

  const selectedSummary = useMemo(
    () => derivedSummaries.find((summary) => summary.paperId === selectedSummaryPaperId) || null,
    [derivedSummaries, selectedSummaryPaperId],
  );

  const folderCounts = useMemo(() => {
    const counts = new Map<string, number>();
    userNotes.forEach((note) => {
      const folderId = getFolderIdFromTags(note.tags);
      if (!folderId) {
        return;
      }
      counts.set(folderId, (counts.get(folderId) || 0) + 1);
    });
    return counts;
  }, [userNotes]);

  const folders = useMemo<NotesFolder[]>(() => {
    const merged = [...kbFolders, ...manualFolders];
    const mapped = merged.map((folder) => ({
      ...folder,
      noteCount: folderCounts.get(folder.id) || 0,
    }));
    const unarchivedCount = userNotes.filter((note) => getFolderIdFromTags(note.tags) === null).length;
    return [
      {
        id: UNARCHIVED_FOLDER_ID,
        name: '未归档',
        parentId: null,
        noteCount: unarchivedCount,
        source: 'manual' as const,
      },
      ...mapped,
    ];
  }, [folderCounts, kbFolders, manualFolders, userNotes]);

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

      if (selectedFolderId !== null || folderSelectionSource !== null) {
        setSelectedFolderId(null);
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

    if (selectedFolderId !== null || folderSelectionSource !== null) {
      setSelectedFolderId(null);
      setFolderSelectionSource(null);
    }
  }, [catalogLoading, folderSelectionSource, notesLoading, paperCatalog, paperIdFilter, selectedFolderId, userNotes]);

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
          note.title.toLowerCase().includes(query) ||
          extractEditorPlainText(note.contentDoc || note.content).toLowerCase().includes(query),
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

  const handleSave = useCallback(
    async (content: any) => {
      if (!selectedNoteId) return;
      const note = userNotes.find((n) => n.id === selectedNoteId);
      if (!note) return;

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
    },
    [selectedFolderId, selectedNoteId, updateNote, userNotes],
  );

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

  const handleSelectNote = useCallback((note: Note, selectionSource: FolderSelectionSource | null = 'manual') => {
    setSelectedSummaryPaperId(null);
    setSelectedNoteId(note.id);

    const folderId = getFolderIdFromTags(note.tags);
    if (folderId) {
      setSelectedFolderId(folderId);
      setFolderSelectionSource(selectionSource);
    } else {
      setSelectedFolderId(null);
      setFolderSelectionSource(null);
    }

    setEditorContent(normalizeEditorDocument(note.contentDoc || note.content));
  }, []);

  const handleSelectSummary = useCallback(
    (summary: ReadingSummaryProjection, selectionSource: FolderSelectionSource | null = 'manual') => {
    setSelectedNoteId(null);
    setSelectedSummaryPaperId(summary.paperId);
    setEditorContent(null);

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
    setSearchParams(nextParams, { replace: true });
  }, [searchParams, setSearchParams]);

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

    if (paperIdFilter) {
      const related = userNotes.find(
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
      const payloadTags = paperIdFilter
        ? [...baseTags, `${PAPER_TAG_PREFIX}${paperIdFilter}`]
        : baseTags;

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
    if (!pendingCreateAfterFolder) {
      return;
    }
    if (!selectedFolderId) {
      return;
    }
    setPendingCreateAfterFolder(false);
    void handleCreateNote();
  }, [handleCreateNote, pendingCreateAfterFolder, selectedFolderId]);

  const handleDeleteNote = useCallback(async () => {
    if (!deleteNoteId) return;
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
  }, [deleteNoteId, selectedNoteId, deleteNote, filteredNotes, handleSelectNote]);

  const handleCreateFolder = useCallback((name: string, parentId: string | null) => {
    const newFolder: NotesFolder = {
      id: `manual:${Date.now()}`,
      name,
      parentId,
      noteCount: 0,
      source: 'manual',
    };
    setManualFolders((prev) => [...prev, newFolder]);
    setSelectedFolderId(newFolder.id);
    setFolderSelectionSource('manual');
    toast.success(`文件夹「${name}」已创建`);
  }, []);

  const handleSelectFolder = useCallback((folderId: string | null) => {
    setSelectedFolderId(folderId);
    setFolderSelectionSource('manual');
  }, []);

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
      payload: {
        title: generatedTitle,
      },
    });
  }, []);

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
        sourceType: 'read',
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
  }, [folders, handleSelectFolder, paperIdFilter, paperTitleMap, searchParams, searchQuery, selectedFolderId, setSearchParams, tagFilter]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const SaveIndicator = () => {
    if (!selectedNoteId) return null;

    if (!window.navigator.onLine) {
      return (
        <div className="flex items-center gap-1.5 text-xs text-amber-700">
          <AlertCircle className="w-3 h-3" />
          <span>离线模式，修改将在联网后保存</span>
        </div>
      );
    }

    if (saveStatus === 'idle' && hasUnsavedChanges) {
      return (
        <div className="flex items-center gap-1.5 text-xs text-amber-700">
          <Clock className="w-3 h-3" />
          <span>有未保存修改</span>
        </div>
      );
    }

    if (saveStatus === 'saving') {
      return (
        <div className="flex items-center gap-1.5 text-xs text-yellow-600">
          <Loader2 className="w-3 h-3 animate-spin" />
          <span>保存中...</span>
        </div>
      );
    }

    if (saveStatus === 'error') {
      return (
        <button
          type="button"
          onClick={handleRetrySave}
          className="flex items-center gap-1.5 text-xs text-destructive hover:underline"
        >
          <AlertCircle className="w-3 h-3" />
          <span>{retryingSave ? '重试中...' : '保存失败，点击重试'}</span>
        </button>
      );
    }

    if (saveStatus === 'saved' && lastSaved) {
      return (
        <div className="flex items-center gap-1.5 text-xs text-green-600">
          <CheckCircle2 className="w-3 h-3" />
          <span>已保存 {lastSaved.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="relative min-h-screen bg-background">
      <div className="magazine-toolbar sticky top-0 z-10 border-b border-border/50 bg-background/95 backdrop-blur-md">
        <div className="px-6 py-5 flex items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold text-foreground tracking-tight">笔记</h1>
            <p className="text-[11px] font-medium text-muted-foreground mt-1">Notes Workspace</p>
          </div>
          <div className="flex items-center gap-2">
            {catalogLoading && (
              <Badge variant="outline" className="text-[9px] uppercase tracking-wider font-bold">
                <Loader2 className="h-3 w-3 animate-spin mr-1" />
                同步目录中
              </Badge>
            )}
          </div>
        </div>
        {paperIdFilter && (
          <div className="px-6 pb-4 flex items-center gap-2 flex-wrap">
            <span className="text-xs text-muted-foreground">
              当前筛选：论文《{paperTitleMap.get(paperIdFilter) || paperIdFilter}》
            </span>
            <Button asChild size="sm" variant="outline" className="h-7">
              <Link to={`/read/${paperIdFilter}?source=notes`}>回到阅读页</Link>
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-7"
              onClick={() => {
                const next = new URLSearchParams(searchParams);
                next.delete('paperId');
                setSearchParams(next, { replace: true });
              }}
            >
              清除筛选
            </Button>
          </div>
        )}
      </div>

      <div className="relative flex h-[calc(100vh-10rem)] bg-background/50">
        <div className="absolute left-4 top-4 bottom-4 w-[300px] bg-white rounded-lg border border-border/40 flex flex-col shadow-2xl z-10">
          <div className="px-5 py-5 border-b border-border/30 space-y-4 bg-gradient-to-b from-white to-slate-50/50">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold tracking-wide text-foreground">笔记库</h2>
              <Button variant="outline" size="sm" className="h-6 px-2.5 text-[9px] uppercase font-bold tracking-wider rounded-sm shadow-sm" onClick={handleCreateNote}>
                <Plus className="w-3 h-3 mr-1" />
                新建
              </Button>
            </div>
            {!selectedFolderId && (
              <p className="rounded border border-amber-200 bg-amber-50/50 px-2.5 py-1.5 text-[11px] text-amber-800">
                请选择文件夹后再新建笔记。
              </p>
            )}

            <div className="relative group">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" />
              <Input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索..."
                className="pl-8 h-8 text-xs bg-background/50 border-border/40 focus-visible:ring-1 focus-visible:ring-primary/50 shadow-sm rounded"
              />
            </div>

            {allTags.length > 0 && (
              <Select value={tagFilter} onValueChange={setTagFilter}>
                <SelectTrigger className="h-8 text-xs bg-background/50 border-border/40 focus:ring-1 focus:ring-primary/50 shadow-sm">
                  <SelectValue placeholder="全部标签" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all" className="text-xs">全部标签</SelectItem>
                  {allTags.map((tag) => (
                    <SelectItem key={tag} value={tag} className="text-xs">
                      {tag}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          <div className="border-t border-b border-blue-200/40 bg-blue-50/30 px-4 py-3">
            <div className="text-[10px] font-semibold text-blue-700/90 mb-3 px-1 pb-2 flex justify-between items-center border-b border-blue-200/30">
              <span>文件夹</span>
            </div>
            <NoteFolderTree
              folders={folders}
              selectedFolderId={selectedFolderId}
              onSelectFolder={handleSelectFolder}
              onCreateFolder={handleCreateFolder}
            />
          </div>

          <div className="flex-1 overflow-y-auto bg-background/40 border-t border-border/30">
            {activeFilterChips.length > 0 && (
              <div className="px-3 py-2 border-b border-border/50 flex flex-wrap gap-2 bg-background/60">
                {activeFilterChips.map((chip) => (
                  <button
                    key={chip.key}
                    type="button"
                    onClick={chip.onClear}
                    className="inline-flex items-center gap-1 rounded-full border border-border/70 px-2 py-0.5 text-[10px] text-foreground/80 hover:bg-muted"
                  >
                    <span>{chip.label}</span>
                    <span aria-hidden="true">×</span>
                  </button>
                ))}
              </div>
            )}

            {(notesLoading || catalogLoading) && (
              <div className="flex items-center justify-center py-8 text-muted-foreground text-xs">
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                加载中...
              </div>
            )}

            {!notesLoading && !catalogLoading && filteredNotes.length === 0 && derivedSummaries.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <FileText className="w-10 h-10 mb-3 opacity-40" />
                <p className="text-xs font-medium">暂无笔记</p>
                <p className="text-[10px] mt-1">你可以：选择已有笔记、查看系统摘要，或先选择文件夹后创建笔记</p>
              </div>
            )}

            {!notesLoading && derivedSummaries.length > 0 && (
              <div className="border-b border-border/60 bg-amber-50/30">
                <div className="px-3 py-2.5 text-[10px] font-semibold text-amber-700/90 border-b border-amber-200/30">
                  系统摘要
                </div>
                {derivedSummaries.map((summary) => (
                  <button
                    key={summary.paperId}
                    type="button"
                    className={clsx(
                      'w-full px-3 py-3 text-left transition-all duration-150 border-l-2 border-l-transparent group',
                      selectedSummaryPaperId === summary.paperId 
                        ? 'bg-primary/[0.03] border-l-primary' 
                        : 'hover:bg-primary/[0.02] hover:border-l-primary/30',
                    )}
                    onClick={() => handleSelectSummary(summary)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-amber-950 line-clamp-1">{summary.title}</p>
                        <p className="mt-1 text-[11px] text-amber-900/80 line-clamp-2">
                          {highlightText(extractEditorPlainText(summary.readingNotes, 80) || '系统摘要', searchQuery)}
                        </p>
                        <p className="mt-1 text-[10px] text-amber-800/80">系统生成 · 只读</p>
                        <div className="mt-2 flex items-center gap-1">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-6 px-2 text-[10px]"
                            onClick={(event) => {
                              event.stopPropagation();
                              handleSummaryAppendToCurrent(summary);
                            }}
                          >
                            加入当前笔记
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-6 px-2 text-[10px]"
                            onClick={(event) => {
                              event.stopPropagation();
                              void handleSummaryToNote(summary);
                            }}
                          >
                            转为笔记
                          </Button>
                          <Button asChild size="sm" variant="ghost" className="h-6 px-2 text-[10px]">
                            <Link to={`/read/${summary.paperId}?source=notes`}>打开阅读页</Link>
                          </Button>
                        </div>
                      </div>
                      <Badge variant="secondary" className="h-4 shrink-0 px-1 text-[9px]">
                        摘要
                      </Badge>
                    </div>
                  </button>
                ))}
              </div>
            )}

            {!notesLoading && (archivedNotes.length > 0 || unarchivedNotes.length > 0) && (
              <div className="divide-y divide-border/50">
                {archivedNotes.map((note) => {
                  const displayTags = getDisplayTags(note.tags);
                  const primaryPaperId = note.paperIds[0] || getPaperIdTag(note.tags);
                  const paperLabel =
                    (primaryPaperId && paperTitleMap.get(primaryPaperId)) ||
                    getPaperTitleTag(note.tags);

                  return (
                    <div
                      key={note.id}
                      className={clsx(
                        'group p-3 cursor-pointer transition-all duration-150 border-l-2 border-l-transparent',
                        selectedNoteId === note.id 
                          ? 'bg-primary/[0.03] border-l-primary' 
                          : 'hover:bg-primary/[0.02] hover:border-l-primary/50',
                      )}
                      onClick={() => handleSelectNote(note)}
                    >
                      <div className="flex items-start justify-between gap-1">
                        <h4 className="text-sm font-medium line-clamp-1 flex-1">
                          {highlightText(note.title || '未命名笔记', searchQuery)}
                        </h4>
                        <div className="flex items-center gap-1">
                          <button
                            className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-all"
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeleteNoteId(note.id);
                            }}
                            aria-label="删除笔记"
                            title="删除笔记"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </div>

                      {paperLabel && (
                        <div className="mt-1 flex items-center gap-1 text-[10px] text-amber-700">
                          <FolderOpen className="w-3 h-3" />
                          <span className="truncate">{paperLabel}</span>
                        </div>
                      )}

                      <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                        {highlightText(extractEditorPlainText(note.contentDoc || note.content, 80) || '空笔记', searchQuery)}
                      </p>

                      <div className="flex items-center gap-2 mt-1.5">
                        <Clock className="w-2.5 h-2.5 text-muted-foreground/60" />
                        <span className="text-[10px] text-muted-foreground/60">{formatDate(note.updatedAt)}</span>
                        {displayTags.length > 0 && (
                          <Badge variant="outline" className="text-[9px] px-1 py-0 h-4">
                            {displayTags[0]}
                          </Badge>
                        )}
                      </div>
                    </div>
                  );
                })}

                {unarchivedNotes.length > 0 && (
                  <div className="border-t border-border/60 bg-muted/20">
                    <div className="px-3 py-2 text-[10px] font-semibold text-muted-foreground">未归档</div>
                    {unarchivedNotes.map((note) => (
                      <div
                        key={note.id}
                        className={clsx(
                          'group p-3 cursor-pointer transition-all duration-150 border-l-2 border-l-transparent',
                          selectedNoteId === note.id
                            ? 'bg-primary/[0.03] border-l-primary'
                            : 'hover:bg-primary/[0.02] hover:border-l-primary/50',
                        )}
                        onClick={() => handleSelectNote(note)}
                      >
                        <div className="flex items-start justify-between gap-1">
                          <h4 className="text-sm font-medium line-clamp-1 flex-1">{note.title || '未命名笔记'}</h4>
                          <button
                            className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-all"
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeleteNoteId(note.id);
                            }}
                            aria-label="删除笔记"
                            title="删除笔记"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                        <p className="text-xs text-muted-foreground line-clamp-2 mt-1">{extractEditorPlainText(note.contentDoc || note.content, 80) || '空笔记'}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="ml-[320px] flex-1 flex flex-col bg-background border-l border-border/20 rounded-tl-lg rounded-bl-lg">
          {selectedNote ? (
            <>
              <div className="flex items-center justify-between px-5 py-3 border-b border-border/50 bg-background/60 backdrop-blur-sm">
                <div>
                  {editingTitle ? (
                    <Input
                      value={draftTitle}
                      onChange={(event) => setDraftTitle(event.target.value)}
                      className="h-8 w-[320px] text-sm"
                      onBlur={() => {
                        const nextTitle = draftTitle.trim() || '未命名笔记';
                        setEditingTitle(false);
                        if (nextTitle === selectedNote.title) {
                          return;
                        }
                        void updateNote.mutateAsync({
                          id: selectedNote.id,
                          payload: {
                            title: nextTitle,
                          },
                        });
                      }}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') {
                          event.currentTarget.blur();
                        }
                        if (event.key === 'Escape') {
                          setEditingTitle(false);
                        }
                      }}
                      autoFocus
                    />
                  ) : (
                    <button
                      type="button"
                      className="text-left font-semibold text-sm tracking-tight hover:text-primary"
                      onClick={() => {
                        setDraftTitle(selectedNote.title || '未命名笔记');
                        setEditingTitle(true);
                      }}
                    >
                      {selectedNote.title || '未命名笔记'}
                    </button>
                  )}
                  <div className="flex items-center gap-2 mt-1">
                    {selectedNote.paperIds.length > 0 && (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <FileText className="w-3 h-3" />
                        <span>关联 {selectedNote.paperIds.length} 篇论文</span>
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {paperIdFilter && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 text-[10px]"
                      onClick={() => {
                        const refText = `[[pdf:${paperIdFilter}:page:1]]`;
                        const next = {
                          ...(editorContent || createEmptyEditorDocument()),
                          content: [
                            ...((editorContent?.content as any[]) || []),
                            { type: 'paragraph', content: [{ type: 'text', text: refText }] },
                          ],
                        };
                        setEditorContent(next);
                        toast.success('已插入论文引用');
                      }}
                    >
                      插入论文引用
                    </Button>
                  )}
                  <SaveIndicator />
                </div>
              </div>

              <div className="flex-1 p-6 overflow-auto bg-background">
                <div className="mx-auto max-w-4xl">
                  <LinkedEvidenceList evidence={selectedNote.linkedEvidence || []} />
                  <NotesEditor
                    content={editorContent}
                    onChange={handleEditorChange}
                    placeholder="开始写笔记... 使用 [[pdf:paperId:page:5]] 引用论文"
                  />
                </div>
              </div>
            </>
          ) : selectedSummary ? (
            <>
              <div className="flex items-center justify-between px-5 py-3 border-b border-border/50 bg-background/60 backdrop-blur-sm">
                <div>
                  <h3 className="font-medium text-sm">{selectedSummary.title}</h3>
                  <div className="flex items-center gap-2 mt-0.5 text-xs text-muted-foreground">
                    <Badge variant="secondary" className="text-[10px] h-4">
                      <Sparkles className="w-2.5 h-2.5 mr-0.5" />
                      系统生成摘要
                    </Badge>
                    <span>来自 paper.reading_notes 的派生展示</span>
                  </div>
                </div>
                <Button asChild variant="outline" size="sm">
                  <Link to={`/read/${selectedSummary.paperId}`}>打开论文</Link>
                </Button>
              </div>

              <div className="flex-1 overflow-auto px-6 py-5 bg-background">
                <div className="mx-auto max-w-3xl rounded-xl border border-amber-200/60 bg-amber-50/30 p-6 shadow-xs">
                  <p className="mb-4 text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">
                    系统摘要 - 只读视图
                  </p>
                  <NotesEditor
                    content={normalizeEditorDocument(selectedSummary.readingNotes)}
                    onChange={() => {}}
                    readOnly
                    hideToolbar
                  />
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground bg-gradient-to-b from-background to-slate-50/30">
              <FileText className="w-12 h-12 mb-3 opacity-30" />
              <p className="text-sm font-medium">选择内容开始编辑</p>
              <p className="text-xs mt-2 text-muted-foreground/60">你可以选择用户笔记、打开系统摘要，或先选择文件夹后新建笔记</p>
            </div>
          )}
        </div>
      </div>

      <AlertDialog open={!!deleteNoteId} onOpenChange={(open) => !open && setDeleteNoteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>此操作不可撤销</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteNote}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

/**
 * Outer Notes component wrapper
 * This ensures the Router context is available when NotesContent is rendered
 */
export function Notes() {
  return <NotesContent />;
}
