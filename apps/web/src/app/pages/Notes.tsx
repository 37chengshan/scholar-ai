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
import { Link, useSearchParams } from 'react-router-dom';
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

const MANUAL_FOLDERS_STORAGE_KEY = 'notes-manual-folders-v1';
const FOLDER_TAG_PREFIX = 'folder:';
const PAPER_TAG_PREFIX = 'paper:';
const PAPER_TITLE_TAG_PREFIX = 'paper-title:';

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

function parseEditorContent(content: unknown): any | null {
  if (!content) {
    return null;
  }

  if (typeof content === 'string') {
    try {
      return JSON.parse(content);
    } catch {
      return {
        type: 'doc',
        content: [{ type: 'paragraph', content: [{ type: 'text', text: content }] }],
      };
    }
  }

  if (typeof content === 'object') {
    return content;
  }

  return null;
}

function extractPreview(content: unknown, maxLength = 80): string {
  const parsed = parseEditorContent(content);
  if (!parsed || !parsed.content) return '';
  const texts: string[] = [];

  function walk(nodes: any[]) {
    for (const node of nodes) {
      if (node.text) {
        texts.push(node.text);
      }
      if (node.content) {
        walk(node.content);
      }
    }
  }

  walk(parsed.content);
  const full = texts.join(' ').trim();
  const cleaned = full.replace(/\[\[pdf:[^:]+:page:\d+\]\]/g, '');
  return cleaned.length > maxLength ? `${cleaned.slice(0, maxLength)}...` : cleaned;
}

function highlightText(text: string, query: string): ReactNode {
  if (!query.trim()) return text;
  const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  const parts = text.split(regex);

  return parts.map((part, i) =>
    regex.test(part) ? (
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
    return merged.map((folder) => ({
      ...folder,
      noteCount: folderCounts.get(folder.id) || 0,
    }));
  }, [folderCounts, kbFolders, manualFolders]);

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
      result = result.filter((note) => getFolderIdFromTags(note.tags) === selectedFolderId);
    }

    if (tagFilter !== 'all') {
      result = result.filter((note) => getDisplayTags(note.tags).includes(tagFilter));
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (note) =>
          note.title.toLowerCase().includes(query) ||
          extractPreview(note.content).toLowerCase().includes(query),
      );
    }

    return result;
  }, [paperIdFilter, searchQuery, selectedFolderId, tagFilter, userNotes]);

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
          content: JSON.stringify(content),
          title: note.title || '未命名笔记',
          tags: nextTags,
          paperIds: note.paperIds,
        },
      });
    },
    [selectedFolderId, selectedNoteId, updateNote, userNotes],
  );

  const { status: saveStatus, lastSaved } = useAutoSave({
    content: editorContent,
    onSave: handleSave,
    debounceMs: 1000,
    noteId: selectedNoteId || undefined,
  });

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

    try {
      setEditorContent(JSON.parse(note.content));
    } catch {
      setEditorContent({
        type: 'doc',
        content: [{ type: 'paragraph', content: [{ type: 'text', text: note.content }] }],
      });
    }
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
      toast.warning('请先创建或选择文件夹，再创建笔记');
      return;
    }

    try {
      const baseTags = upsertFolderTag([], selectedFolderId);
      const payloadTags = paperIdFilter
        ? [...baseTags, `${PAPER_TAG_PREFIX}${paperIdFilter}`]
        : baseTags;

      const newNote = await createNote.mutateAsync({
        title: '未命名笔记',
        content: JSON.stringify(createEmptyEditorDocument()),
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
  }, [createNote, handleSelectNote, paperIdFilter, searchParams, selectedFolderId, setSearchParams]);

  const handleDeleteNote = useCallback(async () => {
    if (!deleteNoteId) return;
    try {
      await deleteNote.mutateAsync(deleteNoteId);
      toast.success('删除成功');
      if (selectedNoteId === deleteNoteId) {
        setSelectedNoteId(null);
        setEditorContent(null);
      }
      setDeleteNoteId(null);
    } catch {
      toast.error('删除失败');
    }
  }, [deleteNoteId, selectedNoteId, deleteNote]);

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
  }, []);

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
        <div className="flex items-center gap-1.5 text-xs text-destructive">
          <AlertCircle className="w-3 h-3" />
          <span>保存失败</span>
        </div>
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
      <div className="magazine-toolbar sticky top-0 z-10 border-b bg-background/95 backdrop-blur-sm">
        <div className="px-6 py-5">
          <div className="flex items-end justify-between gap-4">
            <div>
              <h1 className="font-serif text-3xl font-bold text-foreground tracking-tight">笔记</h1>
              <p className="text-sm text-muted-foreground mt-0.5 font-sans">Notes</p>
            </div>
            <div className="flex items-center gap-2">
              {paperIdFilter && (
                <Badge variant="secondary" className="text-xs">
                  论文筛选: {paperTitleMap.get(paperIdFilter) || paperIdFilter.slice(0, 8)}
                </Badge>
              )}
              {catalogLoading && (
                <Badge variant="outline" className="text-xs">
                  <Loader2 className="h-3 w-3 animate-spin mr-1" />
                  同步目录中
                </Badge>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="flex h-[calc(100vh-10rem)]">
        <div className="w-72 border-r border-zinc-300 bg-zinc-100 flex flex-col shrink-0">
          <div className="p-3 border-b border-zinc-200 space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="font-serif text-sm font-bold uppercase tracking-wider text-foreground">笔记</h2>
              <Button variant="default" size="sm" className="h-7 px-2" onClick={handleCreateNote}>
                <Plus className="w-3.5 h-3.5" />
                新建
              </Button>
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索笔记..."
                className="pl-8 h-8 text-xs"
              />
            </div>

            {allTags.length > 0 && (
              <Select value={tagFilter} onValueChange={setTagFilter}>
                <SelectTrigger className="h-7 text-xs">
                  <SelectValue placeholder="全部标签" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部标签</SelectItem>
                  {allTags.map((tag) => (
                    <SelectItem key={tag} value={tag}>
                      {tag}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          <div className="border-b border-border bg-background/70">
            <NoteFolderTree
              folders={folders}
              selectedFolderId={selectedFolderId}
              onSelectFolder={handleSelectFolder}
              onCreateFolder={handleCreateFolder}
            />
          </div>

          <div className="flex-1 overflow-y-auto">
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
                <p className="text-[10px] mt-1">先选择文件夹，再创建您的第一篇笔记</p>
              </div>
            )}

            {!notesLoading && derivedSummaries.length > 0 && (
              <div className="border-b border-border/50 bg-amber-50/40">
                <div className="px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-amber-800">
                  系统摘要
                </div>
                {derivedSummaries.map((summary) => (
                  <button
                    key={summary.paperId}
                    type="button"
                    className={clsx(
                      'w-full px-3 py-3 text-left transition-colors hover:bg-amber-100/60',
                      selectedSummaryPaperId === summary.paperId && 'bg-amber-100 border-l-2 border-l-amber-500',
                    )}
                    onClick={() => handleSelectSummary(summary)}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-amber-950 line-clamp-1">{summary.title}</p>
                        <p className="mt-1 text-[11px] text-amber-900/80 line-clamp-2">
                          {highlightText(extractPreview(summary.readingNotes) || '系统摘要', searchQuery)}
                        </p>
                      </div>
                      <Badge variant="secondary" className="h-4 shrink-0 px-1 text-[9px]">
                        摘要
                      </Badge>
                    </div>
                  </button>
                ))}
              </div>
            )}

            {!notesLoading && filteredNotes.length > 0 && (
              <div className="divide-y divide-border/50">
                {filteredNotes.map((note) => {
                  const displayTags = getDisplayTags(note.tags);
                  const primaryPaperId = note.paperIds[0] || getPaperIdTag(note.tags);
                  const paperLabel =
                    (primaryPaperId && paperTitleMap.get(primaryPaperId)) ||
                    getPaperTitleTag(note.tags);

                  return (
                    <div
                      key={note.id}
                      className={clsx(
                        'group p-3 cursor-pointer transition-colors hover:bg-muted/50',
                        selectedNoteId === note.id && 'bg-muted/80 border-l-2 border-l-accent',
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
                        {highlightText(extractPreview(note.content) || '空笔记', searchQuery)}
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
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 flex flex-col bg-[#fdfaf6] max-w-7xl mx-auto px-6">
          {selectedNote ? (
            <>
              <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-white">
                <div>
                  <h3 className="font-medium text-sm">{selectedNote.title || '未命名笔记'}</h3>
                  <div className="flex items-center gap-2 mt-0.5">
                    {selectedNote.paperIds.length > 0 && (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <FileText className="w-3 h-3" />
                        <span>关联 {selectedNote.paperIds.length} 篇论文</span>
                      </div>
                    )}
                  </div>
                </div>
                <SaveIndicator />
              </div>

              <div className="flex-1 p-4 overflow-auto">
                <NotesEditor
                  content={editorContent}
                  onChange={handleEditorChange}
                  placeholder="开始写笔记... 使用 [[pdf:paperId:page:5]] 引用论文"
                />
              </div>
            </>
          ) : selectedSummary ? (
            <>
              <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-white">
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

              <div className="flex-1 overflow-auto px-6 py-5">
                <div className="mx-auto max-w-3xl rounded-2xl border border-amber-200 bg-white/90 p-6 shadow-sm">
                  <p className="mb-4 text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">
                    系统摘要只读视图
                  </p>
                  <div className="whitespace-pre-wrap text-sm leading-7 text-zinc-800">
                    {selectedSummary.readingNotes}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
              <FileText className="w-16 h-16 mb-4 opacity-30" />
              <h3 className="text-lg font-semibold mb-1">选择或创建一个笔记开始编辑</h3>
              <p className="text-sm mb-4">请先在左侧选择文件夹、系统摘要，或点击「新建」创建笔记</p>
              <Button variant="outline" onClick={handleCreateNote}>
                <Plus className="w-4 h-4 mr-1" />
                新建笔记
              </Button>
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
