import { useMemo } from 'react';

import type { Note } from '@/services/notesApi';
import {
  extractEditorPlainText,
} from '@/features/notes/content';
import {
  buildNoteDisplayTitle,
  getDisplayTags,
  getFolderIdFromTags,
  getPaperIdTag,
  getPaperTitleTag,
  humanizeNotePreview,
  humanizeSummaryPreview,
} from '@/features/notes/notePresentation';
import {
  filterUserEditableNotes,
  isEvidenceCaptureNote,
  type ReadingSummaryProjection,
} from '@/features/notes/ownership';

import { UNARCHIVED_FOLDER_ID, type PaperCatalogItem } from './useNotesCatalog';

export interface NotesDisplayItem {
  note: Note;
  displayTitle: string;
  preview: string;
  paperLabel: string | null;
  displayTag: string | null;
  updatedAtLabel: string;
}

export interface NotesSummaryDisplayItem {
  summary: ReadingSummaryProjection;
  title: string;
  preview: string;
}

export interface UseNotesFilterParams {
  notes: Note[];
  paperIdFilter: string | null;
  selectedFolderId: string | null;
  tagFilter: string;
  searchQuery: string;
  derivedSummaries: ReadingSummaryProjection[];
  paperTitleMap: Map<string, string>;
}

export interface UseNotesFilterReturn {
  userNotes: Note[];
  filteredNotes: Note[];
  archivedNotes: Note[];
  unarchivedNotes: Note[];
  allTags: string[];
  filteredSummaries: ReadingSummaryProjection[];
  notePreviewText: (note: Note) => string;
  summaryItems: NotesSummaryDisplayItem[];
  archivedNoteItems: NotesDisplayItem[];
  unarchivedNoteItems: NotesDisplayItem[];
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

export function useNotesFilter({
  notes,
  paperIdFilter,
  selectedFolderId,
  tagFilter,
  searchQuery,
  derivedSummaries,
  paperTitleMap,
}: UseNotesFilterParams): UseNotesFilterReturn {
  const userNotes = useMemo(() => filterUserEditableNotes(notes), [notes]);

  const notePreviewText = (note: Note): string => {
    const preview = humanizeNotePreview(extractEditorPlainText(note.contentDoc || note.content, 80));
    if (preview !== '暂无正文') return preview;
    if (isEvidenceCaptureNote(note)) {
      const evidenceText = note.linkedEvidence
        ?.map((item) => humanizeNotePreview(String(item?.text || '')))
        .find((text) => text && text !== '暂无正文');
      if (evidenceText) return evidenceText;
    }
    return preview;
  };

  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    userNotes.forEach((note) => getDisplayTags(note.tags).forEach((tag) => tagSet.add(tag)));
    return Array.from(tagSet).sort();
  }, [userNotes]);

  // Filter summaries by folder and search
  const filteredSummaries = useMemo(() => {
    let summaries = derivedSummaries;

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
  }, [derivedSummaries, searchQuery, selectedFolderId]);

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

  const summaryItems = useMemo<NotesSummaryDisplayItem[]>(
    () => filteredSummaries.map((summary) => ({
      summary,
      title: summary.title,
      preview: humanizeSummaryPreview(summary.readingNotes),
    })),
    [filteredSummaries],
  );

  const archivedNoteItems = useMemo<NotesDisplayItem[]>(
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

  const unarchivedNoteItems = useMemo<NotesDisplayItem[]>(
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

  return {
    userNotes,
    filteredNotes,
    archivedNotes,
    unarchivedNotes,
    allTags,
    filteredSummaries,
    notePreviewText,
    summaryItems,
    archivedNoteItems,
    unarchivedNoteItems,
  };
}
