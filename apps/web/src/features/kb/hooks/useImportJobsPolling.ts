import { useCallback, useEffect, useRef } from 'react';

interface UseImportJobsPollingOptions {
  enabled?: boolean;
  intervalMs?: number;
  onTick: () => Promise<void> | void;
}

export function useImportJobsPolling(options: UseImportJobsPollingOptions) {
  const { enabled = true, intervalMs = 5000, onTick } = options;
  const timerRef = useRef<number | null>(null);

  const stop = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const start = useCallback(() => {
    stop();
    if (!enabled) {
      return;
    }

    void onTick();
    timerRef.current = window.setInterval(() => {
      void onTick();
    }, intervalMs);
  }, [enabled, intervalMs, onTick, stop]);

  useEffect(() => {
    start();
    return stop;
  }, [start, stop]);

  return { start, stop };
}
