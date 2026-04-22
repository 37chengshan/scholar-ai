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
      <div className="inline-flex items-center gap-2 text-muted-foreground">
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
        'bg-paper-1 border border-border/80 p-10 text-center space-y-4',
        className || '',
      ]
        .join(' ')
        .trim()}
    >
      <div className="text-foreground font-semibold">{title}</div>
      {description && <p className="text-muted-foreground text-sm leading-relaxed">{description}</p>}
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
        'bg-paper-1 border border-border/80 p-8 text-center space-y-4',
        className || '',
      ]
        .join(' ')
        .trim()}
    >
      <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-primary/[0.08] text-primary mx-auto">
        <AlertCircle className="w-5 h-5" />
      </div>
      <div className="text-foreground font-semibold">{title}</div>
      {description && <p className="text-muted-foreground text-sm leading-relaxed">{description}</p>}
      {retryLabel && onRetry ? (
        <Button variant="outline" onClick={onRetry}>
          {retryLabel}
        </Button>
      ) : null}
    </div>
  );
}
