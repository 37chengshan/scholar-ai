/**
 * useReadKeyboard Hook
 *
 * Keyboard shortcuts for the Read workspace.
 * Only fires when focus is not on an input/textarea/contenteditable.
 */

import { useEffect } from 'react';

type ReadRightTab = 'notes' | 'annotations' | 'summary';

interface UseReadKeyboardOptions {
  goToPage: (page: number, reason?: 'toolbar' | 'thumbnail' | 'section' | 'citation' | 'annotation' | 'url') => void | Promise<void>;
  currentPage: number;
  totalPages: number | null;
  setScale: (updater: (prev: number) => number) => void;
  scale: number;
  setRightTab: (tab: ReadRightTab) => void;
  setIsPanelOpen: (open: boolean) => void;
  toggleFullscreen: () => void;
  isFullscreen: boolean;
  dismissFloating?: () => void;
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA') return true;
  if (target.isContentEditable) return true;
  // TipTap editors use ProseMirror class
  if (target.closest('.ProseMirror')) return true;
  return false;
}

export function useReadKeyboard({
  goToPage,
  currentPage,
  totalPages,
  setScale,
  setRightTab,
  setIsPanelOpen,
  toggleFullscreen,
  isFullscreen,
  dismissFloating,
}: UseReadKeyboardOptions) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (isEditableTarget(e.target)) return;

      const upper = totalPages || Number.MAX_SAFE_INTEGER;

      switch (e.key) {
        case 'j': {
          e.preventDefault();
          const next = Math.min(currentPage + 1, upper);
          goToPage(next);
          break;
        }
        case 'k': {
          e.preventDefault();
          const prev = Math.max(1, currentPage - 1);
          goToPage(prev);
          break;
        }
        case ']': {
          e.preventDefault();
          setScale((s) => Math.min(2, s + 0.1));
          break;
        }
        case '[': {
          e.preventDefault();
          setScale((s) => Math.max(0.5, s - 0.1));
          break;
        }
        case 'n': {
          e.preventDefault();
          setRightTab('notes');
          setIsPanelOpen(true);
          break;
        }
        case 'Escape': {
          if (isFullscreen) {
            toggleFullscreen();
          } else if (dismissFloating) {
            dismissFloating();
          }
          break;
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [
    goToPage,
    currentPage,
    totalPages,
    setScale,
    setRightTab,
    setIsPanelOpen,
    toggleFullscreen,
    isFullscreen,
    dismissFloating,
  ]);
}
