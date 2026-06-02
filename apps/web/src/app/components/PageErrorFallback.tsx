import { useState, useCallback, useRef, useEffect } from "react";
import { AlertTriangle, RefreshCw, LifeBuoy } from "lucide-react";
import { cn } from "@/lib/utils";

const MAX_RETRIES = 5;

/** Exponential backoff delays in ms: immediate, 1s, 2s, 4s, 8s */
const BACKOFF_DELAYS = [0, 1000, 2000, 4000, 8000] as const;

interface PageErrorFallbackProps {
  error: Error;
  resetError: () => void;
  className?: string;
}

export function PageErrorFallback({ error, resetError, className }: PageErrorFallbackProps) {
  const [retryCount, setRetryCount] = useState(0);
  const [isWaiting, setIsWaiting] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isMaxRetries = retryCount >= MAX_RETRIES;

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleRetry = useCallback(() => {
    if (isMaxRetries || isWaiting) return;

    const delay = BACKOFF_DELAYS[Math.min(retryCount, BACKOFF_DELAYS.length - 1)];

    if (delay === 0) {
      setRetryCount((c) => c + 1);
      resetError();
      return;
    }

    setIsWaiting(true);
    timerRef.current = setTimeout(() => {
      setIsWaiting(false);
      setRetryCount((c) => c + 1);
      resetError();
    }, delay);
  }, [retryCount, isMaxRetries, isWaiting, resetError]);

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center min-h-[320px] p-8 text-center",
        className,
      )}
    >
      <div className="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl border border-red-200 bg-red-50">
        <AlertTriangle className="h-7 w-7 text-red-500" />
      </div>

      <h2 className="text-lg font-semibold text-foreground mb-2 font-serif tracking-tight">
        Something went wrong
      </h2>

      <p className="max-w-md text-sm text-muted-foreground leading-relaxed mb-1">
        {error.message || "An unexpected error occurred while loading this page."}
      </p>

      {retryCount > 0 && !isMaxRetries && (
        <p className="text-xs text-muted-foreground/70 mb-4">
          Retry {retryCount} of {MAX_RETRIES}
          {isWaiting ? " -- waiting..." : ""}
        </p>
      )}

      {isMaxRetries ? (
        <div className="mt-4 space-y-3">
          <div className="inline-flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
            <LifeBuoy className="h-4 w-4" />
            Maximum retries reached. Please contact support.
          </div>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="block mx-auto text-sm text-primary hover:underline"
          >
            Reload page
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={handleRetry}
          disabled={isWaiting}
          className="mt-4 inline-flex items-center gap-2 rounded-xl border border-border/60 bg-background px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:border-primary/25 hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={cn("h-4 w-4", isWaiting && "animate-spin")} />
          {isWaiting ? "Retrying..." : "Try again"}
        </button>
      )}
    </div>
  );
}
