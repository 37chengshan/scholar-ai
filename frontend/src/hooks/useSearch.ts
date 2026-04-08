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
 */

import { useState, useEffect, useCallback } from 'react';
import * as searchApi from '@/services/searchApi';

export interface SearchResult {
  id: string;
  title: string;
  authors?: string[];
  abstract?: string;
  year?: number;
  source: 'internal' | 'arxiv' | 's2';
  paperId?: string;
  externalId?: string;
  pdfUrl?: string;
  citations?: number;
}

export interface SearchResults {
  internal: SearchResult[];
  external: SearchResult[];
  total: number;
}

export interface SearchFilters {
  sources?: string[];
  yearFrom?: number;
  yearTo?: number;
  author?: string;
  sortBy?: 'relevance' | 'date';
}

const PAGE_SIZE = 20;

/**
 * useSearch hook with debounce and filters
 *
 * @param debounceMs - Debounce delay in milliseconds (default: 300ms per D-11)
 * @param filters - Search filters (sources, year range, sort)
 * @returns Search state and handlers
 */
export function useSearch(debounceMs: number = 300, filters?: SearchFilters) {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [page, setPage] = useState(0);
  const [results, setResults] = useState<SearchResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
      setPage(0);
    }, debounceMs);

    return () => clearTimeout(timer);
  }, [query, debounceMs]);

  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setResults(null);
      setPage(0);
      return;
    }

    setLoading(true);
    setError(null);

    const offset = page * PAGE_SIZE;

    searchApi.unified(
      debouncedQuery,
      PAGE_SIZE,
      offset,
      filters?.yearFrom,
      filters?.yearTo
    )
      .then(data => {
        let internal = data.results.filter(r => r.source === 'internal');
        let external = data.results.filter(r => r.source !== 'internal');

        if (filters?.sources && filters.sources.length > 0) {
          external = external.filter(r =>
            filters.sources!.some(s => {
              if (s === 'arxiv') return r.source === 'arxiv';
              if (s === 'semantic-scholar' || s === 's2') return r.source === 's2';
              return false;
            })
          );
        }

        if (filters?.sortBy === 'date') {
          const sortByYear = (a: SearchResult, b: SearchResult) => (b.year || 0) - (a.year || 0);
          internal = [...internal].sort(sortByYear);
          external = [...external].sort(sortByYear);
        }

        setResults({
          internal,
          external,
          total: data.total,
        });
      })
      .catch(err => {
        setError(err.response?.data?.error?.detail || err.message || 'Search failed');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [debouncedQuery, page, filters?.yearFrom, filters?.yearTo, filters?.sources, filters?.sortBy]);

  const nextPage = useCallback(() => {
    if (results && (results.internal.length + results.external.length) >= PAGE_SIZE) {
      setPage(p => p + 1);
    }
  }, [results]);

  const prevPage = useCallback(() => {
    setPage(p => Math.max(0, p - 1));
  }, []);

  const goToPage = useCallback((pageNum: number) => {
    setPage(Math.max(0, pageNum));
  }, []);

  const clearSearch = useCallback(() => {
    setQuery('');
    setDebouncedQuery('');
    setResults(null);
    setError(null);
    setPage(0);
  }, []);

  const totalPages = results ? Math.ceil(results.total / PAGE_SIZE) : 0;

  return {
    query,
    setQuery,
    results,
    loading,
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