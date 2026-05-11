import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { toast } from 'sonner';

import type { EvidenceBlockDto } from '@scholar-ai/types';

import * as annotationsApi from '@/services/annotationsApi';
import type { Annotation } from '@/services/annotationsApi';
import * as notesApi from '@/services/notesApi';
import * as papersApi from '@/services/papersApi';
import { useLanguage } from '@/app/contexts/LanguageContext';
import { useEvidenceNavigation } from '@/features/chat/hooks/useEvidenceNavigation';
import { normalizeEditorDocument } from '@/features/notes/content';
import {
  buildReadingNoteTitle,
  createEmptyEditorDocument,
  getPrimaryReadingNoteForPaper,
  READ_WORKSPACE_NOTE_TAG,
} from '@/features/notes/ownership';
import { useChunkHighlight } from '@/features/read/hooks/useChunkHighlight';
import { useSourceNavigation } from '@/features/read/hooks/useSourceNavigation';
import { useReadPreferencesStore } from '@/features/read/state/readPreferencesStore';
import { getEvidenceSource } from '@/services/evidenceApi';

type SelectionPosition = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export function useReadWorkspaceScreen() {
  const MIN_PANEL_WIDTH = 320;
  const MAX_PANEL_WIDTH = 620;

  const { id } = useParams<{ id?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const sourceNav = useSourceNavigation();
  const chunkHighlight = useChunkHighlight(sourceNav.sourceId);
  const { saveEvidence } = useEvidenceNavigation(isZh);

  const [paper, setPaper] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState<number | null>(null);
  const [scale, setScale] = useState(1.0);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [selectedText, setSelectedText] = useState('');
  const [selectionPosition, setSelectionPosition] = useState<SelectionPosition | null>(null);
  const [activeAnnotationId, setActiveAnnotationId] = useState<string | null>(null);
  const [activeEvidence, setActiveEvidence] = useState<EvidenceBlockDto | null>(null);
  const [activeEvidencePreview, setActiveEvidencePreview] = useState('');
  const [linkedNoteId, setLinkedNoteId] = useState<string | null>(null);
  const [linkedNoteTitle, setLinkedNoteTitle] = useState('');
  const [linkedNoteContent, setLinkedNoteContent] = useState<any>(createEmptyEditorDocument());
  const [noteSaveStatus, setNoteSaveStatus] = useState<'idle' | 'pending' | 'saving' | 'saved' | 'error'>('idle');
  const [noteLastSaved, setNoteLastSaved] = useState<Date | null>(null);
  const [pageInputValue, setPageInputValue] = useState('1');
  const [isDesktopViewport, setIsDesktopViewport] = useState(() => {
    if (typeof window === 'undefined') {
      return true;
    }
    return window.matchMedia('(min-width: 1024px)').matches;
  });
  const {
    rightTab,
    isPanelOpen,
    isFullscreen,
    panelWidth,
    setRightTab,
    setIsPanelOpen,
    setIsFullscreen,
    setPanelWidth,
  } = useReadPreferencesStore();

  const clampPage = useCallback(
    (page: number) => {
      const upper = totalPages || Number.MAX_SAFE_INTEGER;
      return Math.max(1, Math.min(page, upper));
    },
    [totalPages],
  );

  const initializeLinkedNote = useCallback(
    async (paperId: string, paperTitle: string) => {
      const noteTitle = buildReadingNoteTitle(paperTitle, isZh);
      const existingNotes = await notesApi.getNotesByPaper(paperId);
      const userNote = getPrimaryReadingNoteForPaper(existingNotes, paperId);

      if (!userNote) {
        setLinkedNoteId(null);
        setLinkedNoteTitle(noteTitle);
        setLinkedNoteContent(createEmptyEditorDocument());
        return;
      }

      setLinkedNoteId(userNote.id);
      setLinkedNoteTitle(userNote.title || noteTitle);
      setLinkedNoteContent(normalizeEditorDocument(userNote.contentDoc || userNote.content));
    },
    [isZh],
  );

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const mediaQuery = window.matchMedia('(min-width: 1024px)');
    const syncViewport = () => setIsDesktopViewport(mediaQuery.matches);
    syncViewport();

    mediaQuery.addEventListener('change', syncViewport);
    return () => mediaQuery.removeEventListener('change', syncViewport);
  }, []);

  useEffect(() => {
    const clampedWidth = Math.min(MAX_PANEL_WIDTH, Math.max(MIN_PANEL_WIDTH, panelWidth));
    if (clampedWidth !== panelWidth) {
      setPanelWidth(clampedWidth);
    }
  }, [panelWidth, setPanelWidth]);

  useEffect(() => {
    const targetPage = searchParams.get('page');
    if (targetPage) {
      const page = parseInt(targetPage, 10);
      if (!isNaN(page) && page >= 1) {
        setCurrentPage(clampPage(page));
      }
    }
  }, [clampPage, searchParams]);

  useEffect(() => {
    setPageInputValue(String(currentPage));
  }, [currentPage]);

  useEffect(() => {
    const panel = searchParams.get('panel');
    if (panel === 'notes' || panel === 'summary' || panel === 'annotations') {
      setRightTab(panel);
      return;
    }

    const source = searchParams.get('source');
    if (source === 'chat') {
      setRightTab('annotations');
    } else if (source === 'search') {
      setRightTab('summary');
    }
  }, [searchParams, setRightTab]);

  useEffect(() => {
    let cancelled = false;

    if (!sourceNav.sourceId) {
      setActiveEvidence(null);
      setActiveEvidencePreview('');
      return;
    }

    void getEvidenceSource(sourceNav.sourceId)
      .then((payload) => {
        if (cancelled) {
          return;
        }
        setActiveEvidence({
          evidence_id: payload.evidence_id,
          source_type: payload.source_type,
          paper_id: payload.paper_id || id || '',
          source_chunk_id: payload.source_chunk_id,
          page_num: payload.page_num || sourceNav.page || currentPage,
          section_path: payload.section_path || null,
          content_type: payload.content_type || 'text',
          text: payload.content || payload.anchor_text || '',
          quote_text: payload.content || payload.anchor_text || '',
          citation_jump_url: payload.citation_jump_url,
        });
        setActiveEvidencePreview(payload.anchor_text || payload.content || '');
      })
      .catch(() => {
        if (!cancelled) {
          setActiveEvidence(null);
          setActiveEvidencePreview('');
        }
      });

    return () => {
      cancelled = true;
    };
  }, [currentPage, id, sourceNav.page, sourceNav.sourceId]);

  useEffect(() => {
    async function loadPaper() {
      if (!id) {
        setPaper(null);
        setError(null);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const data = await papersApi.get(id);
        setPaper(data);

        const annotationData = await annotationsApi.list(id);
        setAnnotations(annotationData);

        await initializeLinkedNote(id, data.title || '');
      } catch (loadError: any) {
        const errorMsg =
          loadError?.message || (isZh ? '加载论文失败' : 'Failed to load paper');
        setError(errorMsg);
        toast.error(errorMsg);
      } finally {
        setLoading(false);
      }
    }

    void loadPaper();
  }, [id, initializeLinkedNote, isZh]);

  const goToPage = useCallback(
    async (page: number, _reason: 'toolbar' | 'thumbnail' | 'section' | 'citation' | 'annotation' | 'url' = 'toolbar') => {
      const nextPage = clampPage(page);
      setCurrentPage(nextPage);
      setPageInputValue(String(nextPage));

      const nextParams = new URLSearchParams(searchParams);
      nextParams.set('page', String(nextPage));
      nextParams.set('source', nextParams.get('source') || 'read');
      setSearchParams(nextParams, { replace: true });

      if (!id) {
        return;
      }
      try {
        await papersApi.saveReadingProgress(id, nextPage);
      } catch {
        toast.warning(
          isZh ? '阅读进度保存失败' : 'Failed to save reading progress',
        );
      }
    },
    [clampPage, id, isZh, searchParams, setSearchParams],
  );

  const handleAnnotationCreated = useCallback(async () => {
    if (!id) {
      return;
    }
    const annotationData = await annotationsApi.list(id);
    setAnnotations(annotationData);
    setSelectedText('');
    setSelectionPosition(null);
  }, [id]);

  const handleNumPagesChange = useCallback((numPages: number) => {
    setTotalPages(numPages);
    setCurrentPage((previous) => Math.min(previous, numPages));
  }, []);

  const handleNotesSave = useCallback(
    async (content: any) => {
      if (!id) {
        return;
      }
      try {
        setNoteSaveStatus('saving');
        const contentJson = JSON.stringify(content || createEmptyEditorDocument());
        const existingText = contentJson.replace(/[\s"{}\[\],:]/g, '');
        if (!existingText) {
          setNoteSaveStatus('idle');
          return;
        }

        if (!linkedNoteId) {
          const created = await notesApi.createNote({
            title: linkedNoteTitle || buildReadingNoteTitle(paper?.title, isZh),
            contentDoc: normalizeEditorDocument(content),
            sourceType: 'read',
            tags: [READ_WORKSPACE_NOTE_TAG],
            paperIds: [id],
          });
          setLinkedNoteId(created.id);
          setLinkedNoteTitle(created.title || linkedNoteTitle);
        } else {
          await notesApi.updateNote(linkedNoteId, {
            title:
              linkedNoteTitle ||
              buildReadingNoteTitle(paper?.title, isZh),
            contentDoc: normalizeEditorDocument(content),
            sourceType: 'read',
            tags: [READ_WORKSPACE_NOTE_TAG],
            paperIds: [id],
          });
        }
        setNoteSaveStatus('saved');
        setNoteLastSaved(new Date());
      } catch {
        setNoteSaveStatus('error');
        toast.error(isZh ? '笔记保存失败' : 'Failed to save notes');
      }
    },
    [id, isZh, linkedNoteId, linkedNoteTitle, paper?.title],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void handleNotesSave(linkedNoteContent);
    }, 800);

    return () => {
      window.clearTimeout(timer);
    };
  }, [handleNotesSave, linkedNoteContent]);

  useEffect(() => {
    if (noteSaveStatus !== 'saved') {
      return;
    }
    const timer = window.setTimeout(() => setNoteSaveStatus('idle'), 1500);
    return () => window.clearTimeout(timer);
  }, [noteSaveStatus]);

  useEffect(() => {
    setNoteSaveStatus('pending');
  }, [linkedNoteContent]);

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      void document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      void document.exitFullscreen();
      setIsFullscreen(false);
    }
  }, [setIsFullscreen]);

  useEffect(() => {
    const onFullscreenChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    onFullscreenChange();
    document.addEventListener('fullscreenchange', onFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', onFullscreenChange);
    };
  }, [setIsFullscreen]);

  return {
    id,
    navigate,
    isZh,
    sourceNav,
    chunkHighlight,
    saveEvidence,
    paper,
    loading,
    error,
    currentPage,
    totalPages,
    scale,
    annotations,
    selectedText,
    selectionPosition,
    activeAnnotationId,
    activeEvidence,
    activeEvidencePreview,
    linkedNoteId,
    linkedNoteTitle,
    linkedNoteContent,
    noteSaveStatus,
    noteLastSaved,
    pageInputValue,
    isDesktopViewport,
    rightTab,
    isPanelOpen,
    isFullscreen,
    clampPage,
    setScale,
    setSelectedText,
    setSelectionPosition,
    setLinkedNoteContent,
    setPageInputValue,
    setRightTab,
    setIsPanelOpen,
    goToPage,
    handleAnnotationCreated,
    handleNumPagesChange,
    toggleFullscreen,
  };
}
