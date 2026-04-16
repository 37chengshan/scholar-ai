/**
 * Thumbnail Strip Component
 *
 * PDF page thumbnail navigation with:
 * - Horizontal scrollable row of page thumbnails
 * - Page preview thumbnails at reduced scale (default 60px width)
 * - Click to navigate to page
 * - Current page highlighted with accent border
 * - Lazy loading: only renders visible thumbnails + buffer of 3
 * - Cookie-based authentication for PDF loading
 *
 * Requirements: D-06 (Thumbnail navigation), 30-03 (horizontal layout, lazy loading)
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';
import * as papersApi from '@/services/papersApi';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface ThumbnailStripProps {
  paperId: string;
  currentPage: number;
  onPageClick: (page: number) => void;
  thumbnailWidth?: number;
}

export function ThumbnailStrip({
  paperId,
  currentPage,
  onPageClick,
  thumbnailWidth = 60,
}: ThumbnailStripProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 10 });
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const buffer = 3;

  useEffect(() => {
    const fetchPdf = async () => {
      try {
        const blob = await papersApi.downloadPdfBlob(paperId);
        const url = URL.createObjectURL(blob);
        setPdfBlobUrl(url);
      } catch (err: any) {
        console.error('ThumbnailStrip PDF fetch error:', err);
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

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setVisibleRange({ start: 0, end: Math.min(10, numPages) });
  };

  const handleScroll = useCallback(() => {
    if (!containerRef.current || numPages === 0) return;
    const container = containerRef.current;
    const scrollLeft = container.scrollLeft;
    const containerWidth = container.clientWidth;
    const thumbnailTotalWidth = thumbnailWidth + 8;

    const startPage = Math.max(0, Math.floor(scrollLeft / thumbnailTotalWidth) - buffer);
    const visibleCount = Math.ceil(containerWidth / thumbnailTotalWidth);
    const endPage = Math.min(numPages, startPage + visibleCount + buffer * 2);

    setVisibleRange({ start: Math.max(0, startPage), end: endPage });
  }, [numPages, thumbnailWidth, buffer]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  useEffect(() => {
    if (!containerRef.current || numPages === 0) return;
    const thumbnailEl = containerRef.current.querySelector(
      `[data-thumbnail-page="${currentPage}"]`
    );
    if (thumbnailEl) {
      thumbnailEl.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    }
  }, [currentPage, numPages]);

  const pagesToRender = Array.from(
    { length: visibleRange.end - visibleRange.start },
    (_, i) => visibleRange.start + i + 1
  );

  if (!pdfBlobUrl) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-xs">
        {isZh ? '加载缩略图...' : 'Loading thumbnails...'}
      </div>
    );
  }

  return (
    <div className="h-full" data-testid="thumbnail-strip">
      <Document
        file={pdfBlobUrl}
        onLoadSuccess={onDocumentLoadSuccess}
        loading={
          <div className="flex items-center justify-center h-full text-muted-foreground text-xs">
            {isZh ? '加载缩略图...' : 'Loading thumbnails...'}
          </div>
        }
      >
        <div
          ref={containerRef}
          className="flex items-center gap-2 h-full px-3 overflow-x-auto"
          style={{ scrollBehavior: 'smooth' }}
        >
          {pagesToRender.map((pageNum) => (
            <button
              key={pageNum}
              data-thumbnail-page={pageNum}
              onClick={() => onPageClick(pageNum)}
              data-testid={`thumbnail-${pageNum}`}
              className={clsx(
                'shrink-0 border-2 rounded overflow-hidden transition-all',
                currentPage === pageNum
                  ? 'border-accent shadow-md ring-2 ring-accent/20'
                  : 'border-transparent hover:border-muted-foreground'
              )}
              title={isZh ? `第 ${pageNum} 页` : `Page ${pageNum}`}
            >
              <Page
                pageNumber={pageNum}
                width={thumbnailWidth}
                renderTextLayer={false}
                renderAnnotationLayer={false}
                loading={
                  <div
                    className="bg-muted flex items-center justify-center"
                    style={{ width: thumbnailWidth, height: thumbnailWidth * 1.4 }}
                  >
                    <span className="text-[10px] text-muted-foreground">
                      {isZh ? '加载中...' : 'Loading...'}
                    </span>
                  </div>
                }
              />
            </button>
          ))}
        </div>
      </Document>
    </div>
  );
}