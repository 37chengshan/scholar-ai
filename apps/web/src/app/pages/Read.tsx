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

import { useState, useEffect, useCallback } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router";
import { PDFViewer } from "../components/PDFViewer";
import { SectionTree } from "../components/SectionTree";
import { AnnotationToolbar } from "../components/AnnotationToolbar";
import { ThumbnailStrip } from "../components/ThumbnailStrip";
import { AISummaryPanel } from "../components/AISummaryPanel";
import { NotesEditor } from "../components/NotesEditor";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "../components/ui/tabs";
import { Button } from "../components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "../components/ui/tooltip";
import * as papersApi from "@/services/papersApi";
import * as annotationsApi from "@/services/annotationsApi";
import * as notesApi from "@/services/notesApi";
import type { Annotation } from "@/services/annotationsApi";
import {
  buildReadingNoteTitle,
  createEmptyEditorDocument,
  getPrimaryUserNoteForPaper,
} from '@/features/notes/ownership';

import { toast } from "sonner";
import { useLanguage } from "../contexts/LanguageContext";
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
} from "lucide-react";

/**
 * Internal Read component that uses Router hooks
 * Extracted to ensure Router context is available
 */
function ReadContent() {
  const MIN_PANEL_WIDTH = 320;
  const MAX_PANEL_WIDTH = 620;

  const { id } = useParams<{ id?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { language } = useLanguage();
  const isZh = language === "zh";

  const [paper, setPaper] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState<number | null>(null);
  const [scale, setScale] = useState(1.0);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [rightTab, setRightTab] = useState("notes");
  const [isPanelOpen, setIsPanelOpen] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [panelWidth, setPanelWidth] = useState(360);
  const [isResizingPanel, setIsResizingPanel] = useState(false);
  const [selectedText, setSelectedText] = useState("");
  const [selectionPosition, setSelectionPosition] = useState<{
    x: number;
    y: number;
    width: number;
    height: number;
  } | null>(null);
  const [activeAnnotationId, setActiveAnnotationId] = useState<string | null>(null);
  const [linkedNoteId, setLinkedNoteId] = useState<string | null>(null);
  const [linkedNoteTitle, setLinkedNoteTitle] = useState<string>("");
  const [linkedNoteContent, setLinkedNoteContent] = useState<any>(createEmptyEditorDocument());

  const clampPage = useCallback(
    (page: number) => {
      const upper = totalPages || Number.MAX_SAFE_INTEGER;
      return Math.max(1, Math.min(page, upper));
    },
    [totalPages],
  );

  const parseNoteJson = useCallback((raw: string | null | undefined) => {
    if (!raw) {
      return { type: "doc", content: [] };
    }

    try {
      return JSON.parse(raw);
    } catch {
      return {
        type: "doc",
        content: [
          {
            type: "paragraph",
            content: [{ type: "text", text: raw }],
          },
        ],
      };
    }
  }, []);

  const initializeLinkedNote = useCallback(
    async (paperId: string, paperTitle: string) => {
      const noteTitle = buildReadingNoteTitle(paperTitle, isZh);
      const existingNotes = await notesApi.getNotesByPaper(paperId);
      const userNote = getPrimaryUserNoteForPaper(existingNotes, paperId);

      const targetNote =
        userNote ||
        (await notesApi.createNote({
          title: noteTitle,
          content: JSON.stringify(createEmptyEditorDocument()),
          tags: ["read-note"],
          paperIds: [paperId],
        }));

      setLinkedNoteId(targetNote.id);
      setLinkedNoteTitle(targetNote.title || noteTitle);
      setLinkedNoteContent(parseNoteJson(targetNote.content));
    },
    [isZh, parseNoteJson],
  );

  // Handle ?page= URL parameter for PDF reference jumps from notes
  useEffect(() => {
    const targetPage = searchParams.get("page");
    if (targetPage) {
      const page = parseInt(targetPage, 10);
      if (!isNaN(page) && page >= 1) {
        setCurrentPage(clampPage(page));
        // Clear the ?page= parameter after navigating to avoid re-triggering
        const newParams = new URLSearchParams(searchParams);
        newParams.delete("page");
        setSearchParams(newParams, { replace: true });
      }
    }
  }, [clampPage, searchParams, setSearchParams]);

  // Load paper data
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

        // Load annotations
        const annotationData = await annotationsApi.list(id);
        setAnnotations(annotationData);

        await initializeLinkedNote(id, data.title || "");
      } catch (error: any) {
        const errorMsg =
          error?.message || (isZh ? "加载论文失败" : "Failed to load paper");
        setError(errorMsg);
        toast.error(errorMsg);
      } finally {
        setLoading(false);
      }
    }

    loadPaper();
  }, [id, isZh, initializeLinkedNote]);

  // Handle page change from PDF viewer
  const handlePageChange = useCallback(
    async (page: number) => {
      const nextPage = clampPage(page);
      setCurrentPage(nextPage);
      if (!id) {
        return;
      }
      // Save reading progress
      try {
        await papersApi.saveReadingProgress(id, nextPage);
      } catch (error: any) {
        // Don't block reading, just show a brief warning
        toast.warning(
          isZh ? "阅读进度保存失败" : "Failed to save reading progress",
        );
      }
    },
    [clampPage, id, isZh],
  );

  const handleAnnotationCreated = async () => {
    if (!id) return;
    const annotationData = await annotationsApi.list(id);
    setAnnotations(annotationData);
    setSelectedText("");
    setSelectionPosition(null);
  };

  useEffect(() => {
    if (!isResizingPanel) {
      return;
    }

    const onMouseMove = (event: MouseEvent) => {
      const nextWidth = window.innerWidth - event.clientX;
      const clampedWidth = Math.min(MAX_PANEL_WIDTH, Math.max(MIN_PANEL_WIDTH, nextWidth));
      setPanelWidth(clampedWidth);
    };

    const onMouseUp = () => {
      setIsResizingPanel(false);
      document.body.style.userSelect = "";
    };

    document.body.style.userSelect = "none";
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
      document.body.style.userSelect = "";
    };
  }, [isResizingPanel]);

  // Handle total pages change from PDF viewer
  const handleNumPagesChange = useCallback((numPages: number) => {
    setTotalPages(numPages);
    setCurrentPage((previous) => Math.min(previous, numPages));
  }, []);

  const handleNotesSave = useCallback(
    async (content: any) => {
      if (!id || !linkedNoteId) return;
      try {
        await notesApi.updateNote(linkedNoteId, {
          title:
            linkedNoteTitle ||
            buildReadingNoteTitle(paper?.title, isZh),
          content: JSON.stringify(content),
          paperIds: [id],
        });
      } catch (error: any) {
        toast.error(isZh ? "笔记保存失败" : "Failed to save notes");
      }
    },
    [id, isZh, linkedNoteId, linkedNoteTitle, paper?.title],
  );

  useEffect(() => {
    if (!linkedNoteId) {
      return;
    }

    const timer = window.setTimeout(() => {
      handleNotesSave(linkedNoteContent);
    }, 800);

    return () => {
      window.clearTimeout(timer);
    };
  }, [handleNotesSave, linkedNoteContent, linkedNoteId]);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  useEffect(() => {
    const onFullscreenChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () => {
      document.removeEventListener("fullscreenchange", onFullscreenChange);
    };
  }, []);

  if (!id) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <div className="max-w-xl px-8 text-center">
          <div className="text-[10px] font-bold uppercase tracking-[0.28em] text-muted-foreground">
            {isZh ? "阅读工作台" : "Reading Workspace"}
          </div>
          <h1 className="mt-4 font-serif text-4xl font-semibold tracking-tight text-foreground">
            {isZh ? "选择一篇论文开始沉浸阅读" : "Choose a paper to start focused reading"}
          </h1>
          <p className="mt-4 text-sm leading-7 text-muted-foreground">
            {isZh
              ? "左侧导航已经可以进入阅读页；接下来从知识库、检索结果或笔记引用里打开具体论文。"
              : "The reading page is now directly reachable. Open a paper from knowledge bases, search results, or linked notes to continue."}
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Button onClick={() => navigate("/knowledge-bases")} className="rounded-full px-5">
              {isZh ? "前往知识库" : "Open Knowledge Bases"}
            </Button>
            <Button variant="outline" onClick={() => navigate("/search")} className="rounded-full px-5">
              {isZh ? "前往检索" : "Go to Search"}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (loading || !paper) {
    return (
      <div className="flex items-center justify-center h-full">
        {error ? (
          <div className="text-center">
            <p className="text-destructive mb-4">{error}</p>
            <Button onClick={() => navigate("/knowledge-bases")}>
              {isZh ? "返回知识库" : "Back to Knowledge Bases"}
            </Button>
          </div>
        ) : isZh ? (
          "加载中..."
        ) : (
          "Loading..."
        )}
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-background">
      {/* Top Toolbar */}
      <div className="magazine-toolbar flex items-center gap-3 border-b border-border/50 bg-background/95 px-4 py-3 backdrop-blur-sm shrink-0">
        <div className="min-w-0">
          <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-muted-foreground">
            {isZh ? "Focused Reading" : "Focused Reading"}
          </div>
          <h1
          className="mt-2 max-w-xs truncate font-serif text-lg font-semibold text-foreground"
          title={paper.title}
        >
          {paper.title || (isZh ? "未命名论文" : "Untitled Paper")}
          </h1>
        </div>

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
          <span className="min-w-[72px] text-center text-xs tabular-nums text-muted-foreground">
            {currentPage} / {totalPages ?? (isZh ? "加载中" : "...")}
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0"
            onClick={() => handlePageChange(clampPage(currentPage + 1))}
            disabled={totalPages !== null && currentPage >= totalPages}
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
                  onClick={() => setScale((s) => Math.max(0.5, s - 0.1))}
                >
                  <ZoomOut className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>{isZh ? "缩小" : "Zoom out"}</TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <span className="min-w-[48px] text-center text-xs text-muted-foreground">
            {Math.round(scale * 100)}%
          </span>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={() => setScale((s) => Math.min(2, s + 0.1))}
                >
                  <ZoomIn className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>{isZh ? "放大" : "Zoom in"}</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>

        {/* Fullscreen Toggle */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0"
                onClick={toggleFullscreen}
              >
                {isFullscreen ? (
                  <Minimize2 className="h-4 w-4" />
                ) : (
                  <Maximize2 className="h-4 w-4" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{isZh ? "全屏" : "Fullscreen"}</TooltipContent>
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
                {isPanelOpen ? (
                  <PanelRightClose className="h-4 w-4" />
                ) : (
                  <PanelRightOpen className="h-4 w-4" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              {isPanelOpen
                ? isZh
                  ? "收起面板"
                  : "Collapse panel"
                : isZh
                  ? "展开面板"
                  : "Expand panel"}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden bg-background">
        {/* Left Sidebar: Section Navigation */}
        <div className="hidden w-[220px] shrink-0 border-r border-border/50 bg-muted/20 lg:flex lg:flex-col">
          <div className="border-b border-border/50 px-5 py-4">
            <h2 className="text-[9px] font-bold text-muted-foreground uppercase tracking-[0.2em]">
              {isZh ? "论文章节" : "Sections"}
            </h2>
          </div>
          <div className="flex-1 overflow-auto">
            <SectionTree
              imrad={paper.imradJson}
              onPageSelect={(page) => {
                setCurrentPage(clampPage(page));
                handlePageChange(clampPage(page));
              }}
              currentPage={currentPage}
              isZh={isZh}
            />
          </div>
        </div>

        {/* Center: PDF Viewer + Thumbnail Strip */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 overflow-hidden">
            <PDFViewer
              paperId={id!}
              currentPage={currentPage}
              onPageChange={handlePageChange}
              onNumPagesChange={handleNumPagesChange}
              annotations={annotations}
              activeAnnotationId={activeAnnotationId}
              onTextSelection={(selection) => {
                if (!selection) {
                  setSelectedText("");
                  setSelectionPosition(null);
                  return;
                }
                setSelectedText(selection.text);
                setSelectionPosition(selection.position);
              }}
            />
          </div>
          {/* Thumbnail Strip at bottom */}
          <div className="h-28 border-t bg-muted/10 shrink-0">
            <ThumbnailStrip
              paperId={id!}
              currentPage={currentPage}
              onPageClick={(page) => {
                const nextPage = clampPage(page);
                setCurrentPage(nextPage);
                handlePageChange(nextPage);
              }}
              thumbnailWidth={60}
            />
          </div>
        </div>

        {/* Right Panel: Collapsible Tabbed Panel */}
        {isPanelOpen && (
          <>
            <div
              role="separator"
              aria-orientation="vertical"
              aria-label={isZh ? "调整右侧面板宽度" : "Resize right panel"}
              className="hidden w-1 cursor-col-resize bg-border/50 transition-colors hover:bg-primary/50 lg:block"
              onMouseDown={() => setIsResizingPanel(true)}
            />

            <div
              className="hidden border-l border-border/50 bg-muted/10 lg:flex lg:flex-col shrink-0"
              style={{ width: `${panelWidth}px` }}
            >
            <Tabs
              value={rightTab}
              onValueChange={setRightTab}
              className="h-full flex flex-col"
            >
              <div className="border-b border-border/50 bg-background/80 backdrop-blur-md px-5 py-4">
                <div className="text-[9px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
                  {isZh ? "Reading Inspector" : "Reading Inspector"}
                </div>
                <div className="mt-2 font-serif text-[1.35rem] font-bold text-foreground">
                  {isZh ? "批注与笔记" : "Notes & Annotations"}
                </div>
              </div>
              <TabsList className="px-3 pt-3 justify-start shrink-0 bg-transparent">
                <TabsTrigger value="notes" className="text-xs">
                  {isZh ? "笔记" : "Notes"}
                </TabsTrigger>
                <TabsTrigger value="annotations" className="text-xs">
                  {isZh ? "批注" : "Annotations"}
                </TabsTrigger>
                <TabsTrigger value="summary" className="text-xs">
                  {isZh ? "AI总结" : "AI Summary"}
                </TabsTrigger>
              </TabsList>

              <TabsContent
                value="annotations"
                className="flex-1 overflow-hidden mt-0"
              >
                <div className="h-full flex flex-col">
                  <AnnotationToolbar
                    paperId={id!}
                    pageNumber={currentPage}
                    onAnnotationCreated={handleAnnotationCreated}
                    selectedText={selectedText}
                    selectionPosition={selectionPosition}
                  />
                  <div className="flex-1 overflow-auto p-3">
                    {annotations.length === 0 ? (
                      <p className="text-xs text-muted-foreground text-center py-8">
                        {isZh ? "暂无批注" : "No annotations yet"}
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {annotations.map((ann) => (
                          <div
                            key={ann.id}
                            className="cursor-pointer rounded-2xl border border-border/60 bg-background p-3 text-xs transition-colors hover:bg-primary/[0.04]"
                            onClick={() => {
                              setCurrentPage(clampPage(ann.pageNumber));
                              handlePageChange(clampPage(ann.pageNumber));
                              setActiveAnnotationId(ann.id);
                              setRightTab("annotations");
                            }}
                            style={{
                              borderLeftColor: ann.color,
                              borderLeftWidth: 3,
                            }}
                          >
                            <p className="text-muted-foreground">
                              {isZh ? "第" : "Page"} {ann.pageNumber}
                            </p>
                            {ann.content && (
                              <p className="mt-1 text-foreground">
                                {ann.content}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </TabsContent>

              <TabsContent
                value="summary"
                className="flex-1 overflow-hidden mt-0"
              >
                <AISummaryPanel paperId={id!} summary={paper.readingNotes} />
              </TabsContent>

              <TabsContent
                value="notes"
                className="flex-1 overflow-hidden mt-0"
              >
                <div className="h-full flex flex-col">
                  <div className="flex items-center justify-between border-b border-border/60 px-3 py-3">
                    <span className="text-xs font-medium text-muted-foreground">
                      {isZh ? "阅读笔记" : "Reading Notes"}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 rounded-full border-border/70 bg-background px-3 text-[10px]"
                      onClick={() => navigate(`/notes?paperId=${id}${linkedNoteId ? `&noteId=${linkedNoteId}` : ""}`)}
                    >
                      <FileText className="w-3 h-3 mr-1" />
                      {isZh ? "在侧边栏编辑笔记" : "Edit in sidebar"}
                    </Button>
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <NotesEditor
                      content={linkedNoteContent}
                      onChange={(json) => {
                        setLinkedNoteContent(json);
                      }}
                      placeholder={
                        isZh
                          ? "添加阅读笔记... 使用 [[pdf:paperId:page:5]] 引用论文"
                          : "Add reading notes... Use [[pdf:paperId:page:5]] to reference"
                      }
                    />
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </div>
          </>
        )}
      </div>
    </div>
  );
}

/**
 * Outer Read component wrapper
 * This ensures the Router context is available when ReadContent is rendered
 */
export function Read() {
  return <ReadContent />;
}
