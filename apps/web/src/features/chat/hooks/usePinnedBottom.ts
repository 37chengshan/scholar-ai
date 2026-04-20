import { RefObject, useCallback, useEffect, useRef, useState } from 'react';

interface UsePinnedBottomOptions {
  containerRef: RefObject<HTMLElement>;
  anchorRef: RefObject<HTMLElement>;
  threshold?: number;
  streamFollowIntervalMs?: number;
}

type ScrollReason = 'message' | 'stream' | 'done';

interface UsePinnedBottomResult {
  isPinnedToBottom: boolean;
  maybeFollowBottom: (reason: ScrollReason) => void;
  alignToBottom: () => void;
}

export function usePinnedBottom({
  containerRef,
  anchorRef,
  threshold = 120,
  streamFollowIntervalMs = 120,
}: UsePinnedBottomOptions): UsePinnedBottomResult {
  const [isPinnedToBottom, setIsPinnedToBottom] = useState(true);
  const pinnedRef = useRef(true);
  const lastStreamFollowAtRef = useRef(0);

  const updatePinnedState = useCallback(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const distanceToBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    const nextPinned = distanceToBottom <= threshold;
    pinnedRef.current = nextPinned;
    setIsPinnedToBottom(nextPinned);
  }, [containerRef, threshold]);

  const scrollToBottom = useCallback((behavior: ScrollBehavior) => {
    anchorRef.current?.scrollIntoView({ behavior, block: 'end' });
  }, [anchorRef]);

  const alignToBottom = useCallback(() => {
    scrollToBottom('auto');
    pinnedRef.current = true;
    setIsPinnedToBottom(true);
  }, [scrollToBottom]);

  const maybeFollowBottom = useCallback((reason: ScrollReason) => {
    if (!pinnedRef.current && reason !== 'done') {
      return;
    }

    if (reason === 'stream') {
      const now = Date.now();
      if (now - lastStreamFollowAtRef.current < streamFollowIntervalMs) {
        return;
      }
      lastStreamFollowAtRef.current = now;
    }

    scrollToBottom('auto');
  }, [scrollToBottom, streamFollowIntervalMs]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    updatePinnedState();

    const handleScroll = () => {
      updatePinnedState();
    };

    container.addEventListener('scroll', handleScroll, { passive: true });

    return () => {
      container.removeEventListener('scroll', handleScroll);
    };
  }, [containerRef, updatePinnedState]);

  return {
    isPinnedToBottom,
    maybeFollowBottom,
    alignToBottom,
  };
}