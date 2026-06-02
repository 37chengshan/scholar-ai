/**
 * useMessageKeyboardNav - j/k keyboard navigation between chat messages
 *
 * Follows the same pattern as Read page keyboard navigation.
 * j = next message, k = previous message
 * Focus moves to the message element with visual indicator.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

interface UseMessageKeyboardNavOptions {
  messageCount: number;
  containerRef: React.RefObject<HTMLElement | null>;
  enabled?: boolean;
}

interface UseMessageKeyboardNavResult {
  focusedIndex: number;
  setFocusedIndex: (index: number) => void;
}

const MESSAGE_SELECTOR = '[data-message-id]';

export function useMessageKeyboardNav({
  messageCount,
  containerRef,
  enabled = true,
}: UseMessageKeyboardNavOptions): UseMessageKeyboardNavResult {
  const [focusedIndex, setFocusedIndex] = useState(-1);

  const handleMessageFocus = useCallback((index: number) => {
    if (index < 0 || index >= messageCount) return;

    setFocusedIndex(index);

    const container = containerRef.current;
    if (!container) return;

    const messages = container.querySelectorAll(MESSAGE_SELECTOR);
    const target = messages[index];
    if (target instanceof HTMLElement) {
      target.focus({ preventScroll: false });
      target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [messageCount, containerRef]);

  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't intercept when user is typing in an input/textarea
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT'
        || target.tagName === 'TEXTAREA'
        || target.isContentEditable
        || target.closest('[role="menu"]')
      ) {
        return;
      }

      if (event.key === 'j') {
        event.preventDefault();
        handleMessageFocus(Math.min(focusedIndex + 1, messageCount - 1));
      } else if (event.key === 'k') {
        event.preventDefault();
        handleMessageFocus(Math.max(focusedIndex - 1, 0));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enabled, focusedIndex, messageCount, handleMessageFocus]);

  // Reset focus index when message count changes
  useEffect(() => {
    if (messageCount === 0) {
      setFocusedIndex(-1);
    }
  }, [messageCount]);

  return { focusedIndex, setFocusedIndex };
}
