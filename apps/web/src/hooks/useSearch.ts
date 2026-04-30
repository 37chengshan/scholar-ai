/**
 * useSearch Hook
 *
 * Search state management with 300ms debounce (D-11)
 *
 * Features:
 * - Debounced search query (300ms delay)
 * - Unified search across internal + external sources
 * - Loading and error states
 * - Pagination support (page navigation)
 * - Filter support (year range, sources, sort)
 * - URL state synchronization support (initialQuery, initialPage)
 */

import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, useEffect, useMemo, useCallback } from 'react';
import * as searchApi from '@/services/searchApi';

export interface SearchResult {
  id: string;
  title: string;
  authors?: string[];
  abstract?: string;
  year?: number;
  source: 'internal' | 'arxiv' | 's2' | 'semantic_scholar';
  paperId?: string;
  externalId?: string;
  pdfUrl?: string;
  citations?: number;
  // canonical ExternalPaper fields (WP0/WP1)
  arxivId?: string;
  s2PaperId?: string;
  doi?: string;
  venue?: string;
  openAccess?: boolean;
  fieldsOfStudy?: string[];
  availability?: 'metadata_only' | 'pdf_available' | 'pdf_unavailable';
  libraryStatus?: 'not_imported' | 'importing' | 'imported_metadata_only' | 'imported_fulltext_ready';
}

export interface SearchResults {
  internal: SearchResult[];
  external: SearchResult[];
  total: number;
  metadata?: SearchPlannerMetadata;
}

export interface SearchPlannerMetadata {
  query_family?: string;
  planner_query_count?: number;
  decontextualized_query?: string;
  second_pass_used?: boolean;
  second_pass_gain?: number;
  evidence_bundle_hit_count?: number;
}

export interface SearchFilters {
  sources?: string[];
  yearFrom?: number;
  yearTo?: number;
  author?: string;
  sortBy?: 'relevance' | 'date';
}

export interface UseSearchOptions {
  debounceMs?: number;
  filters?: SearchFilters;
  initialQuery?: string;
  initialPage?: number;
}

const PAGE_SIZE = 20;
const SEARCH_QUERY_KEY = 'search-unified';
const SEARCH_STALE_TIME_MS = 45_000;
const SEARCH_GC_TIME_MS = 15 * 60_000;
const sessionSearchCache = new Map<string, SearchResults>();

function buildSessionCacheKey(query: string, page: number, filters: SearchFilters): string {
  const normalizedSources = [...(filters.sources || [])].sort().join(',');
  return [
    query.trim().toLowerCase(),
    page,
    filters.yearFrom ?? '',
    filters.yearTo ?? '',
    filters.sortBy ?? 'relevance',
    normalizedSources,
  ].join('|');
}

interface FetchSearchParams {
  query: string;
  page: number;
  filters?: SearchFilters;
  signal?: AbortSignal;
}

async function fetchSearchResults({
  query,
  page,
  filters,
  signal,
}: FetchSearchParams): Promise<SearchResults> {
  const offset = page * PAGE_SIZE;
  const data = await searchApi.unified(
    query,
    PAGE_SIZE,
    offset,
    filters?.yearFrom,
    filters?.yearTo,
    signal,
  );

  let internal = data.results.filter((result) => result.source === 'internal');
  let external = data.results.filter((result) => result.source !== 'internal');

  if (filters?.sources && filters.sources.length > 0) {
    external = external.filter((result) =>
      filters.sources!.some((source) => {
        if (source === 'arxiv') return result.source === 'arxiv';
        if (source === 'semantic-scholar' || source === 's2') return result.source === 's2';
        return false;
      }),
    );
  }

  if (filters?.sortBy === 'date') {
    const sortByYear = (a: SearchResult, b: SearchResult) => (b.year || 0) - (a.year || 0);
    internal = [...internal].sort(sortByYear);
    external = [...external].sort(sortByYear);
  }

  return {
    internal,
    external,
    total: data.total,
    metadata: {
      query_family: (data as Record<string, unknown>).query_family as string | undefined,
      planner_query_count: (data as Record<string, unknown>).planner_query_count as number | undefined,
      decontextualized_query: (data as Record<string, unknown>).decontextualized_query as string | undefined,
      second_pass_used: (data as Record<string, unknown>).second_pass_used as boolean | undefined,
      second_pass_gain: (data as Record<string, unknown>).second_pass_gain as number | undefined,
      evidence_bundle_hit_count: (data as Record<string, unknown>).evidence_bundle_hit_count as number | undefined,
    },
  };
}

/**
 * useSearch hook with debounce and filters
 *
 * @param options - Hook options including debounceMs, filters, initialQuery, initialPage
 * @returns Search state and handlers
 */
export function useSearch(options: UseSearchOptions = {}) {
  const { debounceMs = 300, filters, initialQuery = '', initialPage = 0 } = options;

  const queryClient = useQueryClient();
  const [query, setQuery] = useState(initialQuery);
  const [debouncedQuery, setDebouncedQuery] = useState(initialQuery);
  const [page, setPage] = useState(initialPage);
  const normalizedFilters = useMemo(
    () => ({
      yearFrom: filters?.yearFrom,
      yearTo: filters?.yearTo,
      sortBy: filters?.sortBy,
      sources: [...(filters?.sources || [])].sort(),
    }),
    [filters?.yearFrom, filters?.yearTo, filters?.sortBy, filters?.sources],
  );
  const hasInput = query.trim().length > 0;
  const queryEnabled = debouncedQuery.trim().length > 0;
  const immediateCacheKey = useMemo(
    () => buildSessionCacheKey(query, page, normalizedFilters),
    [query, page, normalizedFilters],
  );
  const immediateCachedData = useMemo(
    () => sessionSearchCache.get(immediateCacheKey) ?? null,
    [immediateCacheKey],
  );
  const activeCacheKey = useMemo(
    () => buildSessionCacheKey(debouncedQuery, page, normalizedFilters),
    [debouncedQuery, page, normalizedFilters],
  );
  const sessionCachedData = useMemo(
    () => sessionSearchCache.get(activeCacheKey) ?? null,
    [activeCacheKey],
  );

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
      setPage(0);
    }, debounceMs);

    return () => clearTimeout(timer);
  }, [query, debounceMs]);

  useEffect(() => {
    setPage(0);
  }, [normalizedFilters.yearFrom, normalizedFilters.yearTo, normalizedFilters.sortBy, normalizedFilters.sources]);

  const submitSearch = useCallback(() => {
    setDebouncedQuery(query);
    setPage(0);
  }, [query]);

  const searchQuery = useQuery({
    queryKey: [SEARCH_QUERY_KEY, debouncedQuery, page, normalizedFilters],
    enabled: queryEnabled,
    placeholderData: keepPreviousData,
    staleTime: SEARCH_STALE_TIME_MS,
    gcTime: SEARCH_GC_TIME_MS,
    initialData: () => (queryEnabled ? (sessionSearchCache.get(activeCacheKey) ?? undefined) : undefined),
    queryFn: ({ signal }) =>
      fetchSearchResults({
        query: debouncedQuery,
        page,
        filters: normalizedFilters,
        signal,
      }),
  });

  useEffect(() => {
    if (!queryEnabled || !searchQuery.data) {
      return;
    }
    sessionSearchCache.set(activeCacheKey, searchQuery.data);
  }, [activeCacheKey, queryEnabled, searchQuery.data]);

  useEffect(() => {
    if (!queryEnabled || !searchQuery.data) {
      setPage(0);
      return;
    }

    if (searchQuery.isPlaceholderData) {
      return;
    }

    const totalPages = Math.ceil(searchQuery.data.total / PAGE_SIZE);
    if (page >= totalPages - 1) {
      return;
    }

    const nextPage = page + 1;
    void queryClient.prefetchQuery({
      queryKey: [SEARCH_QUERY_KEY, debouncedQuery, nextPage, normalizedFilters],
      queryFn: ({ signal }) =>
        fetchSearchResults({
          query: debouncedQuery,
          page: nextPage,
          filters: normalizedFilters,
          signal,
        }),
    });
  }, [debouncedQuery, normalizedFilters, page, queryClient, queryEnabled, searchQuery.data]);

  const shouldHidePlaceholderData = searchQuery.isPlaceholderData && page === 0;
  const results = hasInput
    ? shouldHidePlaceholderData
      ? (immediateCachedData ?? sessionCachedData ?? null)
      : (searchQuery.data ?? immediateCachedData ?? sessionCachedData ?? null)
    : null;
  const isInitialLoading = queryEnabled && searchQuery.isFetching && !searchQuery.data;
  const isPageFetching = queryEnabled && searchQuery.isFetching && !!searchQuery.data;
  const loading = isInitialLoading || isPageFetching;
  const error = searchQuery.error
    ? searchQuery.error instanceof Error
      ? searchQuery.error.message
      : 'Search failed'
    : null;

  const nextPage = useCallback(() => {
    const totalPages = results ? Math.ceil(results.total / PAGE_SIZE) : 0;
    if (results && page < totalPages - 1) {
      setPage(p => p + 1);
    }
  }, [page, results]);

  const prevPage = useCallback(() => {
    setPage(p => Math.max(0, p - 1));
  }, []);

  const goToPage = useCallback((pageNum: number) => {
    setPage(Math.max(0, pageNum));
  }, []);

  const clearSearch = useCallback(() => {
    setQuery('');
    setDebouncedQuery('');
    setPage(0);
  }, []);

  const totalPages = results ? Math.ceil(results.total / PAGE_SIZE) : 0;

  return {
    query,
    setQuery,
    submitSearch,
    results,
    loading,
    isInitialLoading,
    isPageFetching,
    error,
    clearSearch,
    page,
    totalPages,
    nextPage,
    prevPage,
    goToPage,
    hasMore: results && page < totalPages - 1,
    hasPrev: page > 0,
    pageSize: PAGE_SIZE,
  };
}
