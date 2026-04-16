/**
 * NotePreviewCard Component
 *
 * Displays create_note / update_note tool result with content preview.
 *
 * Part of Phase 28: Chat Frontend Enhancement
 */

import { useLanguage } from '../../contexts/LanguageContext';
import { Badge } from '../ui/badge';
import { FilePlus, ExternalLink } from 'lucide-react';

interface NotePreviewCardProps {
  result: {
    note_id: string;
    title?: string;
    content?: string;
    updated?: boolean;
  };
  tool: string;
}

export function NotePreviewCard({ result, tool }: NotePreviewCardProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const isUpdate = tool === 'update_note' || result.updated;
  const title = result.title ?? (isZh ? '无标题' : 'Untitled');
  const content = result.content ?? '';
  const preview = content.length > 100 ? content.slice(0, 100) + '...' : content;

  return (
    <div className="flex items-start gap-3 p-3 rounded-lg border border-border/50 bg-card">
      <FilePlus className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">
            {isUpdate
              ? isZh
                ? '笔记已更新'
                : 'Note updated'
              : isZh
                ? '笔记已创建'
                : 'Note created'}
          </span>
          {isUpdate && (
            <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
              {isZh ? '已更新' : 'Updated'}
            </Badge>
          )}
        </div>
        {title !== (isZh ? '无标题' : 'Untitled') && (
          <div className="text-xs font-medium mt-0.5">{title}</div>
        )}
        {preview && (
          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{preview}</p>
        )}
        <a
          href={`/notes/${result.note_id}`}
          className="inline-flex items-center gap-1 text-xs text-primary mt-2 hover:underline"
        >
          <ExternalLink className="w-3 h-3" />
          {isZh ? '查看笔记' : 'View note'}
        </a>
      </div>
    </div>
  );
}
