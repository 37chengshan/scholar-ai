/**
 * CitationPanel - Interactive citation display with paper grouping
 *
 * Features:
 * - Groups citations by paper_id
 * - Click to navigate to Read page (with URL allowlist validation)
 * - Filter citations by paper name
 * - Collapsible groups
 */

import { useState, useMemo } from 'react';
import { Search, X } from 'lucide-react';
import { clsx } from 'clsx';
import { CitationsPanel as BaseCitationsPanel } from '@/app/components/CitationsPanel';
import type { CitationItem } from '@/features/chat/components/workspaceTypes';
import { CitationGroup } from './CitationGroup';
import { useCitationNavigation } from './useCitationNavigation';

interface CitationPanelProps {
  visible: boolean;
  citations: CitationItem[];
  isZh?: boolean;
  onCitationClick?: (citation: CitationItem) => void;
}

/**
 * Group citations by paper_id, preserving order.
 */
function groupByPaper(citations: CitationItem[]): Map<string, {
  title: string;
  citations: CitationItem[];
}> {
  const groups = new Map<string, { title: string; citations: CitationItem[] }>();

  for (const citation of citations) {
    const key = citation.paper_id || 'unknown';
    const existing = groups.get(key);
    if (existing) {
      existing.citations.push(citation);
    } else {
      groups.set(key, {
        title: citation.title || key,
        citations: [citation],
      });
    }
  }

  return groups;
}

export function CitationPanel({
  visible,
  citations,
  isZh = true,
  onCitationClick,
}: CitationPanelProps) {
  const [filterText, setFilterText] = useState('');
  const { navigateToCitation } = useCitationNavigation({ onCitationClick });

  const filteredCitations = useMemo(() => {
    if (!filterText.trim()) return citations;
    const query = filterText.toLowerCase();
    return citations.filter(
      (c) =>
        (c.title || '').toLowerCase().includes(query) ||
        (c.paper_id || '').toLowerCase().includes(query),
    );
  }, [citations, filterText]);

  const groups = useMemo(() => groupByPaper(filteredCitations), [filteredCitations]);
  const hasMultiplePapers = groups.size > 1;

  if (!visible || citations.length === 0) {
    return null;
  }

  // For single-paper or few citations, use the base panel directly
  if (!hasMultiplePapers && citations.length <= 5) {
    return (
      <BaseCitationsPanel
        citations={citations.map((citation) => ({
          paper_id: citation.paper_id,
          title: citation.title,
          authors: citation.authors || [],
          year: citation.year || 0,
          page: citation.page_num || citation.page || 1,
          snippet: citation.text_preview || citation.snippet || '',
          score: citation.score || 0,
          content_type: citation.content_type || 'text',
          source_chunk_id: citation.source_chunk_id || citation.source_id || citation.chunk_id,
          source_id: citation.source_chunk_id || citation.source_id || citation.chunk_id,
          chunk_id: citation.chunk_id || citation.source_id || citation.source_chunk_id,
          citation_jump_url: citation.citation_jump_url,
        }))}
      />
    );
  }

  // Multi-paper grouped view
  return (
    <div className="border-t border-border/40 pt-3 mt-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-xs font-semibold text-muted-foreground">
          {isZh ? `${citations.length} 个引用来源` : `${citations.length} source${citations.length > 1 ? 's' : ''}`}
        </h4>
        <span className="text-[10px] text-muted-foreground">
          {isZh ? `${groups.size} 篇论文` : `${groups.size} papers`}
        </span>
      </div>

      {/* Filter input */}
      {citations.length > 3 && (
        <div className="relative mb-2">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
          <input
            type="text"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            placeholder={isZh ? '搜索论文...' : 'Search papers...'}
            className="w-full pl-7 pr-7 py-1.5 text-xs bg-muted/30 border border-border/40 rounded-lg outline-none focus:border-primary/30 focus:ring-1 focus:ring-primary/10 transition-colors"
          />
          {filterText && (
            <button
              type="button"
              onClick={() => setFilterText('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      )}

      {/* Grouped citations */}
      <div className="space-y-2">
        {Array.from(groups.entries()).map(([paperId, group]) => (
          <CitationGroup
            key={paperId}
            paperId={paperId}
            title={group.title}
            citations={group.citations}
            isZh={isZh}
            onNavigate={navigateToCitation}
          />
        ))}
      </div>

      {filteredCitations.length === 0 && filterText && (
        <p className="text-xs text-muted-foreground text-center py-2">
          {isZh ? '未找到匹配的引用' : 'No matching citations'}
        </p>
      )}
    </div>
  );
}
