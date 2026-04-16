/**
 * NoteDetailCard Component
 *
 * Displays read_note tool result with full content via MarkdownRenderer.
 *
 * Part of Phase 28: Chat Frontend Enhancement
 */

import { useLanguage } from '../../contexts/LanguageContext';
import { Notebook } from 'lucide-react';
import { MarkdownRenderer } from '../MarkdownRenderer';

interface NoteDetailCardProps {
  result: {
    note_id: string;
    title?: string;
    content: string;
    created_at: string;
  };
}

export function NoteDetailCard({ result }: NoteDetailCardProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const title = result.title ?? (isZh ? '无标题' : 'Untitled');
  const content = result.content ?? '';

  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr);
    return date.toLocaleDateString(isZh ? 'zh-CN' : 'en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
      <div className="p-3 border-b border-border/50">
        <div className="flex items-center gap-2">
          <Notebook className="w-4 h-4 text-primary" />
          <h4 className="text-sm font-semibold">{title}</h4>
        </div>
        <div className="text-xs text-muted-foreground mt-1">
          {isZh ? '创建于' : 'Created'} {formatDate(result.created_at)}
        </div>
      </div>
      <div className="p-3">
        {content ? (
          <div className="text-sm prose prose-sm max-w-none">
            <MarkdownRenderer content={content} />
          </div>
        ) : (
          <p className="text-xs text-muted-foreground italic">
            {isZh ? '笔记内容为空' : 'Note content is empty'}
          </p>
        )}
      </div>
    </div>
  );
}
