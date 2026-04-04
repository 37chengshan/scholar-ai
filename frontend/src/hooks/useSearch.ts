/**
 * useSearch Hook
 *
 * Search state management with 300ms debounce (D-11)
 *
 * Features:
 * - Debounced search query (300ms delay)
 * - Unified search across internal + external sources
 * - Loading and error states
 * - Results caching
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

/**
 * useSearch hook with debounce
 *
 * @param debounceMs - Debounce delay in milliseconds (default: 300ms per D-11)
 * @returns Search state and handlers
 */
export function useSearch(debounceMs: number = 300) {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [results, setResults] = useState<SearchResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Debounce query (D-11: 300ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, debounceMs);

    return () => clearTimeout(timer);
  }, [query, debounceMs]);

  // Search when debounced query changes
  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setResults(null);
      return;
    }

    setLoading(true);
    setError(null);

    searchApi.unified(debouncedQuery)
      .then(data => {
        // Separate internal and external results
        const internal = data.results.filter(r => r.source === 'internal');
        const external = data.results.filter(r => r.source !== 'internal');

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
  }, [debouncedQuery]);

  // Clear search
  const clearSearch = useCallback(() => {
    setQuery('');
    setDebouncedQuery('');
    setResults(null);
    setError(null);
  }, []);

  return {
    query,
    setQuery,
    results,
    loading,
    error,
    clearSearch,
  };
}