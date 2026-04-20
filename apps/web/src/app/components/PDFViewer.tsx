/**
 * PDF Viewer Component
 *
 * React-pdf based PDF viewer with:
 * - Pagination controls (previous/next, page number)
 * - Zoom controls (50%-200%)
 * - Smooth page scrolling when currentPage prop changes
 * - Responsive layout
 * - Cookie-based authentication for PDF loading
 *
 * Requirements: PAGE-06 (Read page PDF viewer), 30-03 (smooth page transitions)
 */

import { useState, useRef, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import * as papersApi from '@/services/papersApi';
import type { Annotation } from '@/services/annotationsApi';
import { toast } from 'sonner';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface PDFViewerProps {
  paperId: string;
  currentPage?: number;
  onPageChange?: (page: number) => void;
  onNumPagesChange?: (numPages: number) => void;
  initialPage?: number;
  annotations?: Annotation[];
  onTextSelection?: (selection: { text: string; position: { x: number; y: number; width: number; height: number } } | null) => void;
  activeAnnotationId?: string | null;
}

function clampPercent(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.min(100, Math.max(0, value));
}

function toRgba(hexColor: string, alpha: number): string {
  const normalized = hexColor.replace('#', '');
  if (normalized.length !== 6) {
    return `rgba(251, 191, 36, ${alpha})`;
  }
  const r = parseInt(normalized.slice(0, 2), 16);
  const g = parseInt(normalized.slice(2, 4), 16);
  const b = parseInt(normalized.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function PDFViewer({
  paperId,
  currentPage,
  onPageChange,
  onNumPagesChange,
  initialPage = 1,
  annotations = [],
  onTextSelection,
  activeAnnotationId = null,
}: PDFViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState(initialPage);
  const [scale, setScale] = useState(1.0);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draftSelection, setDraftSelection] = useState<{ text: string; position: { x: number; y: number; width: number; height: number } } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const pageLayerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let objectUrl: string | null = null;

    const fetchPdf = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const blob = await papersApi.downloadPdfBlob(paperId);
        objectUrl = URL.createObjectURL(blob);
        setPdfBlobUrl(objectUrl);
      } catch (err: any) {
        console.error('PDF fetch error:', err);
        const errorMsg = err.response?.status === 401 
          ? '请先登录后查看论文' 
          : err.response?.status === 404 
            ? 'PDF 文件未找到' 
            : '加载 PDF 失败';
        setError(errorMsg);
        toast.error(errorMsg);
      } finally {
        setLoading(false);
      }
    };

    if (paperId) {
      fetchPdf();
    }

    return () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [paperId]);

  useEffect(() => {
    if (currentPage !== undefined && currentPage !== pageNumber && currentPage >= 1 && currentPage <= numPages) {
      setPageNumber(currentPage);
      setDraftSelection(null);
      onTextSelection?.(null);
    }
  }, [currentPage, pageNumber, numPages, onTextSelection]);

  useEffect(() => {
    if (containerRef.current && numPages > 0) {
      const pageEl = containerRef.current.querySelector(`[data-page="${pageNumber}"]`);
      if (pageEl) {
        pageEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  }, [pageNumber, numPages]);

  const onDocumentLoadSuccess = ({ numPages: pages }: { numPages: number }) => {
    setNumPages(pages);
    onNumPagesChange?.(pages);
  };

  const goToPage = (page: number) => {
    if (page >= 1 && page <= numPages) {
      setPageNumber(page);
      setDraftSelection(null);
      onTextSelection?.(null);
      onPageChange?.(page);
    }
  };

  const handleTextSelection = () => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) {
      return;
    }

    const selectedText = selection.toString().trim();
    if (!selectedText) {
      setDraftSelection(null);
      onTextSelection?.(null);
      return;
    }

    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    const pageRect = pageLayerRef.current?.getBoundingClientRect();

    if (!pageRect || rect.width === 0 || rect.height === 0) {
      return;
    }

    const isInsidePage =
      rect.bottom >= pageRect.top &&
      rect.top <= pageRect.bottom &&
      rect.right >= pageRect.left &&
      rect.left <= pageRect.right;

    if (!isInsidePage) {
      return;
    }

    const position = {
      x: clampPercent(((rect.left - pageRect.left) / pageRect.width) * 100),
      y: clampPercent(((rect.top - pageRect.top) / pageRect.height) * 100),
      width: clampPercent((rect.width / pageRect.width) * 100),
      height: clampPercent((rect.height / pageRect.height) * 100),
    };

    const selectionPayload = {
      text: selectedText,
      position,
    };
    setDraftSelection(selectionPayload);
    onTextSelection?.(selectionPayload);
  };

  const currentPageAnnotations = annotations.filter((item) => item.pageNumber === pageNumber);

  if (loading) {
    return (
      <div className="flex flex-col h-full items-center justify-center" data-testid="pdf-viewer-loading">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
        <p className="text-sm text-muted-foreground">加载 PDF...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col h-full items-center justify-center" data-testid="pdf-viewer-error">
        <p className="text-sm text-destructive">{error}</p>
      </div>
    );
  }

  if (!pdfBlobUrl) {
    return (
      <div className="flex flex-col h-full items-center justify-center" data-testid="pdf-viewer-empty">
        <p className="text-sm text-muted-foreground">无 PDF 内容</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full" data-testid="pdf-viewer">
      <div className="flex items-center gap-4 p-2 border-b bg-white" data-testid="pdf-controls">
        <button
          onClick={() => goToPage(pageNumber - 1)}
          disabled={pageNumber <= 1}
          data-testid="prev-page"
          className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed rounded"
        >
          Previous
        </button>
        <span className="text-sm" data-testid="page-counter">
          {pageNumber} / {numPages}
        </span>
        <button
          onClick={() => goToPage(pageNumber + 1)}
          disabled={pageNumber >= numPages}
          data-testid="next-page"
          className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed rounded"
        >
          Next
        </button>
        <div className="flex-1" />
        <button
          onClick={() => setScale(s => Math.max(0.5, s - 0.1))}
          data-testid="zoom-out"
          className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
        >
          -
        </button>
        <span className="text-sm min-w-[48px] text-center" data-testid="zoom-level">{Math.round(scale * 100)}%</span>
        <button
          onClick={() => setScale(s => Math.min(2, s + 0.1))}
          data-testid="zoom-in"
          className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
        >
          +
        </button>
      </div>

      <div
        ref={containerRef}
        className="flex-1 overflow-auto"
        style={{ scrollBehavior: 'smooth' }}
        data-testid="pdf-content"
      >
        <Document file={pdfBlobUrl} onLoadSuccess={onDocumentLoadSuccess}>
          <div
            ref={pageLayerRef}
            className="relative mx-auto w-fit"
            data-page={pageNumber}
            onMouseUp={handleTextSelection}
          >
            <Page pageNumber={pageNumber} scale={scale} />

            <div className="pointer-events-none absolute inset-0">
              {currentPageAnnotations.map((annotation) => {
                const position = annotation.position || {};
                const x = typeof position.x === 'number' ? position.x : 0;
                const y = typeof position.y === 'number' ? position.y : 0;
                const width = typeof position.width === 'number' ? position.width : 0;
                const height = typeof position.height === 'number' ? position.height : 0;
                const isActive = activeAnnotationId === annotation.id;

                return (
                  <div
                    key={annotation.id}
                    className="absolute rounded-sm transition-all"
                    style={{
                      left: `${clampPercent(x)}%`,
                      top: `${clampPercent(y)}%`,
                      width: `${clampPercent(width)}%`,
                      height: `${Math.max(1, clampPercent(height))}%`,
                      backgroundColor: toRgba(annotation.color || '#FFEB3B', isActive ? 0.55 : 0.35),
                      outline: isActive ? `1px solid ${annotation.color || '#FFEB3B'}` : 'none',
                    }}
                    title={annotation.content || 'highlight'}
                  />
                );
              })}

              {draftSelection && (
                <div
                  className="absolute rounded-sm border border-primary/50 bg-primary/20"
                  style={{
                    left: `${draftSelection.position.x}%`,
                    top: `${draftSelection.position.y}%`,
                    width: `${draftSelection.position.width}%`,
                    height: `${Math.max(1, draftSelection.position.height)}%`,
                  }}
                />
              )}
            </div>
          </div>
        </Document>
      </div>
    </div>
  );
}