import { useMemo } from 'react';
import { useSearch } from '@/hooks/useSearch';

interface UseUnifiedSearchOptions {
  sortBy: 'relevance' | 'date';
  activeSource: string;
  initialQuery: string;
  initialPage: number;
}

export function useUnifiedSearch(options: UseUnifiedSearchOptions) {
  const { sortBy, activeSource, initialQuery, initialPage } = options;

  const filters = useMemo(() => ({
    sortBy,
    sources:
      activeSource === 'arxiv'
        ? ['arxiv']
        : activeSource === 'semantic_scholar' || activeSource === 's2'
          ? ['semantic_scholar']
          : undefined,
  }), [activeSource, sortBy]);

  const search = useSearch({
    debounceMs: 300,
    filters,
    initialQuery,
    initialPage,
  });

  return search;
}
