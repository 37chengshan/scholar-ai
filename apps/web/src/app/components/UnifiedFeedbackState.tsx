import { cva, type VariantProps } from 'class-variance-authority';
import { AlertCircle, FileQuestion, Loader2, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import React from 'react';
import { Button } from '@/app/components/ui/button';

const feedbackVariants = cva(
  "flex flex-col items-center justify-center p-8 text-center animate-in fade-in duration-500",
  {
    variants: {
      status: {
        empty: "text-stone-500 bg-stone-50/50 rounded-xl border border-dashed border-stone-200",
        error: "text-red-700 bg-red-50/50 rounded-xl border border-red-100",
        loading: "text-orange-600",
        partial: "text-amber-700 bg-amber-50 rounded-xl border border-amber-200",
      },
      size: { sm: "min-h-[120px] text-sm py-4", md: "min-h-[240px] text-base" }
    },
    defaultVariants: { status: "empty", size: "md" }
  }
);

interface UnifiedFeedbackStateProps extends VariantProps<typeof feedbackVariants> {
  title?: string;
  message?: string;
  action?: React.ReactNode;
  className?: string;
}

export function UnifiedFeedbackState({ status, size, title, message, action, className }: UnifiedFeedbackStateProps) {
  const Icon = status === 'error' ? AlertCircle :
               status === 'loading' ? Loader2 :
               status === 'partial' ? Info : FileQuestion;

  return (
    <div className={cn(feedbackVariants({ status, size }), className)}>
      <Icon className={cn("mb-3 w-8 h-8", status === 'loading' && "animate-spin opacity-80")} />
      {title && <h3 className="font-semibold text-stone-800 mb-1">{title}</h3>}
      {message && <p className="max-w-sm text-inherit opacity-80 leading-relaxed">{message}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

// Backward compatibility interfaces and wrappers (temporary)
export function UnifiedEmptyState({ title, description, actionLabel, onAction, className }: any) {
  return (
    <UnifiedFeedbackState
      status="empty"
      title={title}
      message={description}
      action={actionLabel && onAction ? <Button onClick={onAction}>{actionLabel}</Button> : null}
      className={className}
    />
  );
}
export function UnifiedLoadingState({ label, fullScreen, className }: any) {
  return <UnifiedFeedbackState status="loading" message={label} size={fullScreen ? "md" : "sm"} className={className} />;
}
export function UnifiedErrorState({ title, description, retryLabel, onRetry, className }: any) {
  return (
    <UnifiedFeedbackState
      status="error"
      title={title}
      message={description}
      action={retryLabel && onRetry ? <Button variant="outline" onClick={onRetry}>{retryLabel}</Button> : null}
      className={className}
    />
  );
}
