import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

import type { NoteFolder } from '@/app/components/NoteFolderTree';
import { kbApi } from '@/services/kbApi';
import * as papersApi from '@/services/papersApi';
import {
  buildPaperDisplayTitle,
  buildSummaryDisplayTitle,
  getFolderIdFromTags,
} from '@/features/notes/notePresentation';
import type { Note } from '@/services/notesApi';
import {
  filterUserEditableNotes,
  type ReadingSummaryProjection,
} from '@/features/notes/ownership';

const MANUAL_FOLDERS_STORAGE_KEY = 'notes-manual-folders-v1';
export const UNARCHIVED_FOLDER_ID = '__unarchived__';

type FolderSource = 'kb' | 'manual';

export interface NotesFolder extends NoteFolder {
  source: FolderSource;
}

export interface PaperCatalogItem {
  id: string;
  title: string;
  readingNotes: string | null;
  folderId: string | null;
}

export interface UseNotesCatalogParams {
  notes: Note[];
  paperIdFilter: string | null;
}

export interface UseNotesCatalogReturn {
  kbFolders: NotesFolder[];
  manualFolders: NotesFolder[];
  folders: NotesFolder[];
  paperCatalog: PaperCatalogItem[];
  paperTitleMap: Map<string, string>;
  catalogLoading: boolean;
  derivedSummaries: ReadingSummaryProjection[];
  setManualFolders: React.Dispatch<React.SetStateAction<NotesFolder[]>>;
  setKbFolders: React.Dispatch<React.SetStateAction<NotesFolder[]>>;
  setPaperCatalog: React.Dispatch<React.SetStateAction<PaperCatalogItem[]>>;
  setPaperTitleMap: React.Dispatch<React.SetStateAction<Map<string, string>>>;
}

export function useNotesCatalog({ notes, paperIdFilter }: UseNotesCatalogParams): UseNotesCatalogReturn {
  const userNotes = useMemo(() => filterUserEditableNotes(notes), [notes]);

  const [kbFolders, setKbFolders] = useState<NotesFolder[]>([]);
  const [manualFolders, setManualFolders] = useState<NotesFolder[]>([]);
  const [paperCatalog, setPaperCatalog] = useState<PaperCatalogItem[]>([]);
  const [paperTitleMap, setPaperTitleMap] = useState<Map<string, string>>(new Map());
  const [hydratedPaperIds, setHydratedPaperIds] = useState<Set<string>>(new Set());
  const [catalogLoading, setCatalogLoading] = useState(false);

  // Load manual folders from localStorage
  useEffect(() => {
    try {
      const raw = localStorage.getItem(MANUAL_FOLDERS_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as NotesFolder[];
      if (!Array.isArray(parsed)) return;
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

  // Persist manual folders to localStorage
  useEffect(() => {
    localStorage.setItem(MANUAL_FOLDERS_STORAGE_KEY, JSON.stringify(manualFolders));
  }, [manualFolders]);

  // Load paper catalog and KB folders
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

  // Hydrate missing paper metadata from URL filter
  useEffect(() => {
    if (!paperIdFilter) return;
    const targetPaperId = paperIdFilter;

    if (paperTitleMap.has(targetPaperId) || hydratedPaperIds.has(targetPaperId)) return;

    let cancelled = false;

    async function hydrateMissingPaperMetadata() {
      try {
        const paper = await papersApi.get(targetPaperId);
        if (cancelled) return;

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

  // Derive summaries from paper catalog
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

    return summaries;
  }, [paperCatalog, paperIdFilter]);

  // Compute folder counts and merged folder list
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
        source: 'manual' as FolderSource,
      },
      ...mapped,
    ];
  }, [folderCounts, kbFolders, manualFolders, userNotes]);

  return {
    kbFolders,
    manualFolders,
    folders,
    paperCatalog,
    paperTitleMap,
    catalogLoading,
    derivedSummaries,
    setManualFolders,
    setKbFolders,
    setPaperCatalog,
    setPaperTitleMap,
  };
}
