/**
 * MergePreviewCard Component
 *
 * Displays merge_documents tool result with merged content preview.
 *
 * Part of Phase 28: Chat Frontend Enhancement
 */

import { useLanguage } from '../../contexts/LanguageContext';
import { Combine } from 'lucide-react';
import { MarkdownRenderer } from '../MarkdownRenderer';

interface MergePreviewCardProps {
  result: {
    merged_content: string;
    source_count?: number;
  };
}

export function MergePreviewCard({ result }: MergePreviewCardProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const sourceCount = result.source_count ?? 0;
  const content = result.merged_content ?? '';
  const preview = content.length > 200 ? content.slice(0, 200) + '...' : content;

  return (
    <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
      <div className="flex items-center gap-2 p-3 border-b border-border/50">
        <Combine className="w-4 h-4 text-primary" />
        <span className="text-sm font-semibold">
          {isZh ? `已合并 ${sourceCount} 个文档` : `Merged ${sourceCount} documents`}
        </span>
      </div>
      <div className="p-3">
        <div className="text-sm prose prose-sm max-w-none">
          <MarkdownRenderer content={preview} />
        </div>
      </div>
    </div>
  );
}
