/**
 * MarkdownRenderer Component
 *
 * Renders markdown content with GFM tables, code block highlighting,
 * and custom component overrides. Replaces TypingText per D-01.
 *
 * Features:
 * - react-markdown with remarkGfm (tables, strikethrough, task lists)
 * - rehypeHighlight for code block syntax highlighting
 * - Custom CodeBlock component for fenced code blocks
 * - External links open in new tab
 * - Responsive tables with horizontal scroll
 * - Typography per UI-SPEC: text-sm leading-relaxed, --font-sans
 *
 * Heavy deps (react-markdown, katex, highlight.js, mermaid) are dynamically
 * imported to keep them out of the main bundle chunk.
 */

import { lazy, Suspense, type ComponentProps } from 'react';
import { Skeleton } from '@/app/components/ui/skeleton';

// Dynamic import of the heavy markdown rendering internals
const MarkdownRendererInner = lazy(() =>
  import('./MarkdownRendererInner').then((m) => ({ default: m.MarkdownRendererInner }))
);

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

function MarkdownFallback({ className }: { className?: string }) {
  return (
    <div className={className}>
      <div className="space-y-3 p-4">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-20 w-full" />
      </div>
    </div>
  );
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <Suspense fallback={<MarkdownFallback className={className} />}>
      <MarkdownRendererInner content={content} className={className} />
    </Suspense>
  );
}
