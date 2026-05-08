import { useLanguage } from '@/app/contexts/LanguageContext';
import type { CitationItem } from '@/features/chat/components/workspaceTypes';

interface CitationInlineProps {
  citations: CitationItem[];
  onJump: (citation: CitationItem) => void;
}

export function CitationInline({ citations, onJump }: CitationInlineProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  if (citations.length === 0) {
    return null;
  }

  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {citations.map((citation, idx) => (
        <button
          key={
            citation.source_id
            || citation.source_chunk_id
            || citation.chunk_id
            || `${citation.paper_id}-${citation.page_num || citation.page || idx}-${idx}`
          }
          type="button"
          onClick={() => onJump(citation)}
          className="inline-flex items-center rounded-full border border-border/70 bg-background px-2 py-1 text-[11px] text-foreground/80 hover:border-primary/40 hover:text-primary"
        >
          [{idx + 1}] {isZh ? `第 ${citation.page_num || citation.page || 1} 页` : `Page ${citation.page_num || citation.page || 1}`}
        </button>
      ))}
    </div>
  );
}
