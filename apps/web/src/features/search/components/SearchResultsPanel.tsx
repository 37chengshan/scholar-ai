import { motion } from 'motion/react';
import { Loader2 } from 'lucide-react';
import { SearchResultCard } from '@/app/components/SearchResultCard';
import { AuthorResultCard } from '@/app/components/AuthorResultCard';
import { NoSearchResultsState } from '@/app/components/EmptyState';
import { SearchResults } from '@/hooks/useSearch';
import { AuthorSearchResult } from '@/services/searchApi';

interface SearchResultsPanelProps {
  activeSource: string;
  query: string;
  loading: boolean;
  isInitialLoading: boolean;
  isPageFetching: boolean;
  error: string | null;
  results: SearchResults | null;
  authorResults: AuthorSearchResult[];
  authorLoading: boolean;
  labels: {
    searching: string;
    startTyping: string;
    authorResults: string;
    yourLibrary: string;
    externalSources: string;
  };
  onViewPaper: (paperId: string) => void;
  onAddToLibrary: (result: any) => void;
  onAuthorClick: (author: AuthorSearchResult) => void;
}

export function SearchResultsPanel({
  activeSource,
  query,
  loading,
  isInitialLoading,
  isPageFetching,
  error,
  results,
  authorResults,
  authorLoading,
  labels,
  onViewPaper,
  onAddToLibrary,
  onAuthorClick,
}: SearchResultsPanelProps) {
  if (isInitialLoading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="search-initial-loading">
        <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
          {labels.searching}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-sm text-red-500">{error}</div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
          {labels.startTyping}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="search-results-panel">
      {loading && isPageFetching && (
        <div
          className="flex items-center gap-2 text-xs text-muted-foreground"
          data-testid="search-page-loading"
          aria-live="polite"
        >
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          {labels.searching}
        </div>
      )}

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="space-y-8"
      >
      {activeSource === 'authors' && (
        <div>
          <h2 className="font-semibold mb-4 text-lg">
            {labels.authorResults} ({authorResults.length})
          </h2>
          {authorLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                {labels.searching}
              </div>
            </div>
          ) : authorResults.length > 0 ? (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
              {authorResults.map((author) => (
                <AuthorResultCard key={author.authorId} author={author} onClick={onAuthorClick} />
              ))}
            </div>
          ) : (
            <NoSearchResultsState query={query} />
          )}
        </div>
      )}

      {activeSource !== 'authors' && results.internal.length > 0 && (
        <div>
          <h2 className="font-semibold mb-4 text-lg">
            {labels.yourLibrary} ({results.internal.length})
          </h2>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            {results.internal.map((result) => (
              <SearchResultCard
                key={result.id}
                result={{ ...result, source: 'internal', paperId: result.id }}
                onViewPaper={onViewPaper}
              />
            ))}
          </div>
        </div>
      )}

      {activeSource !== 'authors' && results.external.length > 0 && (
        <div>
          <h2 className="font-semibold mb-4 text-lg">
            {labels.externalSources} ({results.external.length})
          </h2>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            {results.external.map((result, index) => (
              <SearchResultCard key={`${result.source}-${result.id}-${index}`} result={result} onAddToLibrary={onAddToLibrary} />
            ))}
          </div>
        </div>
      )}

      {activeSource !== 'authors' && results.internal.length === 0 && results.external.length === 0 && (
        <NoSearchResultsState query={query} />
      )}
      </motion.div>
    </div>
  );
}
