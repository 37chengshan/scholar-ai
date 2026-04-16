/**
 * SearchResultCard Component
 *
 * Displays rag_search and external_search tool results.
 * Supports 'rag' and 'external' variants.
 *
 * Part of Phase 28: Chat Frontend Enhancement
 */

import { useLanguage } from '../../contexts/LanguageContext';
import { Badge } from '../ui/badge';
import { Search, ExternalLink } from 'lucide-react';
import { clsx } from 'clsx';

interface SearchResult {
  title: string;
  score?: number;
  source?: string;
  snippet?: string;
}

interface SearchResultCardProps {
  result: {
    results: SearchResult[];
    query?: string;
  };
  variant?: 'rag' | 'external';
}

function getScoreColor(score: number): string {
  if (score > 0.8) return 'bg-green-100 text-green-700';
  if (score >= 0.6) return 'bg-yellow-100 text-yellow-700';
  return 'bg-muted text-muted-foreground';
}

function getScoreBadge(score: number | undefined, isZh: boolean): string | null {
  if (score === undefined) return null;
  const pct = Math.round(score * 100);
  return `${pct}%`;
}

export function SearchResultCard({ result, variant = 'rag' }: SearchResultCardProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const results = result.results ?? [];
  const query = result.query;

  return (
    <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
      <div className="flex items-center gap-2 p-3 border-b border-border/50">
        <Search className="w-4 h-4 text-primary" />
        <span className="text-sm font-semibold">
          {isZh ? '搜索结果' : 'Search results'}
        </span>
        {query && (
          <span className="text-xs text-muted-foreground truncate">
            — {query}
          </span>
        )}
      </div>
      <div className="divide-y divide-border/30">
        {results.map((r, idx) => (
          <div key={idx} className="px-3 py-2.5 hover:bg-muted/30 transition-colors">
            <div className="flex items-start justify-between gap-2">
              <div className="text-sm font-medium flex-1 truncate">{r.title}</div>
              <div className="flex items-center gap-1 flex-shrink-0">
                {variant === 'rag' && r.score !== undefined && (
                  <Badge className={clsx('text-xs', getScoreColor(r.score))}>
                    {getScoreBadge(r.score, isZh)}
                  </Badge>
                )}
                {variant === 'external' && r.source && (
                  <Badge variant="outline" className="text-xs">
                    {r.source}
                  </Badge>
                )}
              </div>
            </div>
            {r.snippet && (
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                {r.snippet}
              </p>
            )}
          </div>
        ))}
      </div>
      {results.length === 0 && (
        <div className="px-3 py-4 text-center text-xs text-muted-foreground">
          {isZh ? '没有找到结果' : 'No results found'}
        </div>
      )}
    </div>
  );
}


