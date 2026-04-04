/**
 * PDF Viewer Component
 *
 * React-pdf based PDF viewer with:
 * - Pagination controls (previous/next, page number)
 * - Zoom controls (50%-200%)
 * - Responsive layout
 *
 * Requirements: PAGE-06 (Read page PDF viewer)
 */

import { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Configure PDF.js worker (D-03)
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

interface PDFViewerProps {
  fileUrl: string;
  onPageChange?: (page: number) => void;
  initialPage?: number;
}

export function PDFViewer({ fileUrl, onPageChange, initialPage = 1 }: PDFViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState(initialPage);
  const [scale, setScale] = useState(1.0);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
  };

  const goToPage = (page: number) => {
    if (page >= 1 && page <= numPages) {
      setPageNumber(page);
      onPageChange?.(page);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Controls */}
      <div className="flex items-center gap-4 p-2 border-b">
        <button
          onClick={() => goToPage(pageNumber - 1)}
          disabled={pageNumber <= 1}
          className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed rounded"
        >
          Previous
        </button>
        <span className="text-sm">
          {pageNumber} / {numPages}
        </span>
        <button
          onClick={() => goToPage(pageNumber + 1)}
          disabled={pageNumber >= numPages}
          className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed rounded"
        >
          Next
        </button>
        <div className="flex-1" />
        <button
          onClick={() => setScale(s => Math.max(0.5, s - 0.1))}
          className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
        >
          -
        </button>
        <span className="text-sm">{Math.round(scale * 100)}%</span>
        <button
          onClick={() => setScale(s => Math.min(2, s + 0.1))}
          className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
        >
          +
        </button>
      </div>

      {/* PDF */}
      <div className="flex-1 overflow-auto">
        <Document file={fileUrl} onLoadSuccess={onDocumentLoadSuccess}>
          <Page pageNumber={pageNumber} scale={scale} />
        </Document>
      </div>
    </div>
  );
}