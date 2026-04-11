/**
 * Read Page — Refactored
 *
 * Paper reading interface with:
 * - URL-based page navigation (?page=N) for PDF reference jumps from notes
 * - Three-column layout: left sidebar (sections), center PDF, right panel (collapsible)
 * - Right panel tabs: 批注 (annotations), AI总结 (AI summary), 笔记 (quick notes)
 * - Top toolbar with paper title, page nav, zoom, fullscreen, panel toggle
 * - Thumbnail strip at bottom of PDF viewer for page navigation
 *
 * Requirements: PAGE-06, D-16, 30-03 (PDF reference jump support)
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router';
import { PDFViewer } from '../components/PDFViewer';
import { SectionTree } from '../components/SectionTree';
import { AnnotationToolbar } from '../components/AnnotationToolbar';
import { ThumbnailStrip } from '../components/ThumbnailStrip';
import { AISummaryPanel } from '../components/AISummaryPanel';
import { NotesEditor } from '../components/NotesEditor';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { Button } from '../components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '../components/ui/tooltip';
import * as papersApi from '@/services/papersApi';
import * as annotationsApi from '@/services/annotationsApi';
import type { Annotation } from '@/services/annotationsApi';
import apiClient from '@/utils/apiClient';
import { API_BASE_URL, API_PREFIX } from '@/config/api';
import { toast } from 'sonner';
import { useLanguage } from '../contexts/LanguageContext';
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  PanelRightClose,
  PanelRightOpen,
  FileText,
} from 'lucide-react';

export function Read() {
  const { id } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const [paper, setPaper] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState<number | null>(null);
  const [scale, setScale] = useState(1.0);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [rightTab, setRightTab] = useState('annotations');
  const [isPanelOpen, setIsPanelOpen] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Handle ?page= URL parameter for PDF reference jumps from notes
  useEffect(() => {
    const targetPage = searchParams.get('page');
    if (targetPage) {
      const page = parseInt(targetPage, 10);
      if (!isNaN(page) && page >= 1) {
        setCurrentPage(page);
        // Clear the ?page= parameter after navigating to avoid re-triggering
        const newParams = new URLSearchParams(searchParams);
        newParams.delete('page');
        setSearchParams(newParams, { replace: true });
      }
    }
  }, [searchParams, setSearchParams]);

  // Load paper data
  useEffect(() => {
    async function loadPaper() {
      if (!id) {
        const errorMsg = isZh ? '未提供论文ID' : 'No paper ID provided';
        setError(errorMsg);
        toast.error(errorMsg);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const data = await papersApi.get(id);
        setPaper(data);

        // Load annotations
        const annotationData = await annotationsApi.list(id);
        setAnnotations(annotationData);
      } catch (error: any) {
        const errorMsg = error?.message || (isZh ? '加载论文失败' : 'Failed to load paper');
        console.error('Failed to load paper:', error);
        setError(errorMsg);
        toast.error(errorMsg);
      } finally {
        setLoading(false);
      }
    }

    loadPaper();
  }, [id, isZh]);

  // Handle page change from PDF viewer
  const handlePageChange = useCallback(async (page: number) => {
    setCurrentPage(page);
    // Save reading progress
    try {
      await apiClient.post(`${API_PREFIX}/reading-progress/${id}`, {
        currentPage: page,
      });
    } catch (error: any) {
      // Don't block reading, just show a brief warning
      toast.warning(isZh ? '阅读进度保存失败' : 'Failed to save reading progress');
    }
  }, [id, isZh]);

  const handleAnnotationCreated = async () => {
    if (!id) return;
    const annotationData = await annotationsApi.list(id);
    setAnnotations(annotationData);
  };

  // Handle total pages change from PDF viewer
  const handleNumPagesChange = useCallback((numPages: number) => {
    setTotalPages(numPages);
  }, []);

  const handleNotesSave = async (content: string) => {
    if (!id) return;
    try {
      await papersApi.update(id, { readingNotes: content });
      toast.success(isZh ? '笔记已自动保存' : 'Note auto-saved');
    } catch (error: any) {
      toast.error(isZh ? '笔记保存失败' : 'Failed to save notes');
    }
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  if (loading || !paper) {
    return (
      <div className="flex items-center justify-center h-full">
        {error ? (
          <div className="text-center">
            <p className="text-destructive mb-4">{error}</p>
            <Button onClick={() => navigate('/library')}>
              {isZh ? '返回论文库' : 'Back to Library'}
            </Button>
          </div>
        ) : (
          isZh ? '加载中...' : 'Loading...'
        )}
      </div>
    );
  }

  const pdfUrl = `${API_BASE_URL}${API_PREFIX}/papers/${id}/pdf`;

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Top Toolbar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b bg-white shrink-0">
        <h1 className="text-sm font-semibold truncate max-w-xs" title={paper.title}>
          {paper.title || (isZh ? '未命名论文' : 'Untitled Paper')}
        </h1>

        <div className="flex-1" />

        {/* Page Navigation */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0"
            onClick={() => handlePageChange(Math.max(1, currentPage - 1))}
            disabled={currentPage <= 1}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-xs min-w-[64px] text-center tabular-nums">
            {currentPage} / {totalPages ?? (isZh ? '加载中' : '...')}
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0"
            onClick={() => handlePageChange(currentPage + 1)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center gap-1">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={() => setScale(s => Math.max(0.5, s - 0.1))}
                >
                  <ZoomOut className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>{isZh ? '缩小' : 'Zoom out'}</TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <span className="text-xs min-w-[40px] text-center">{Math.round(scale * 100)}%</span>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={() => setScale(s => Math.min(2, s + 0.1))}
                >
                  <ZoomIn className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>{isZh ? '放大' : 'Zoom in'}</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>

        {/* Fullscreen Toggle */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={toggleFullscreen}>
                {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{isZh ? '全屏' : 'Fullscreen'}</TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Right Panel Toggle */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0"
                onClick={() => setIsPanelOpen(!isPanelOpen)}
              >
                {isPanelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              {isPanelOpen ? (isZh ? '收起面板' : 'Collapse panel') : (isZh ? '展开面板' : 'Expand panel')}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar: Section Navigation */}
        <div className="w-64 border-r bg-muted/10 flex flex-col shrink-0">
          <div className="px-3 py-2 border-b">
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              {isZh ? '论文章节' : 'Sections'}
            </h2>
          </div>
          <div className="flex-1 overflow-auto">
            <SectionTree
              imrad={paper.imradJson}
              onPageSelect={(page) => {
                setCurrentPage(page);
                handlePageChange(page);
              }}
              currentPage={currentPage}
            />
          </div>
        </div>

        {/* Center: PDF Viewer + Thumbnail Strip */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 overflow-hidden">
            <PDFViewer
              fileUrl={pdfUrl}
              currentPage={currentPage}
              onPageChange={handlePageChange}
              onNumPagesChange={handleNumPagesChange}
            />
          </div>
          {/* Thumbnail Strip at bottom */}
          <div className="h-28 border-t bg-muted/10 shrink-0">
            <ThumbnailStrip
              fileUrl={pdfUrl}
              currentPage={currentPage}
              onPageClick={(page) => {
                setCurrentPage(page);
                handlePageChange(page);
              }}
              thumbnailWidth={60}
            />
          </div>
        </div>

        {/* Right Panel: Collapsible Tabbed Panel */}
        {isPanelOpen && (
          <div className="w-80 border-l bg-white flex flex-col shrink-0">
            <Tabs value={rightTab} onValueChange={setRightTab} className="h-full flex flex-col">
              <TabsList className="px-2 pt-2 justify-start shrink-0">
                <TabsTrigger value="annotations" className="text-xs">
                  {isZh ? '批注' : 'Annotations'}
                </TabsTrigger>
                <TabsTrigger value="summary" className="text-xs">
                  {isZh ? 'AI总结' : 'AI Summary'}
                </TabsTrigger>
                <TabsTrigger value="notes" className="text-xs">
                  {isZh ? '笔记' : 'Notes'}
                </TabsTrigger>
              </TabsList>

              <TabsContent value="annotations" className="flex-1 overflow-hidden mt-0">
                <div className="h-full flex flex-col">
                  <AnnotationToolbar
                    paperId={id!}
                    pageNumber={currentPage}
                    onAnnotationCreated={handleAnnotationCreated}
                  />
                  <div className="flex-1 overflow-auto p-3">
                    {annotations.length === 0 ? (
                      <p className="text-xs text-muted-foreground text-center py-8">
                        {isZh ? '暂无批注' : 'No annotations yet'}
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {annotations.map((ann) => (
                          <div
                            key={ann.id}
                            className="p-2 rounded border text-xs"
                            style={{ borderLeftColor: ann.color, borderLeftWidth: 3 }}
                          >
                            <p className="text-muted-foreground">
                              {isZh ? '第' : 'Page'} {ann.pageNumber}
                            </p>
                            {ann.content && (
                              <p className="mt-1 text-foreground">{ann.content}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="summary" className="flex-1 overflow-hidden mt-0">
                <AISummaryPanel paperId={id!} summary={paper.readingNotes} />
              </TabsContent>

              <TabsContent value="notes" className="flex-1 overflow-hidden mt-0">
                <div className="h-full flex flex-col">
                  <div className="flex items-center justify-between px-3 py-2 border-b">
                    <span className="text-xs font-medium text-muted-foreground">
                      {isZh ? '阅读笔记' : 'Reading Notes'}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-6 text-[10px] px-2"
                      onClick={() => navigate('/notes')}
                    >
                      <FileText className="w-3 h-3 mr-1" />
                      {isZh ? '在侧边栏编辑笔记' : 'Edit in sidebar'}
                    </Button>
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <NotesEditor
                      content={(() => {
                        try {
                          return paper.readingNotes
                            ? JSON.parse(paper.readingNotes)
                            : { type: 'doc', content: [] };
                        } catch {
                          return {
                            type: 'doc',
                            content: [
                              {
                                type: 'paragraph',
                                content: [{ type: 'text', text: paper.readingNotes || '' }],
                              },
                            ],
                          };
                        }
                      })()}
                      onChange={(json) => {
                        handleNotesSave(JSON.stringify(json));
                      }}
                      placeholder={
                        isZh
                          ? '添加阅读笔记... 使用 [[pdf:paperId:page:5]] 引用论文'
                          : 'Add reading notes... Use [[pdf:paperId:page:5]] to reference'
                      }
                    />
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        )}
      </div>
    </div>
  );
}
