/**
 * Notes Page — Independent Top-Level Page
 *
 * Features:
 * - Two-panel layout: note list sidebar (w-64) + Tiptap editor
 * - Auto-save with 1s debounce via useAutoSave hook
 * - Save status indicator (已保存/保存中.../保存失败)
 * - PDF reference syntax rendering as clickable chips
 * - Sonner toast notifications
 * - IndexedDB fallback for offline editing
 *
 * Requirements: D-10, D-11, D-12, D-13, NOTE-01, NOTE-02, NOTE-03
 */

import { useState, useCallback, useMemo } from 'react';
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
} from 'lucide-react';
import { toast } from 'sonner';
import { clsx } from 'clsx';

/**
 * Extract plain text preview from Tiptap JSON content
 */
function extractPreview(content: any, maxLength = 80): string {
  if (!content || !content.content) return '';
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
  walk(content.content);
  const full = texts.join(' ').trim();
  // Strip PDF reference patterns from preview
  const cleaned = full.replace(/\[\[pdf:[^:]+:page:\d+\]\]/g, '');
  return cleaned.length > maxLength ? cleaned.slice(0, maxLength) + '...' : cleaned;
}

/**
 * Highlight matching text in a string
 */
function highlightText(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;
  const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  const parts = text.split(regex);
  return parts.map((part, i) =>
    regex.test(part) ? (
      <mark key={i} className="bg-yellow-200 text-inherit rounded px-0.5">{part}</mark>
    ) : (
      part
    )
  );
}

export function Notes() {
  const { notes, loading: notesLoading } = useNotes();
  const createNote = useCreateNote();
  const updateNote = useUpdateNote();
  const deleteNote = useDeleteNote();

  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [tagFilter, setTagFilter] = useState<string>('all');
  const [deleteNoteId, setDeleteNoteId] = useState<string | null>(null);
  const [editorContent, setEditorContent] = useState<any>(null);
  const [folders, setFolders] = useState<NoteFolder[]>([]);
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [noteFolderMap] = useState<Record<string, string>>({});

  const selectedNote = useMemo(
    () => notes.find((n) => n.id === selectedNoteId) || null,
    [notes, selectedNoteId]
  );

  // Collect all unique tags from notes
  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    notes.forEach((note) => note.tags?.forEach((tag) => tagSet.add(tag)));
    return Array.from(tagSet).sort();
  }, [notes]);

  // Filter notes by search, tag, and folder
  const filteredNotes = useMemo(() => {
    let result = notes;

    // Folder filter
    if (selectedFolderId !== null) {
      result = result.filter((note) => noteFolderMap[note.id] === selectedFolderId);
    }

    // Tag filter
    if (tagFilter !== 'all') {
      result = result.filter((note) => note.tags?.includes(tagFilter));
    }

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (note) =>
          note.title.toLowerCase().includes(query) ||
          extractPreview(note.content).toLowerCase().includes(query)
      );
    }

    return result;
  }, [notes, searchQuery, tagFilter, selectedFolderId, noteFolderMap]);

  // Auto-save handler
  const handleSave = useCallback(
    async (content: any) => {
      if (!selectedNoteId) return;
      const note = notes.find((n) => n.id === selectedNoteId);
      if (!note) return;

      await updateNote.mutateAsync({
        id: selectedNoteId,
        payload: { content: JSON.stringify(content), title: note.title || '未命名笔记' },
      });
    },
    [selectedNoteId, notes, updateNote]
  );

  const { status: saveStatus, lastSaved } = useAutoSave({
    content: editorContent,
    onSave: handleSave,
    debounceMs: 1000,
    noteId: selectedNoteId || undefined,
  });

  // When selection changes, load note content
  const handleSelectNote = useCallback(
    (note: Note) => {
      setSelectedNoteId(note.id);
      try {
        // Try parsing as JSON (Tiptap format)
        setEditorContent(JSON.parse(note.content));
      } catch {
        // Legacy HTML content — convert to minimal Tiptap JSON
        setEditorContent({
          type: 'doc',
          content: [{ type: 'paragraph', content: [{ type: 'text', text: note.content }] }],
        });
      }
    },
    []
  );

  // Create new note
  const handleCreateNote = useCallback(async () => {
    try {
      const newNote = await createNote.mutateAsync({
        title: '未命名笔记',
        content: '{}',
        tags: [],
        paperIds: [],
      });
      toast.success('笔记已创建');
      handleSelectNote(newNote);
      setEditorContent({ type: 'doc', content: [] });
    } catch {
      toast.error('创建笔记失败');
    }
  }, [createNote, handleSelectNote]);

  // Delete note
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

  // Folder handlers
  const handleCreateFolder = useCallback((name: string, parentId: string | null) => {
    const newFolder: NoteFolder = {
      id: `folder-${Date.now()}`,
      name,
      parentId,
      noteCount: 0,
    };
    setFolders((prev) => [...prev, newFolder]);
    toast.success(`文件夹「${name}」已创建`);
  }, []);

  // Handle editor content change (from Tiptap)
  const handleEditorChange = useCallback((json: any) => {
    setEditorContent(json);
  }, []);

  // Format date
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  // Save status indicator
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
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Left Sidebar — Note List */}
      <div className="w-64 border-r border-border bg-muted/20 flex flex-col">
        {/* Sidebar Header */}
        <div className="p-3 border-b border-border space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-sm">笔记</h2>
            <Button variant="default" size="sm" className="h-7 px-2" onClick={handleCreateNote}>
              <Plus className="w-3.5 h-3.5" />
              新建
            </Button>
          </div>
          {/* Search */}
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

          {/* Tag Filter */}
          {allTags.length > 0 && (
            <Select value={tagFilter} onValueChange={setTagFilter}>
              <SelectTrigger className="h-7 text-xs">
                <SelectValue placeholder="全部标签" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部标签</SelectItem>
                {allTags.map((tag) => (
                  <SelectItem key={tag} value={tag}>{tag}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>

        {/* Folder Tree */}
        <div className="border-b border-border">
          <NoteFolderTree
            folders={folders}
            selectedFolderId={selectedFolderId}
            onSelectFolder={setSelectedFolderId}
            onCreateFolder={handleCreateFolder}
          />
        </div>

        {/* Note List */}
        <div className="flex-1 overflow-y-auto">
          {notesLoading && (
            <div className="flex items-center justify-center py-8 text-muted-foreground text-xs">
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
              加载中...
            </div>
          )}

          {!notesLoading && filteredNotes.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <FileText className="w-10 h-10 mb-3 opacity-40" />
              <p className="text-xs font-medium">暂无笔记</p>
              <p className="text-[10px] mt-1">创建您的第一篇笔记</p>
            </div>
          )}

          {!notesLoading && filteredNotes.length > 0 && (
            <div className="divide-y divide-border/50">
              {filteredNotes.map((note) => (
                <div
                  key={note.id}
                  className={clsx(
                    'group p-3 cursor-pointer transition-colors hover:bg-muted/50',
                    selectedNoteId === note.id && 'bg-muted/80 border-l-2 border-l-accent'
                  )}
                  onClick={() => handleSelectNote(note)}
                >
                  <div className="flex items-start justify-between gap-1">
                    <h4 className="text-sm font-medium line-clamp-1 flex-1">
                      {highlightText(note.title || '未命名笔记', searchQuery)}
                    </h4>
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
                  <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                    {highlightText(extractPreview(note.content) || '空笔记', searchQuery)}
                  </p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <Clock className="w-2.5 h-2.5 text-muted-foreground/60" />
                    <span className="text-[10px] text-muted-foreground/60">
                      {formatDate(note.updatedAt)}
                    </span>
                    {note.tags.length > 0 && (
                      <Badge variant="outline" className="text-[9px] px-1 py-0 h-4">
                        {note.tags[0]}
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right Main — Editor Area */}
      <div className="flex-1 flex flex-col bg-[#fdfaf6]">
        {selectedNote ? (
          <>
            {/* Editor Header */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-white">
              <div>
                <h3 className="font-medium text-sm">{selectedNote.title || '未命名笔记'}</h3>
                {selectedNote.paperIds.length > 0 && (
                  <div className="flex items-center gap-1 mt-0.5">
                    <FileText className="w-3 h-3 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">
                      关联 {selectedNote.paperIds.length} 篇论文
                    </span>
                  </div>
                )}
              </div>
              <SaveIndicator />
            </div>

            {/* Editor */}
            <div className="flex-1 p-4 overflow-auto">
              <NotesEditor
                content={editorContent}
                onChange={handleEditorChange}
                placeholder="开始写笔记... 使用 [[pdf:paperId:page:5]] 引用论文"
              />
            </div>
          </>
        ) : (
          /* Empty State */
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
            <FileText className="w-16 h-16 mb-4 opacity-30" />
            <h3 className="text-lg font-semibold mb-1">选择或创建一个笔记开始编辑</h3>
            <p className="text-sm mb-4">在左侧选择笔记或点击「新建」创建新笔记</p>
            <Button variant="outline" onClick={handleCreateNote}>
              <Plus className="w-4 h-4 mr-1" />
              新建笔记
            </Button>
          </div>
        )}
      </div>

      {/* Delete Confirmation */}
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
