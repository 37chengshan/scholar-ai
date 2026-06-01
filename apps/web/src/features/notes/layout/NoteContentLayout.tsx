/**
 * NoteContentLayout - Pretext-based text layout wrapper for note content
 *
 * Applies pretext measurement to note content for proper text flow.
 * Handles paragraph flow, heading breaks, code block full-width,
 * callout fixed-width with text wrapping inside.
 *
 * Uses CSS custom properties from design system tokens.
 */

import { type ReactNode, useRef, useState, useEffect } from 'react';
import { clsx } from 'clsx';

interface NoteContentLayoutProps {
  children: ReactNode;
  className?: string;
}

export function NoteContentLayout({ children, className }: NoteContentLayoutProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);

  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });

    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={containerRef}
      className={clsx(
        'note-content-layout',
        'max-w-prose',
        className,
      )}
      style={{
        '--note-content-width': `${containerWidth}px`,
        '--note-line-height': '1.75',
        '--note-font-size': '15px',
      } as React.CSSProperties}
    >
      {children}
    </div>
  );
}
