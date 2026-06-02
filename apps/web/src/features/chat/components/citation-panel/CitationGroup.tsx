/**
 * CitationGroup - Groups citations by paper with collapsible sections
 *
 * Each paper group shows the paper title and a count badge.
 * Individual citations within a group are listed with snippets.
 */

import { useState } from 'react';
import { ChevronDown, ChevronRight, FileText, ExternalLink } from 'lucide-react';
import { clsx } from 'clsx';
import type { CitationItem } from '@/features/chat/components/workspaceTypes';

interface CitationGroupProps {
  paperId: string;
  title: string;
  citations: CitationItem[];
  isZh: boolean;
  onNavigate: (citation: CitationItem) => void;
}

export function CitationGroup({
  paperId,
  title,
  citations,
  isZh,
  onNavigate,
}: CitationGroupProps) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="border-l-2 border-border/40 pl-2">
      {/* Group header */}
      <button
        type="button"
        onClick={() => setExpanded(v => !v)}
        className="flex items-center gap-1.5 w-full text-left py-1 group"
      >
        {expanded
          ? <ChevronDown className="w-3 h-3 text-muted-foreground" />
          : <ChevronRight className="w-3 h-3 text-muted-foreground" />
        }
        <FileText className="w-3 h-3 text-muted-foreground flex-shrink-0" />
        <span className="text-xs font-medium text-foreground/80 truncate flex-1">
          {title || paperId}
        </span>
        <span className="text-[10px] text-muted-foreground bg-muted/50 rounded-full px-1.5 py-0.5">
          {citations.length}
        </span>
      </button>

      {/* Citation items */}
      {expanded && (
        <div className="ml-4 space-y-1">
          {citations.map((citation, index) => {
            const pageNum = citation.page_num || citation.page;
            const snippet = citation.text_preview || citation.snippet || '';

            return (
              <button
                key={citation.source_chunk_id || citation.source_id || `${paperId}-${index}`}
                type="button"
                onClick={() => onNavigate(citation)}
                className="w-full text-left px-2 py-1.5 rounded-md text-xs hover:bg-muted/50 transition-colors group/item"
              >
                <div className="flex items-start gap-1.5">
                  <span className="text-[10px] text-muted-foreground tabular-nums mt-0.5 flex-shrink-0">
                    {pageNum ? `p.${pageNum}` : `#${index + 1}`}
                  </span>
                  <div className="flex-1 min-w-0">
                    {snippet && (
                      <p className="text-[11px] text-foreground/70 line-clamp-2 leading-relaxed">
                        {snippet}
                      </p>
                    )}
                  </div>
                  <ExternalLink className="w-3 h-3 text-muted-foreground opacity-0 group-hover/item:opacity-100 transition-opacity flex-shrink-0 mt-0.5" />
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
