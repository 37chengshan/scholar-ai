/**
 * Floating Annotation Toolbar
 *
 * Appears near text selection in the PDF viewer.
 * Shows color pickers for creating highlights.
 */

import { useEffect, useRef, useState } from 'react';
import { clsx } from 'clsx';
import { X } from 'lucide-react';

const HIGHLIGHT_COLORS = [
  { hex: '#FFEB3B', zhName: '黄色', enName: 'Yellow' },
  { hex: '#FF5722', zhName: '橙色', enName: 'Orange' },
  { hex: '#2196F3', zhName: '蓝色', enName: 'Blue' },
  { hex: '#4CAF50', zhName: '绿色', enName: 'Green' },
];

interface FloatingAnnotationToolbarProps {
  selectionRect: DOMRect;
  onHighlight: (color: string) => void;
  onDismiss: () => void;
  isZh: boolean;
}

export function FloatingAnnotationToolbar({
  selectionRect,
  onHighlight,
  onDismiss,
  isZh,
}: FloatingAnnotationToolbarProps) {
  const toolbarRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  useEffect(() => {
    const toolbarHeight = 40;
    const gap = 8;
    const toolbarWidth = 200;

    let top = selectionRect.top - toolbarHeight - gap;
    let below = false;

    // Boundary detection: if toolbar overflows viewport top, position below
    if (top < 0) {
      top = selectionRect.bottom + gap;
      below = true;
    }

    // Center horizontally relative to selection
    const selectionCenter = selectionRect.left + selectionRect.width / 2;
    let left = selectionCenter - toolbarWidth / 2;

    // Clamp to viewport edges
    left = Math.max(8, Math.min(left, window.innerWidth - toolbarWidth - 8));

    setPosition({ top, left });
  }, [selectionRect]);

  // Auto-dismiss when selection is cleared
  useEffect(() => {
    const handleSelectionChange = () => {
      const selection = window.getSelection();
      if (!selection || selection.toString().trim() === '') {
        onDismiss();
      }
    };

    document.addEventListener('selectionchange', handleSelectionChange);
    return () => document.removeEventListener('selectionchange', handleSelectionChange);
  }, [onDismiss]);

  return (
    <div
      ref={toolbarRef}
      data-testid="floating-annotation-toolbar"
      className="fixed z-50 flex items-center gap-1 rounded-lg border border-border/60 bg-background/95 px-2 py-1.5 shadow-lg backdrop-blur-sm"
      style={{ top: position.top, left: position.left }}
    >
      {HIGHLIGHT_COLORS.map((c) => (
        <button
          key={c.hex}
          onClick={() => onHighlight(c.hex)}
          data-testid={`floating-color-${c.zhName}`}
          className={clsx(
            'h-6 w-6 rounded-sm border border-border/40 transition-all',
            'hover:scale-110 hover:border-foreground/30',
          )}
          style={{ backgroundColor: c.hex }}
          title={isZh ? c.zhName : c.enName}
          aria-label={isZh ? `选择${c.zhName}高亮` : `Select ${c.enName} highlight`}
        />
      ))}
      <div className="mx-1 h-5 w-px bg-border/40" />
      <button
        onClick={onDismiss}
        className="flex h-6 w-6 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        aria-label={isZh ? '关闭' : 'Dismiss'}
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
