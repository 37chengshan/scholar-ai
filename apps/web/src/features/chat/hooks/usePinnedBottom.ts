import { RefObject, useCallback, useEffect, useRef, useState } from 'react';

interface UsePinnedBottomOptions {
  containerRef: RefObject<HTMLElement>;
  anchorRef: RefObject<HTMLElement>;
  threshold?: number;
  streamFollowIntervalMs?: number;
  smoothBehavior?: ScrollBehavior;
  /** Total items count when using virtualization; 0 = non-virtualized mode */
  virtualizedItemCount?: number;
}

type ScrollReason = 'message' | 'stream' | 'done';

interface UsePinnedBottomResult {
  isPinnedToBottom: boolean;
  maybeFollowBottom: (reason: ScrollReason) => void;
  alignToBottom: () => void;
  /** Report visible range from VirtualizedMessageList's onItemsRendered */
  reportVisibleRange: (startIndex: number, stopIndex: number) => void;
}

export function usePinnedBottom({
  containerRef,
  anchorRef,
  threshold = 120,
  streamFollowIntervalMs = 120,
  smoothBehavior = 'smooth',
  virtualizedItemCount = 0,
}: UsePinnedBottomOptions): UsePinnedBottomResult {
  const [isPinnedToBottom, setIsPinnedToBottom] = useState(true);
  const pinnedRef = useRef(true);
  const lastStreamFollowAtRef = useRef(0);
  const lastVisibleStopRef = useRef(0);
  const isVirtualized = virtualizedItemCount > 0;

  const updatePinnedState = useCallback(() => {
    if (isVirtualized) {
      // In virtualized mode, pinned state is driven by reportVisibleRange
      return;
    }
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const distanceToBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    const nextPinned = distanceToBottom <= threshold;
    pinnedRef.current = nextPinned;
    setIsPinnedToBottom(nextPinned);
  }, [containerRef, threshold, isVirtualized]);

  const scrollToBottom = useCallback((behavior: ScrollBehavior) => {
    if (isVirtualized) {
      // In virtualized mode, scrolling is handled externally via listRef.scrollToItem
      return;
    }
    anchorRef.current?.scrollIntoView({ behavior, block: 'end' });
  }, [anchorRef, isVirtualized]);

  const alignToBottom = useCallback(() => {
    if (isVirtualized) {
      pinnedRef.current = true;
      setIsPinnedToBottom(true);
      return;
    }
    scrollToBottom('auto');
    pinnedRef.current = true;
    setIsPinnedToBottom(true);
  }, [scrollToBottom, isVirtualized]);

  /**
   * Called by VirtualizedMessageList's onItemsRendered callback.
   * If the last visible item is near the end, consider it pinned.
   */
  const reportVisibleRange = useCallback((startIndex: number, stopIndex: number) => {
    if (!isVirtualized) {
      return;
    }
    lastVisibleStopRef.current = stopIndex;
    // Consider pinned if the last visible item is within 2 of the last item
    const nearEnd = stopIndex >= virtualizedItemCount - 2;
    pinnedRef.current = nearEnd;
    setIsPinnedToBottom(nearEnd);
  }, [isVirtualized, virtualizedItemCount]);

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

    if (isVirtualized) {
      // In virtualized mode, the caller (MessageFeed) handles scrollToItem
      // We just ensure pinned state is true
      pinnedRef.current = true;
      setIsPinnedToBottom(true);
      return;
    }

    const prefersReducedMotion = typeof window !== 'undefined'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    scrollToBottom(reason === 'stream' && !prefersReducedMotion ? smoothBehavior : 'auto');
  }, [scrollToBottom, smoothBehavior, streamFollowIntervalMs, isVirtualized]);

  useEffect(() => {
    if (isVirtualized) {
      return;
    }
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
  }, [containerRef, updatePinnedState, isVirtualized]);

  return {
    isPinnedToBottom,
    maybeFollowBottom,
    alignToBottom,
    reportVisibleRange,
  };
}
