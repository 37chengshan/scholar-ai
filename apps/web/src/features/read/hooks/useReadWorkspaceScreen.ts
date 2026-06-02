/**
 * useReadWorkspaceScreen Hook (Orchestrator)
 *
 * Composes focused sub-hooks for the Read workspace screen.
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';

import type { EvidenceBlockDto } from '@scholar-ai/types';

import { useLanguage } from '@/app/contexts/LanguageContext';
import { useEvidenceNavigation } from '@/features/chat/hooks/useEvidenceNavigation';
import { useChunkHighlight } from '@/features/read/hooks/useChunkHighlight';
import { useSourceNavigation } from '@/features/read/hooks/useSourceNavigation';
import { useReadPreferencesStore } from '@/features/read/state/readPreferencesStore';
import { getEvidenceSource } from '@/services/evidenceApi';

import { usePaperLoader } from './usePaperLoader';
import { useAnnotationManager } from './useAnnotationManager';
import { useLinkedNote } from './useLinkedNote';
import { usePageNavigation } from './usePageNavigation';

export function useReadWorkspaceScreen() {
  const MIN_PANEL_WIDTH = 320;
  const MAX_PANEL_WIDTH = 620;

  const { id } = useParams<{ id?: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const sourceNav = useSourceNavigation();
  const chunkHighlight = useChunkHighlight(sourceNav.sourceId);
  const { saveEvidence } = useEvidenceNavigation(isZh);

  // Sub-hooks
  const paperLoader = usePaperLoader(id, isZh);
  const annotationMgr = useAnnotationManager(id);
  const pageNav = usePageNavigation(id, isZh);
  const linkedNote = useLinkedNote(
    id,
    paperLoader.paper?.title,
    isZh,
    paperLoader.linkedNoteId,
    paperLoader.setLinkedNoteId,
    paperLoader.linkedNoteTitle,
    paperLoader.setLinkedNoteTitle,
  );

  // Evidence state
  const [activeEvidence, setActiveEvidence] = useState<EvidenceBlockDto | null>(null);
  const [activeEvidencePreview, setActiveEvidencePreview] = useState('');

  // Viewport detection
  const [isDesktopViewport, setIsDesktopViewport] = useState(() => {
    if (typeof window === 'undefined') return true;
    return window.matchMedia('(min-width: 1024px)').matches;
  });

  const {
    rightTab, isPanelOpen, isFullscreen, panelWidth,
    setRightTab, setIsPanelOpen, setIsFullscreen, setPanelWidth,
  } = useReadPreferencesStore();

  // Viewport listener
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const mediaQuery = window.matchMedia('(min-width: 1024px)');
    const syncViewport = () => setIsDesktopViewport(mediaQuery.matches);
    syncViewport();
    mediaQuery.addEventListener('change', syncViewport);
    return () => mediaQuery.removeEventListener('change', syncViewport);
  }, []);

  // Panel width clamping
  useEffect(() => {
    const clampedWidth = Math.min(MAX_PANEL_WIDTH, Math.max(MIN_PANEL_WIDTH, panelWidth));
    if (clampedWidth !== panelWidth) setPanelWidth(clampedWidth);
  }, [panelWidth, setPanelWidth]);

  // Panel tab from URL
  useEffect(() => {
    const panel = searchParams.get('panel');
    if (panel === 'notes' || panel === 'summary' || panel === 'annotations') {
      setRightTab(panel);
      return;
    }
    const source = searchParams.get('source');
    if (source === 'chat') setRightTab('annotations');
    else if (source === 'search') setRightTab('summary');
  }, [searchParams, setRightTab]);

  // Evidence loading
  useEffect(() => {
    let cancelled = false;
    if (!sourceNav.sourceId) {
      setActiveEvidence(null);
      setActiveEvidencePreview('');
      return;
    }
    void getEvidenceSource(sourceNav.sourceId)
      .then((payload) => {
        if (cancelled) return;
        setActiveEvidence({
          evidence_id: payload.evidence_id,
          source_type: payload.source_type,
          paper_id: payload.paper_id || id || '',
          source_chunk_id: payload.source_chunk_id,
          page_num: payload.page_num || sourceNav.page || pageNav.currentPage,
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
    return () => { cancelled = true; };
  }, [pageNav.currentPage, id, sourceNav.page, sourceNav.sourceId]);

  // Fullscreen
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
    return () => document.removeEventListener('fullscreenchange', onFullscreenChange);
  }, [setIsFullscreen]);

  // Annotation refresh also clears selection
  const handleAnnotationCreated = useCallback(async () => {
    await paperLoader.refreshAnnotations();
    annotationMgr.setSelectedText('');
    annotationMgr.setSelectionPosition(null);
  }, [paperLoader, annotationMgr]);

  return {
    id,
    navigate,
    isZh,
    sourceNav,
    chunkHighlight,
    saveEvidence,
    paper: paperLoader.paper,
    loading: paperLoader.loading,
    error: paperLoader.error,
    currentPage: pageNav.currentPage,
    totalPages: pageNav.totalPages,
    scale: pageNav.scale,
    annotations: annotationMgr.annotations,
    selectedText: annotationMgr.selectedText,
    selectionPosition: annotationMgr.selectionPosition,
    activeAnnotationId: annotationMgr.activeAnnotationId,
    activeEvidence,
    activeEvidencePreview,
    linkedNoteId: paperLoader.linkedNoteId,
    linkedNoteTitle: paperLoader.linkedNoteTitle,
    linkedNoteContent: linkedNote.linkedNoteContent,
    noteSaveStatus: linkedNote.noteSaveStatus,
    noteLastSaved: linkedNote.noteLastSaved,
    pageInputValue: pageNav.pageInputValue,
    isDesktopViewport,
    rightTab,
    isPanelOpen,
    isFullscreen,
    clampPage: pageNav.clampPage,
    setScale: pageNav.setScale,
    setSelectedText: annotationMgr.setSelectedText,
    setSelectionPosition: annotationMgr.setSelectionPosition,
    setLinkedNoteContent: linkedNote.setLinkedNoteContent,
    setPageInputValue: pageNav.setPageInputValue,
    setRightTab,
    setIsPanelOpen,
    goToPage: pageNav.goToPage,
    handleAnnotationCreated,
    handleNumPagesChange: pageNav.handleNumPagesChange,
    toggleFullscreen,
  };
}
