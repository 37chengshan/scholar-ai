/**
 * EvidenceTextLayout - Pretext-based layout for evidence quotes
 *
 * Implements shrinkwrap: long evidence quotes (> 200 chars)
 * auto-collapse to 3 lines with "Show more" expansion.
 * Text wraps around evidence type indicators.
 */

import { useCallback, useMemo, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { clsx } from 'clsx';

import { usePretextMeasure } from './usePretextMeasure';

interface EvidenceTextLayoutProps {
  text: string;
  className?: string;
  maxCollapsedLines?: number;
  lineHeight?: number;
}

const COLLAPSE_THRESHOLD = 200;

export function EvidenceTextLayout({
  text,
  className,
  maxCollapsedLines = 3,
  lineHeight = 22,
}: EvidenceTextLayoutProps) {
  const [expanded, setExpanded] = useState(false);

  const isLong = text.length > COLLAPSE_THRESHOLD;

  const { height: fullHeight } = usePretextMeasure({
    text,
    width: 560,
    lineHeight,
  });

  const collapsedHeight = maxCollapsedLines * lineHeight;
  const shouldCollapse = isLong && !expanded && fullHeight > collapsedHeight;

  const handleToggle = useCallback(() => {
    setExpanded((prev) => !prev);
  }, []);

  return (
    <div className={clsx('evidence-text-layout', className)}>
      <div
        className={clsx(
          'relative overflow-hidden transition-all duration-200',
          shouldCollapse && 'cursor-pointer',
        )}
        style={{
          maxHeight: shouldCollapse ? `${collapsedHeight}px` : undefined,
        }}
        onClick={shouldCollapse ? handleToggle : undefined}
        onKeyDown={shouldCollapse ? (e) => { if (e.key === 'Enter') handleToggle(); } : undefined}
        role={shouldCollapse ? 'button' : undefined}
        tabIndex={shouldCollapse ? 0 : undefined}
      >
        <p className="text-sm leading-relaxed text-foreground/90">
          {text}
        </p>

        {shouldCollapse && (
          <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-background to-transparent" />
        )}
      </div>

      {isLong && (
        <button
          type="button"
          className="mt-1 flex items-center gap-1 text-[11px] text-primary hover:text-primary/80"
          onClick={handleToggle}
        >
          {expanded ? (
            <>
              <ChevronUp className="h-3 w-3" />
              收起
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3" />
              展开全部
            </>
          )}
        </button>
      )}
    </div>
  );
}
