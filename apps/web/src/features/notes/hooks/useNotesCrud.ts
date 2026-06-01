import { useCallback } from 'react';
import { useSearchParams } from 'react-router';
import { toast } from 'sonner';

import { useCreateNote, useDeleteNote, useUpdateNote } from '@/hooks/useNotes';
import type { Note } from '@/services/notesApi';
import {
  normalizeEditorDocument,
} from '@/features/notes/content';
import {
  createEmptyEditorDocument,
  type ReadingSummaryProjection,
} from '@/features/notes/ownership';
import {
  PAPER_TAG_PREFIX,
  getFolderIdFromTags,
  upsertFolderTag,
} from '@/features/notes/notePresentation';

export interface UseNotesCrudReturn {
  createNote: ReturnType<typeof useCreateNote>;
  updateNote: ReturnType<typeof useUpdateNote>;
  deleteNote: ReturnType<typeof useDeleteNote>;
  handleSave: (note: Note, content: any, selectedFolderId: string | null) => Promise<void>;
  handleCreateNote: (
    selectedFolderId: string | null,
    paperIdFilter: string | null,
    paperTitleMap: Map<string, string>,
    onSelectNote: (note: Note) => void,
    onSetEditorContent: (content: any) => void,
  ) => Promise<void>;
  handleDeleteNote: (
    deleteNoteId: string,
    selectedNoteId: string | null,
    filteredNotes: Note[],
    onSelectNote: (note: Note) => void,
    onClearSelection: () => void,
  ) => Promise<void>;
  handleEditorChange: (
    json: any,
    selectedNote: Note | null,
    onSetEditorContent: (content: any) => void,
  ) => void;
  handleSummaryToNote: (
    summary: ReadingSummaryProjection,
    selectedFolderId: string | null,
    onSelectNote: (note: Note) => void,
  ) => Promise<void>;
  handleSummaryAppendToCurrent: (
    summary: ReadingSummaryProjection,
    selectedNoteId: string | null,
    editorContent: any,
    onSetEditorContent: (content: any) => void,
  ) => void;
}

export function useNotesCrud(): UseNotesCrudReturn {
  const [searchParams, setSearchParams] = useSearchParams();
  const createNote = useCreateNote();
  const updateNote = useUpdateNote();
  const deleteNote = useDeleteNote();

  const handleSave = useCallback(async (note: Note, content: any, selectedFolderId: string | null) => {
    const folderId = getFolderIdFromTags(note.tags) || selectedFolderId;
    const nextTags = folderId ? upsertFolderTag(note.tags, folderId) : note.tags;

    await updateNote.mutateAsync({
      id: note.id,
      payload: {
        contentDoc: normalizeEditorDocument(content),
        title: note.title || '未命名笔记',
        tags: nextTags,
        paperIds: note.paperIds,
      },
    });
  }, [updateNote]);

  const handleCreateNote = useCallback(async (
    selectedFolderId: string | null,
    paperIdFilter: string | null,
    paperTitleMap: Map<string, string>,
    onSelectNote: (note: Note) => void,
    onSetEditorContent: (content: any) => void,
  ) => {
    if (!selectedFolderId) {
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
      onSelectNote(newNote);
      onSetEditorContent(createEmptyEditorDocument());

      const nextParams = new URLSearchParams(searchParams);
      nextParams.set('noteId', newNote.id);
      setSearchParams(nextParams, { replace: true });
    } catch {
      toast.error('创建笔记失败');
    }
  }, [createNote, searchParams, setSearchParams]);

  const handleDeleteNote = useCallback(async (
    deleteNoteId: string,
    selectedNoteId: string | null,
    filteredNotes: Note[],
    onSelectNote: (note: Note) => void,
    onClearSelection: () => void,
  ) => {
    try {
      await deleteNote.mutateAsync(deleteNoteId);
      toast.success('删除成功');
      if (selectedNoteId === deleteNoteId) {
        const remaining = filteredNotes.filter((note) => note.id !== deleteNoteId);
        const nextNote = remaining[0];
        if (nextNote) {
          onSelectNote(nextNote);
        } else {
          onClearSelection();
        }
      }
    } catch {
      toast.error('删除失败');
    }
  }, [deleteNote]);

  const handleEditorChange = useCallback((
    json: any,
    selectedNote: Note | null,
    onSetEditorContent: (content: any) => void,
  ) => {
    onSetEditorContent(json);

    if (!selectedNote || selectedNote.title !== '未命名笔记') return;

    const textParts: string[] = [];
    const walk = (nodes: any[]) => {
      nodes.forEach((node) => {
        if (node?.text) textParts.push(node.text);
        if (Array.isArray(node?.content)) walk(node.content);
      });
    };

    if (Array.isArray(json?.content)) walk(json.content);

    const firstLine = textParts.join(' ').trim().split('\n')[0]?.trim();
    if (!firstLine) return;

    const generatedTitle = firstLine.slice(0, 48) || '未命名笔记';
    if (generatedTitle === selectedNote.title) return;

    void updateNote.mutateAsync({
      id: selectedNote.id,
      payload: { title: generatedTitle },
    });
  }, [updateNote]);

  const handleSummaryToNote = useCallback(async (
    summary: ReadingSummaryProjection,
    selectedFolderId: string | null,
    onSelectNote: (note: Note) => void,
  ) => {
    const targetFolderId = selectedFolderId;
    if (!targetFolderId) {
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
      onSelectNote(newNote);
      toast.success('已转为用户笔记');
    } catch {
      toast.error('转换失败');
    }
  }, [createNote]);

  const handleSummaryAppendToCurrent = useCallback((
    summary: ReadingSummaryProjection,
    selectedNoteId: string | null,
    editorContent: any,
    onSetEditorContent: (content: any) => void,
  ) => {
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
    onSetEditorContent(next);
    toast.success('摘要内容已加入当前笔记');
  }, []);

  return {
    createNote,
    updateNote,
    deleteNote,
    handleSave,
    handleCreateNote,
    handleDeleteNote,
    handleEditorChange,
    handleSummaryToNote,
    handleSummaryAppendToCurrent,
  };
}
