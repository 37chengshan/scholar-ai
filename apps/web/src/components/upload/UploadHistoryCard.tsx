/**
 * UploadHistoryCard Component
 *
 * Displays a single upload history record with:
 * - Basic info: filename, status, created time
 * - Expandable details for processing stats
 * - Delete action with confirmation
 *
 * Per D-01: Expandable details, failure details, safe deletion
 * Per D-02: Progress display, history tracking
 * Per UI-SPEC: 12px padding, accent color for status
 */

import { useState } from 'react';
import { clsx } from 'clsx';
import { ChevronDown, ChevronUp, Trash2, ExternalLink, AlertCircle, CheckCircle2, Clock, Loader2 } from 'lucide-react';
import { useLanguage } from '@/app/contexts/LanguageContext';
import type { UploadHistoryRecord } from '@/services/uploadHistoryApi';
import { Progress } from '@/app/components/ui/progress';

/**
 * Component props
 */
interface UploadHistoryCardProps {
  record: UploadHistoryRecord;
  onDelete: (id: string) => void;
}

/**
 * Format relative time
 */
function formatRelativeTime(dateString: string, isZh: boolean): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return isZh ? '刚刚' : 'Just now';
  if (diffMins < 60) return isZh ? `${diffMins}分钟前` : `${diffMins} mins ago`;
  if (diffHours < 24) return isZh ? `${diffHours}小时前` : `${diffHours} hours ago`;
  if (diffDays < 7) return isZh ? `${diffDays}天前` : `${diffDays} days ago`;
  return date.toLocaleDateString();
}

/**
 * Format processing time in seconds
 */
function formatProcessingTime(ms: number | null | undefined, isZh: boolean): string {
  if (!ms) return '-';
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return isZh ? `${seconds}秒` : `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return isZh ? `${mins}分${secs}秒` : `${mins}m ${secs}s`;
}

/**
 * UploadHistoryCard Component
 *
 * @param props - Component props
 * @returns JSX element
 */
export function UploadHistoryCard({ record, onDelete }: UploadHistoryCardProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const [isExpanded, setIsExpanded] = useState(false);

  const t = {
    viewDetails: isZh ? '查看详情' : 'View Details',
    deleteRecord: isZh ? '删除记录' : 'Delete Record',
    viewPaper: isZh ? '查看论文' : 'View Paper',
    chunks: isZh ? '文本块' : 'Chunks',
    llmTokens: isZh ? 'LLM Tokens' : 'LLM Tokens',
    pages: isZh ? '页数' : 'Pages',
    images: isZh ? '图片' : 'Images',
    tables: isZh ? '表格' : 'Tables',
    processingTime: isZh ? '处理时间' : 'Processing Time',
    error: isZh ? '错误信息' : 'Error',
  };

  // Status badge styling
  const getStatusBadge = () => {
    switch (record.status) {
      case 'PROCESSING':
        return {
          icon: <Loader2 className="w-3 h-3 animate-spin" />,
          className: 'bg-blue-500/10 text-blue-600 border border-blue-500/20',
          text: isZh ? '处理中' : 'Processing',
        };
      case 'COMPLETED':
        return {
          icon: <CheckCircle2 className="w-3 h-3" />,
          className: 'bg-green-500/10 text-green-600 border border-green-500/20',
          text: isZh ? '完成' : 'Completed',
        };
      case 'FAILED':
        return {
          icon: <AlertCircle className="w-3 h-3" />,
          className: 'bg-red-500/10 text-red-600 border border-red-500/20',
          text: isZh ? '失败' : 'Failed',
        };
      default:
        return {
          icon: <Clock className="w-3 h-3" />,
          className: 'bg-muted text-muted-foreground border border-border/50',
          text: record.status,
        };
    }
  };

  const statusBadge = getStatusBadge();

  return (
    <div className="flex flex-col border border-border/50 bg-card rounded-sm shadow-sm overflow-hidden hover:border-primary/20 transition-colors">
      {/* Main content row */}
      <div className="flex items-center gap-3 px-3 py-2.5">
        {/* Filename */}
        <div className="flex-1 min-w-0">
          <span className="text-[11px] font-mono font-bold text-foreground truncate block">
            {record.filename}
          </span>
        </div>

        {/* Status badge */}
        <span className={clsx(
          'text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-sm flex items-center gap-1.5',
          statusBadge.className
        )}>
          {statusBadge.icon}
          {statusBadge.text}
        </span>

        {/* Created time */}
        <span className="text-[9px] font-mono text-muted-foreground whitespace-nowrap">
          {formatRelativeTime(record.createdAt, isZh)}
        </span>

        {/* Expand button */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1 hover:bg-muted rounded-sm transition-colors"
        >
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          )}
        </button>
      </div>

      {/* Expandable details */}
      {isExpanded && (
        <div className="px-3 py-3 border-t border-border/50 bg-muted/10">
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-[10px]">
            {record.progress !== null && record.progress !== undefined && (
              <div className="col-span-2 space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">进度:</span>
                  <span className="font-bold">{record.progress}%</span>
                </div>
                <Progress value={record.progress} className="h-1.5" />
              </div>
            )}

            {/* Processing stats - show for COMPLETED */}
            {record.status === 'COMPLETED' && (
              <>
                {record.chunksCount !== null && record.chunksCount !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t.chunks}:</span>
                    <span className="font-bold">{record.chunksCount}</span>
                  </div>
                )}
                {record.llmTokens !== null && record.llmTokens !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t.llmTokens}:</span>
                    <span className="font-bold">{record.llmTokens.toLocaleString()}</span>
                  </div>
                )}
                {record.pageCount !== null && record.pageCount !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t.pages}:</span>
                    <span className="font-bold">{record.pageCount}</span>
                  </div>
                )}
                {record.imageCount !== null && record.imageCount !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t.images}:</span>
                    <span className="font-bold">{record.imageCount}</span>
                  </div>
                )}
                {record.tableCount !== null && record.tableCount !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t.tables}:</span>
                    <span className="font-bold">{record.tableCount}</span>
                  </div>
                )}
                {record.processingTime !== null && record.processingTime !== undefined && (
                  <div className="flex justify-between col-span-2">
                    <span className="text-muted-foreground">{t.processingTime}:</span>
                    <span className="font-bold">{formatProcessingTime(record.processingTime, isZh)}</span>
                  </div>
                )}
              </>
            )}

            {/* Error message - show for FAILED */}
            {record.status === 'FAILED' && record.errorMessage && (
              <div className="col-span-2">
                <span className="text-red-500 text-[9px]">{t.error}:</span>
                <p className="text-red-600 text-[9px] mt-1 bg-red-500/10 p-2 rounded-sm">
                  {record.errorMessage}
                </p>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-2 mt-3 pt-3 border-t border-border/30">
            {/* View paper button - if paperId exists */}
            {record.paper?.id && (
              <a
                href={`/read/${record.paper.id}`}
                className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-widest text-primary hover:text-primary/80 transition-colors"
              >
                <ExternalLink className="w-3 h-3" />
                {t.viewPaper}
              </a>
            )}

            {/* Delete button */}
            <button
              onClick={() => onDelete(record.id)}
              className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-widest text-red-500 hover:text-red-600 transition-colors ml-auto"
            >
              <Trash2 className="w-3 h-3" />
              {t.deleteRecord}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export type { UploadHistoryCardProps };
