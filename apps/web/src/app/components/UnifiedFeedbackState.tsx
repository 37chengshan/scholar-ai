import { AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '@/app/components/ui/button';

interface UnifiedLoadingStateProps {
  label?: string;
  fullScreen?: boolean;
  className?: string;
}

interface UnifiedEmptyStateProps {
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

interface UnifiedErrorStateProps {
  title: string;
  description?: string;
  retryLabel?: string;
  onRetry?: () => void;
  className?: string;
}

export function UnifiedLoadingState({
  label = '加载中...',
  fullScreen = false,
  className,
}: UnifiedLoadingStateProps) {
  return (
    <div
      className={[
        'flex items-center justify-center',
        fullScreen ? 'min-h-[60vh]' : 'py-16',
        className || '',
      ]
        .join(' ')
        .trim()}
    >
      <div className="inline-flex items-center gap-2 text-zinc-600">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
        <span className="text-sm font-medium">{label}</span>
      </div>
    </div>
  );
}

export function UnifiedEmptyState({
  title,
  description,
  actionLabel,
  onAction,
  className,
}: UnifiedEmptyStateProps) {
  return (
    <div
      className={[
        'bg-white border-2 border-zinc-900 p-10 text-center space-y-4 shadow-[8px_8px_0px_0px_rgba(24,24,27,1)]',
        className || '',
      ]
        .join(' ')
        .trim()}
    >
      <div className="text-zinc-700 font-semibold">{title}</div>
      {description && <p className="text-zinc-500 text-sm leading-relaxed">{description}</p>}
      {actionLabel && onAction ? <Button onClick={onAction}>{actionLabel}</Button> : null}
    </div>
  );
}

export function UnifiedErrorState({
  title,
  description,
  retryLabel,
  onRetry,
  className,
}: UnifiedErrorStateProps) {
  return (
    <div
      className={[
        'bg-white border-2 border-zinc-900 p-8 text-center space-y-4 shadow-[8px_8px_0px_0px_rgba(24,24,27,1)]',
        className || '',
      ]
        .join(' ')
        .trim()}
    >
      <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-red-50 text-red-600 mx-auto">
        <AlertCircle className="w-5 h-5" />
      </div>
      <div className="text-zinc-800 font-semibold">{title}</div>
      {description && <p className="text-zinc-500 text-sm leading-relaxed">{description}</p>}
      {retryLabel && onRetry ? (
        <Button variant="outline" onClick={onRetry}>
          {retryLabel}
        </Button>
      ) : null}
    </div>
  );
}
