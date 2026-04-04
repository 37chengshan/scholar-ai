/**
 * usePapers Hook - Papers State Management
 *
 * Custom hook for managing papers list with:
 * - Pagination (page, limit, total)
 * - Search (debounced in component)
 * - Starred filter
 * - Loading and error states
 *
 * Uses papersApi.list() to fetch from backend.
 * Integrates with AuthContext for user isolation.
 */

import { useState, useEffect, useCallback } from 'react';
import * as papersApi from '@/services/papersApi';
import { useAuth } from '@/contexts/AuthContext';
import type { PaperWithProgress, PapersQueryParams } from '@/types';

/**
 * Hook options
 */
interface UsePapersOptions {
  limit?: number;
  search?: string;
  starred?: boolean;
}

/**
 * Hook return type
 */
interface UsePapersReturn {
  papers: PaperWithProgress[];
  total: number;
  page: number;
  totalPages: number;
  loading: boolean;
  error: string | null;
  setPage: (page: number) => void;
  refetch: () => Promise<void>;
}

/**
 * usePapers Hook
 *
 * Manages papers list with pagination, search, and filters.
 * Automatically fetches when page, search, or starred changes.
 *
 * @param options - Hook options (limit, search, starred)
 * @returns Papers state and actions
 */
export function usePapers(options: UsePapersOptions = {}): UsePapersReturn {
  const { limit = 20, search, starred } = options;
  const { user } = useAuth();

  // State
  const [papers, setPapers] = useState<PaperWithProgress[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Calculate total pages
  const totalPages = Math.ceil(total / limit);

  /**
   * Fetch papers from API
   */
  const fetchPapers = useCallback(async () => {
    // Don't fetch if not authenticated
    if (!user) {
      setPapers([]);
      setTotal(0);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Build query params
      const params: PapersQueryParams = {
        page,
        limit,
        search: search || undefined,
      };

      // Note: starred filter will be added when backend supports it (Plan 15-01)
      // For now, we prepare the interface but don't send it to the API
      // if (starred !== undefined) {
      //   params.starred = starred;
      // }

      const response = await papersApi.list(params);

      if (response.success && response.data) {
        setPapers(response.data.papers);
        setTotal(response.data.total);
      } else {
        setPapers([]);
        setTotal(0);
      }
    } catch (err: any) {
      // Error is already handled by apiClient interceptor (shows toast)
      // Just set local error state for component use
      setError(err.response?.data?.error?.detail || err.message || 'Failed to fetch papers');
      setPapers([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [user, page, limit, search, starred]);

  // Fetch papers on mount and when dependencies change
  useEffect(() => {
    fetchPapers();
  }, [fetchPapers]);

  // Reset to page 1 when search or starred filter changes
  useEffect(() => {
    setPage(1);
  }, [search, starred]);

  /**
   * Set page and trigger refetch
   */
  const handleSetPage = useCallback((newPage: number) => {
    setPage(newPage);
  }, []);

  /**
   * Manual refetch
   */
  const refetch = useCallback(async () => {
    await fetchPapers();
  }, [fetchPapers]);

  return {
    papers,
    total,
    page,
    totalPages,
    loading,
    error,
    setPage: handleSetPage,
    refetch,
  };
}

export type { UsePapersOptions, UsePapersReturn };