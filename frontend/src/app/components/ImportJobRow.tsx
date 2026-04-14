/**
 * Import Job Row Component
 *
 * Displays a single import job with:
 * - Title or source input
 * - Source type badge
 * - Stage display (not just status)
 * - Progress bar (0-100)
 * - Error message for failed
 * - Action buttons: Retry, Cancel, View Result
 */

import { Loader2, CheckCircle, AlertCircle, Clock, RotateCcw, XCircle, ExternalLink } from 'lucide-react';
import { Button } from './ui/button';
import { Progress } from './ui/progress';
import { cn } from './ui/utils';
import { ImportJob } from '@/services/importApi';

// Stage labels mapping
const STAGE_LABELS: Record<string, string> = {
  awaiting_input: '等待输入',
  resolving_source: '解析来源',
  fetching_metadata: '获取元数据',
  downloading_pdf: '下载 PDF',
  validating_pdf: '验证 PDF',
  hashing_file: '计算哈希',
  dedupe_check: '去重检查',
  awaiting_dedupe_decision: '等待决策',
  materializing_paper: '创建论文',
  attaching_to_kb: '关联知识库',
  parsing: '解析内容',
  chunking: '切分内容',
  embedding: '生成向量',
  indexing: '索引存储',
  finalizing: '完成处理',
  completed: '完成',
};

interface ImportJobRowProps {
  job: ImportJob;
  showProgress?: boolean;
  showError?: boolean;
  showResult?: boolean;
  awaitingAction?: boolean;
  actionMessage?: string;
  onRetry?: () => void;
  onCancel?: () => void;
  onViewResult?: () => void;
}

// Source type labels
const SOURCE_TYPE_LABELS: Record<string, string> = {
  local_file: '本地',
  arxiv: 'arXiv',
  pdf_url: 'URL',
  doi: 'DOI',
  semantic_scholar: 'S2',
};

// Status color mapping
const STATUS_COLORS: Record<string, string> = {
  created: 'text-zinc-500',
  queued: 'text-blue-500',
  running: 'text-primary',
  awaiting_user_action: 'text-yellow-600',
  completed: 'text-green-600',
  failed: 'text-red-600',
  cancelled: 'text-zinc-400',
};

export function ImportJobRow({
  job,
  showProgress,
  showError,
  showResult,
  awaitingAction,
  actionMessage,
  onRetry,
  onCancel,
  onViewResult,
}: ImportJobRowProps) {
  const stageLabel = STAGE_LABELS[job.stage] || job.stage;
  const sourceLabel = SOURCE_TYPE_LABELS[job.sourceType] || job.sourceType;

  // Get display title
  const displayTitle =
    job.preview?.title || job.source?.rawInput || '未知来源';

  // Get status icon
  const getStatusIcon = () => {
    switch (job.status) {
      case 'created':
        return <Clock className="h-4 w-4 text-zinc-500" />;
      case 'queued':
        return <Clock className="h-4 w-4 text-blue-500" />;
      case 'running':
        return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
      case 'awaiting_user_action':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'cancelled':
        return <XCircle className="h-4 w-4 text-zinc-400" />;
      default:
        return <Clock className="h-4 w-4 text-zinc-500" />;
    }
  };

  return (
    <div
      className={cn(
        'flex items-center gap-4 rounded-lg border px-4 py-3 bg-white',
        job.status === 'failed' && 'border-red-200 bg-red-50/30',
        job.status === 'completed' && 'border-green-200 bg-green-50/30',
        job.status === 'awaiting_user_action' && 'border-yellow-200 bg-yellow-50/30',
        !['failed', 'completed', 'awaiting_user_action'].includes(job.status) && 'border-zinc-200'
      )}
    >
      {/* Status icon */}
      <div className="flex-shrink-0">{getStatusIcon()}</div>

      {/* Source type badge */}
      <span
        className={cn(
          'flex-shrink-0 px-2 py-0.5 text-xs font-bold uppercase tracking-wider border',
          job.sourceType === 'local_file' && 'bg-zinc-100 text-zinc-600 border-zinc-200',
          job.sourceType === 'arxiv' && 'bg-blue-100 text-blue-600 border-blue-200',
          job.sourceType === 'pdf_url' && 'bg-purple-100 text-purple-600 border-purple-200',
          job.sourceType === 'doi' && 'bg-indigo-100 text-indigo-600 border-indigo-200',
          job.sourceType === 'semantic_scholar' && 'bg-orange-100 text-orange-600 border-orange-200'
        )}
      >
        {sourceLabel}
      </span>

      {/* Title and metadata */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-zinc-900 truncate">
          {displayTitle}
        </p>

        {/* Stage display (not just status) */}
        <p className={cn('text-xs mt-0.5', STATUS_COLORS[job.status] || 'text-zinc-500')}>
          {stageLabel}
          {job.progress > 0 && job.status === 'running' && ` · ${job.progress}%`}
        </p>

        {/* Error message */}
        {showError && job.error?.message && (
          <p className="text-xs text-red-600 mt-1 truncate">
            {job.error.message}
          </p>
        )}

        {/* Awaiting action message */}
        {awaitingAction && actionMessage && (
          <p className="text-xs text-yellow-600 mt-1 font-medium">
            {actionMessage}
          </p>
        )}
      </div>

      {/* Progress bar */}
      {showProgress && job.status === 'running' && (
        <div className="w-24 flex-shrink-0">
          <Progress value={job.progress} className="h-2" />
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {onRetry && job.status === 'failed' && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRetry}
            className="h-7 text-xs"
          >
            <RotateCcw className="h-3 w-3 mr-1" />
            重试
          </Button>
        )}

        {onCancel && (job.status === 'running' || job.status === 'queued') && (
          <Button
            variant="outline"
            size="sm"
            onClick={onCancel}
            className="h-7 text-xs"
          >
            <XCircle className="h-3 w-3 mr-1" />
            取消
          </Button>
        )}

        {showResult && job.status === 'completed' && job.paper?.paperId && onViewResult && (
          <Button
            variant="outline"
            size="sm"
            onClick={onViewResult}
            className="h-7 text-xs"
          >
            <ExternalLink className="h-3 w-3 mr-1" />
            查看
          </Button>
        )}
      </div>
    </div>
  );
}

export default ImportJobRow;