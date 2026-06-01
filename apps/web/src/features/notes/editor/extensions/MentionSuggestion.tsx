/**
 * MentionSuggestion - Popover for @mention suggestions
 *
 * Renders a filtered list of mentionable items (papers, chunks, evidence)
 * when the user types @ in the editor. Supports keyboard navigation.
 */

import { useCallback, useEffect, useState } from 'react';
import type { SuggestionProps } from '@tiptap/suggestion';
import { clsx } from 'clsx';
import { FileText, Layers, Quote, Loader2 } from 'lucide-react';

import type { MentionSuggestionItem } from './MentionExtension';

interface MentionSuggestionProps extends SuggestionProps<MentionSuggestionItem> {
  items: MentionSuggestionItem[];
  loading?: boolean;
}

const TYPE_ICONS: Record<string, typeof FileText> = {
  paper: FileText,
  chunk: Layers,
  evidence: Quote,
};

export function MentionSuggestionList({
  items,
  loading,
  command,
}: Pick<MentionSuggestionProps, 'items' | 'loading' | 'command'>) {
  const [selectedIndex, setSelectedIndex] = useState(0);

  useEffect(() => {
    setSelectedIndex(0);
  }, [items]);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === 'ArrowUp') {
        event.preventDefault();
        setSelectedIndex((prev) => (prev + items.length - 1) % items.length);
        return true;
      }
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % items.length);
        return true;
      }
      if (event.key === 'Enter') {
        event.preventDefault();
        const item = items[selectedIndex];
        if (item) {
          command({ id: item.id, label: item.label, type: item.type });
        }
        return true;
      }
      return false;
    },
    [command, items, selectedIndex],
  );

  useEffect(() => {
    const handler = (event: KeyboardEvent) => handleKeyDown(event);
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [handleKeyDown]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-border bg-background p-3 shadow-lg">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        <span className="text-xs text-muted-foreground">搜索中...</span>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-background p-3 shadow-lg">
        <p className="text-xs text-muted-foreground">无匹配结果</p>
      </div>
    );
  }

  return (
    <div className="max-h-[240px] overflow-auto rounded-lg border border-border bg-background py-1 shadow-lg">
      {items.map((item, index) => {
        const Icon = TYPE_ICONS[item.type] || FileText;
        return (
          <button
            key={`${item.type}-${item.id}`}
            type="button"
            className={clsx(
              'flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors',
              index === selectedIndex
                ? 'bg-primary/10 text-primary'
                : 'text-foreground hover:bg-muted/50',
            )}
            onClick={() => command({ id: item.id, label: item.label, type: item.type })}
          >
            <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <span className="flex-1 truncate">{item.label}</span>
            <span className="shrink-0 text-[10px] text-muted-foreground">
              {item.type === 'paper' ? '论文' : item.type === 'chunk' ? '段落' : '证据'}
            </span>
          </button>
        );
      })}
    </div>
  );
}
