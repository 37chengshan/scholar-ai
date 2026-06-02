/**
 * MarkdownPreview - Renders markdown content in preview mode
 *
 * Used by ComposerInput when the user toggles preview mode.
 * Wraps MarkdownRenderer with a preview-specific container.
 */

import { MarkdownRenderer } from '@/app/components/MarkdownRenderer';

interface MarkdownPreviewProps {
  content: string;
  isZh: boolean;
}

export function MarkdownPreview({ content, isZh }: MarkdownPreviewProps) {
  if (!content.trim()) {
    return (
      <div className="min-h-[2.75rem] flex-1 flex items-center text-sm text-muted-foreground italic">
        {isZh ? ' nothing to preview' : 'Nothing to preview'}
      </div>
    );
  }

  return (
    <div className="min-h-[2.75rem] max-h-[12.5rem] flex-1 overflow-y-auto prose prose-sm dark:prose-invert max-w-none">
      <MarkdownRenderer content={content} />
    </div>
  );
}
