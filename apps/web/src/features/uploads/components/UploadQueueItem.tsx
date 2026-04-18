import { AlertCircle, CheckCircle2, Clock, Loader2, X } from 'lucide-react';
import { UploadQueueItem as UploadQueueItemModel } from '@/features/uploads/state/uploadWorkspaceStore';

interface UploadQueueItemProps {
  item: UploadQueueItemModel;
  onRemove: (id: string) => void;
  removable: boolean;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

function renderStatusIcon(status: UploadQueueItemModel['status']) {
  if (status === 'completed' || status === 'queued') {
    return <CheckCircle2 className="h-4 w-4 text-green-600" />;
  }
  if (status === 'uploading' || status === 'preparing') {
    return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
  }
  if (status === 'failed') {
    return <AlertCircle className="h-4 w-4 text-destructive" />;
  }
  return <Clock className="h-4 w-4 text-muted-foreground" />;
}

export function UploadQueueItem({ item, onRemove, removable }: UploadQueueItemProps) {
  return (
    <div className="flex items-start gap-3 rounded-md border border-border/60 px-3 py-2 bg-card">
      <div className="mt-0.5">{renderStatusIcon(item.status)}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm font-medium truncate">{item.fileName}</p>
          <span className="text-xs text-muted-foreground">{formatFileSize(item.sizeBytes)}</span>
        </div>
        <div className="mt-1 text-xs text-muted-foreground">
          {item.status === 'queued' ? '已入队，后台处理中' : `进度 ${Math.round(item.progress)}%`}
        </div>
        {item.error && <div className="mt-1 text-xs text-destructive">{item.error}</div>}
      </div>
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
  );
}
