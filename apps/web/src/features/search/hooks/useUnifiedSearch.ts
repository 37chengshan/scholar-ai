import { useMemo } from 'react';
import { useSearch } from '@/hooks/useSearch';

interface UseUnifiedSearchOptions {
  sortBy: 'relevance' | 'date';
  initialQuery: string;
  initialPage: number;
}

export function useUnifiedSearch(options: UseUnifiedSearchOptions) {
  const { sortBy, initialQuery, initialPage } = options;

  const filters = useMemo(() => ({ sortBy }), [sortBy]);

  return useSearch({
    debounceMs: 300,
    filters,
    initialQuery,
    initialPage,
  });
}
