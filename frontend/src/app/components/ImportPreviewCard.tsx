/**
 * Import Preview Card Component
 *
 * Displays resolved source preview information before import confirmation.
 * Shows title, authors, year, venue, and PDF availability status.
 */

import { FileText, CheckCircle, AlertTriangle, Loader2 } from 'lucide-react';
import { cn } from './ui/utils';
import { SourceResolution } from '@/services/importApi';

interface ImportPreviewCardProps {
  preview: SourceResolution['preview'];
  availability?: SourceResolution['availability'];
  resolved?: boolean;
  loading?: boolean;
  errorMessage?: string | null;
}

export function ImportPreviewCard({
  preview,
  availability,
  resolved,
  loading,
  errorMessage,
}: ImportPreviewCardProps) {
  if (loading) {
    return (
      <div className="mt-4 rounded-lg border border-border/50 p-4 bg-card">
        <div className="flex items-center gap-3">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span className="text-sm text-muted-foreground">解析来源信息...</span>
        </div>
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div className="mt-4 rounded-lg border border-destructive/30 p-4 bg-destructive/5">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-destructive" />
          <div>
            <p className="text-sm font-medium text-destructive">解析失败</p>
            <p className="text-xs text-muted-foreground mt-1">{errorMessage}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!resolved || !preview) {
    return null;
  }

  const pdfAvailable = availability?.pdfAvailable ?? preview.pdfAvailable;

  return (
    <div className="mt-4 rounded-lg border-2 border-zinc-300 p-4 bg-white shadow-[4px_4px_0px_0px_rgba(24,24,27,0.2)]">
      <div className="flex items-start gap-4">
        <FileText className="h-8 w-8 text-zinc-400 flex-shrink-0 mt-1" />

        <div className="flex-1 min-w-0">
          {/* Title */}
          <h4 className="font-serif text-lg font-semibold text-zinc-900 leading-tight line-clamp-2">
            {preview.title || '未知标题'}
          </h4>

          {/* Authors */}
          {preview.authors && preview.authors.length > 0 && (
            <p className="text-sm text-zinc-600 mt-1 line-clamp-1">
              {preview.authors.slice(0, 5).join(', ')}
              {preview.authors.length > 5 && ` 等 ${preview.authors.length} 位作者`}
            </p>
          )}

          {/* Year and Venue */}
          <div className="flex items-center gap-3 mt-2 text-xs text-zinc-500">
            {preview.year && (
              <span className="font-medium">{preview.year}</span>
            )}
            {preview.venue && (
              <span className="truncate">{preview.venue}</span>
            )}
          </div>

          {/* PDF Availability Badge */}
          <div className="mt-3">
            <span
              className={cn(
                'inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-bold uppercase tracking-wider border',
                pdfAvailable
                  ? 'bg-green-50 text-green-700 border-green-200'
                  : 'bg-yellow-50 text-yellow-700 border-yellow-200'
              )}
            >
              {pdfAvailable ? (
                <>
                  <CheckCircle className="h-3.5 w-3.5" />
                  PDF 可获取
                </>
              ) : (
                <>
                  <AlertTriangle className="h-3.5 w-3.5" />
                  需上传 PDF
                </>
              )}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ImportPreviewCard;