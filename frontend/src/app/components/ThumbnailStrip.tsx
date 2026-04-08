/**
 * Thumbnail Strip Component
 *
 * PDF page thumbnail navigation with:
 * - Page preview thumbnails at reduced scale
 * - Click to navigate to page
 * - Current page highlighting
 * - Scroll container for many pages
 *
 * Requirements: D-06 (Thumbnail navigation in left sidebar)
 */

import { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { ScrollArea } from './ui/scroll-area';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';

// Configure PDF.js worker (same as PDFViewer)
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface ThumbnailStripProps {
  fileUrl: string;
  currentPage: number;
  onPageClick: (page: number) => void;
  thumbnailWidth?: number;
}

export function ThumbnailStrip({
  fileUrl,
  currentPage,
  onPageClick,
  thumbnailWidth = 120,
}: ThumbnailStripProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
  };

  return (
    <ScrollArea className="h-full" data-testid="thumbnail-strip">
      <Document
        file={fileUrl}
        onLoadSuccess={onDocumentLoadSuccess}
        loading={
          <div className="p-4 text-muted-foreground text-sm">
            {isZh ? '加载缩略图...' : 'Loading thumbnails...'}
          </div>
        }
      >
        <div className="flex flex-col gap-2 p-2">
          {Array.from({ length: numPages }, (_, i) => (
            <button
              key={i}
              onClick={() => onPageClick(i + 1)}
              data-testid={`thumbnail-${i + 1}`}
              className={clsx(
                'border-2 rounded transition-colors overflow-hidden',
                currentPage === i + 1
                  ? 'border-primary shadow-sm'
                  : 'border-transparent hover:border-muted-foreground'
              )}
              title={isZh ? `第 ${i + 1} 页` : `Page ${i + 1}`}
            >
              <Page
                pageNumber={i + 1}
                width={thumbnailWidth}
                renderTextLayer={false}
                renderAnnotationLayer={false}
                loading={
                  <div
                    className="bg-muted flex items-center justify-center"
                    style={{ width: thumbnailWidth, height: thumbnailWidth * 1.4 }}
                  >
                    <span className="text-xs text-muted-foreground">
                      {isZh ? '加载中...' : 'Loading...'}
                    </span>
                  </div>
                }
              />
              <div className="text-xs text-center mt-1 py-1 text-muted-foreground">
                {isZh ? `第 ${i + 1} 页` : `Page ${i + 1}`}
              </div>
            </button>
          ))}
        </div>
      </Document>
    </ScrollArea>
  );
}