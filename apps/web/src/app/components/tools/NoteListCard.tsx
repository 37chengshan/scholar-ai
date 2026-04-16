/**
 * NoteListCard Component
 *
 * Displays list_notes tool result as a list of notes.
 *
 * Part of Phase 28: Chat Frontend Enhancement
 */

import { useLanguage } from '../../contexts/LanguageContext';
import { Badge } from '../ui/badge';
import { Notebook } from 'lucide-react';

interface NoteListCardProps {
  result: {
    notes: Array<{
      id: string;
      title?: string;
      created_at: string;
      paper_ids?: string[];
    }>;
  };
}

export function NoteListCard({ result }: NoteListCardProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const notes = result.notes ?? [];

  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr);
    return date.toLocaleDateString(isZh ? 'zh-CN' : 'en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
      <div className="flex items-center gap-2 p-3 border-b border-border/50">
        <Notebook className="w-4 h-4 text-primary" />
        <span className="text-sm font-semibold">
          {isZh ? `笔记列表 (${notes.length})` : `Notes (${notes.length})`}
        </span>
      </div>
      <div className="divide-y divide-border/30">
        {notes.map((note) => (
          <div key={note.id} className="px-3 py-2.5 hover:bg-muted/30 transition-colors">
            <div className="text-sm font-medium truncate">
              {note.title ?? (isZh ? '无标题' : 'Untitled')}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-muted-foreground">{formatDate(note.created_at)}</span>
              {note.paper_ids && note.paper_ids.length > 0 && (
                <Badge variant="outline" className="text-xs">
                  {note.paper_ids.length} {isZh ? '篇论文' : 'papers'}
                </Badge>
              )}
            </div>
          </div>
        ))}
      </div>
      {notes.length === 0 && (
        <div className="px-3 py-4 text-center text-xs text-muted-foreground">
          {isZh ? '没有找到笔记' : 'No notes found'}
        </div>
      )}
    </div>
  );
}
