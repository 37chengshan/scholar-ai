import { useState } from 'react';
import { AlertCircle, CheckCircle2, Clock, Loader2, X, XCircle } from 'lucide-react';
import { UploadQueueItem as UploadQueueItemModel } from '@/features/uploads/state/uploadWorkspaceStore';
import { STAGE_LABELS } from '@/app/components/ImportQueueList';
import { Progress } from '@/app/components/ui/progress';
import { CancelConfirmDialog } from './CancelConfirmDialog';

interface UploadQueueItemProps {
  item: UploadQueueItemModel;
  onRemove: (id: string) => void;
  onCancel?: (item: UploadQueueItemModel) => void;
  removable: boolean;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

function renderStatusIcon(status: UploadQueueItemModel['status']) {
  if (status === 'completed') {
    return <CheckCircle2 className="h-4 w-4 text-green-600" />;
  }
  if (status === 'queued') {
    return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
  }
  if (status === 'cancelled') {
    return <X className="h-4 w-4 text-muted-foreground" />;
  }
  if (status === 'uploading' || status === 'preparing') {
    return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
  }
  if (status === 'failed' || status === 'needs_file_reselect') {
    return <AlertCircle className="h-4 w-4 text-destructive" />;
  }
  return <Clock className="h-4 w-4 text-muted-foreground" />;
}

function renderStatusText(item: UploadQueueItemModel): string {
  if (item.status === 'completed') {
    return '处理完成';
  }

  if (item.status === 'queued' && item.pipelineStage) {
    const label = STAGE_LABELS[item.pipelineStage] ?? item.pipelineStage;
    return `处理中: ${label}`;
  }

  if (item.status === 'queued') {
    return '已入队，后台处理中';
  }

  if (item.status === 'needs_file_reselect') {
    return '需要重新选择原始文件后继续上传';
  }

  if (item.status === 'cancelled') {
    return '上传已取消';
  }

  return `进度 ${Math.round(item.progress)}%`;
}

export function UploadQueueItem({ item, onRemove, onCancel, removable }: UploadQueueItemProps) {
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const showPipelineProgress = item.status === 'queued' && item.pipelineStage;
  const canCancel = (item.status === 'uploading' || item.status === 'preparing' || item.status === 'queued') && onCancel;

  return (
    <>
      <div className="flex items-start gap-3 rounded-md border border-border/60 px-3 py-2 bg-card">
        <div className="mt-0.5">{renderStatusIcon(item.status)}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-medium truncate">{item.fileName}</p>
            <span className="text-xs text-muted-foreground">{formatFileSize(item.sizeBytes)}</span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            {renderStatusText(item)}
          </div>
          {showPipelineProgress && item.pipelineProgress != null && (
            <Progress value={item.pipelineProgress} className="h-1.5 mt-1.5" />
          )}
          {item.error && <div className="mt-1 text-xs text-destructive">{item.error}</div>}
        </div>
        <div className="flex items-center gap-1">
          {canCancel && (
            <button
              type="button"
              onClick={() => setCancelDialogOpen(true)}
              className="text-muted-foreground hover:text-destructive transition-colors"
              aria-label={`cancel-${item.fileName}`}
            >
              <XCircle className="h-4 w-4" />
            </button>
          )}
          {removable && (
            <button
              type="button"
              onClick={() => onRemove(item.id)}
              className="text-muted-foreground hover:text-destructive transition-colors"
              aria-label={`remove-${item.fileName}`}
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {canCancel && (
        <CancelConfirmDialog
          open={cancelDialogOpen}
          onOpenChange={setCancelDialogOpen}
          onConfirm={() => onCancel(item)}
        />
      )}
    </>
  );
}
