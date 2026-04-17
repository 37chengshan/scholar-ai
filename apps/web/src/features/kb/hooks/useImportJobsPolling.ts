import { useCallback, useEffect, useRef } from 'react';
import { trackImportEvent } from '@/lib/observability/telemetry';

interface UseImportJobsPollingOptions {
  enabled?: boolean;
  intervalMs?: number;
  pauseWhenHidden?: boolean;
  onTick: () => Promise<void> | void;
}

export function useImportJobsPolling(options: UseImportJobsPollingOptions) {
  const {
    enabled = true,
    intervalMs = 5000,
    pauseWhenHidden = true,
    onTick,
  } = options;
  const timerRef = useRef<number | null>(null);

  const canPoll = useCallback(() => {
    if (!enabled) {
      return false;
    }
    if (!pauseWhenHidden) {
      return true;
    }
    return document.visibilityState === 'visible';
  }, [enabled, pauseWhenHidden]);

  const stop = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
      trackImportEvent({ event: 'polling_stopped' });
    }
  }, []);

  const start = useCallback(() => {
    stop();
    if (!canPoll()) {
      trackImportEvent({ event: 'polling_skipped' });
      return;
    }

    trackImportEvent({ event: 'polling_started', intervalMs });
    void onTick();
    timerRef.current = window.setInterval(() => {
      if (!canPoll()) {
        stop();
        return;
      }
      trackImportEvent({ event: 'polling_tick' });
      void onTick();
    }, intervalMs);
  }, [canPoll, intervalMs, onTick, stop]);

  const restartOnVisibilityChange = useCallback(() => {
    if (canPoll()) {
      start();
      return;
    }
    stop();
  }, [canPoll, start, stop]);

  useEffect(() => {
    start();
    if (pauseWhenHidden) {
      document.addEventListener('visibilitychange', restartOnVisibilityChange);
    }

    return stop;
  }, [pauseWhenHidden, restartOnVisibilityChange, start, stop]);

  useEffect(() => () => {
    if (pauseWhenHidden) {
      document.removeEventListener('visibilitychange', restartOnVisibilityChange);
    }
  }, [pauseWhenHidden, restartOnVisibilityChange]);

  return { start, stop };
}
