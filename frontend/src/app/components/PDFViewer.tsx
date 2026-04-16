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
}

export function PDFViewer({ paperId, currentPage, onPageChange, onNumPagesChange, initialPage = 1 }: PDFViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState(initialPage);
  const [scale, setScale] = useState(1.0);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchPdf = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const blob = await papersApi.downloadPdfBlob(paperId);
        const url = URL.createObjectURL(blob);
        setPdfBlobUrl(url);
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
      if (pdfBlobUrl) {
        URL.revokeObjectURL(pdfBlobUrl);
      }
    };
  }, [paperId]);

  useEffect(() => {
    if (currentPage !== undefined && currentPage !== pageNumber && currentPage >= 1 && currentPage <= numPages) {
      setPageNumber(currentPage);
    }
  }, [currentPage, pageNumber, numPages]);

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
      onPageChange?.(page);
    }
  };

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
          <Page pageNumber={pageNumber} scale={scale} data-page={pageNumber} />
        </Document>
      </div>
    </div>
  );
}