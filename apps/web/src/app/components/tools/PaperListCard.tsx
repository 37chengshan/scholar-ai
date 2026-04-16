/**
 * PaperListCard Component
 *
 * Displays list_papers tool result as a compact paper list.
 *
 * Part of Phase 28: Chat Frontend Enhancement
 */

import { useState } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';
import { Badge } from '../ui/badge';
import { List, ChevronDown, ChevronUp } from 'lucide-react';

interface PaperListCardProps {
  result: {
    papers: Array<{
      id: string;
      title: string;
      authors?: string[];
      year?: number;
    }>;
    total?: number;
  };
}

const MAX_VISIBLE = 5;

export function PaperListCard({ result }: PaperListCardProps) {
  const [showAll, setShowAll] = useState(false);
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const papers = result.papers ?? [];
  const total = result.total ?? papers.length;
  const visiblePapers = showAll ? papers : papers.slice(0, MAX_VISIBLE);
  const hasMore = papers.length > MAX_VISIBLE;

  const formatAuthors = (authors?: string[]): string => {
    if (!authors || authors.length === 0) return isZh ? '未知作者' : 'Unknown authors';
    if (authors.length === 1) return authors[0];
    return `${authors[0]} ${isZh ? '等' : 'et al'}`;
  };

  return (
    <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
      <div className="flex items-center gap-2 p-3 border-b border-border/50">
        <List className="w-4 h-4 text-primary" />
        <span className="text-sm font-semibold">
          {isZh ? `找到 ${total} 篇论文` : `Found ${total} papers`}
        </span>
      </div>
      <div className="divide-y divide-border/30">
        {visiblePapers.map((paper, idx) => (
          <div key={paper.id ?? idx} className="px-3 py-2 hover:bg-muted/30 transition-colors">
            <div className="text-sm font-medium truncate">{paper.title}</div>
            <div className="flex items-center gap-2 mt-1">
              {paper.year && (
                <Badge variant="outline" className="text-xs">
                  {paper.year}
                </Badge>
              )}
              <span className="text-xs text-muted-foreground truncate">
                {formatAuthors(paper.authors)}
              </span>
            </div>
          </div>
        ))}
      </div>
      {hasMore && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="w-full flex items-center justify-center gap-1 py-2 text-xs text-muted-foreground hover:bg-muted/50 transition-colors"
        >
          {showAll ? (
            <>
              <ChevronUp className="w-3 h-3" />
              {isZh ? '收起' : 'Show less'}
            </>
          ) : (
            <>
              <ChevronDown className="w-3 h-3" />
              {isZh ? `显示全部 ${papers.length} 篇` : `Show all ${papers.length}`}
            </>
          )}
        </button>
      )}
    </div>
  );
}
