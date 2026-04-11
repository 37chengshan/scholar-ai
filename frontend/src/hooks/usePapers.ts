/**
 * usePapers Hook - Papers State Management
 *
 * Custom hook for managing papers list with:
 * - Pagination (page, limit, total)
 * - Search (debounced in component)
 * - Starred filter
 * - Loading and error states
 *
 * Now uses React Query for caching and state management (D-06).
 * Maintains backward compatibility with existing interface.
 */

import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import * as papersApi from '@/services/papersApi';
import { useAuth } from '@/contexts/AuthContext';
import type { PaperWithProgress, PapersQueryParams } from '@/types';

/**
 * Hook options
 */
interface UsePapersOptions {
  limit?: number;
  page?: number;
  search?: string;
  starred?: boolean;
  readStatus?: 'unread' | 'in-progress' | 'completed';
  dateFrom?: string;
  dateTo?: string;
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
  updatePaperLocal: (paperId: string, updates: Partial<PaperWithProgress>) => void;
}

/**
 * usePapers Hook
 *
 * Manages papers list with pagination, search, and filters.
 * Uses React Query for caching (staleTime: 5min, gcTime: 10min).
 *
 * @param options - Hook options (limit, search, starred)
 * @returns Papers state and actions
 */
export function usePapers(options: UsePapersOptions = {}): UsePapersReturn {
  const { limit = 20, page: externalPage, search, starred, readStatus, dateFrom, dateTo } = options;
  const { user } = useAuth();

  // Local state for page (can be controlled externally)
  const [internalPage, setInternalPage] = useState(1);
  
  // Use external page if provided, otherwise use internal state
  const page = externalPage ?? internalPage;

  // React Query hook for papers
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['papers', { page, limit, search, starred, readStatus, dateFrom, dateTo, userId: user?.id }],
    queryFn: async () => {
      if (!user) {
        return { papers: [], total: 0 };
      }

      // Build query params
      const params: PapersQueryParams = {
        page,
        limit,
        search: search || undefined,
        starred: starred,
        readStatus: readStatus,
        dateFrom: dateFrom,
        dateTo: dateTo,
      };

      const response = await papersApi.list(params);

      if (response.success && response.data) {
        return {
          papers: response.data.papers,
          total: response.data.total,
        };
      }

      return { papers: [], total: 0 };
    },
    enabled: !!user, // Only fetch when user is authenticated
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });

  // Extract values from query result
  const papers = data?.papers || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / limit);

  // Error handling
  const errorMessage = error ? (error as Error).message : null;

  /**
   * Update paper locally (optimistic update)
   */
  const updatePaperLocal = useCallback((paperId: string, updates: Partial<PaperWithProgress>) => {
    // Note: In a full React Query implementation, we would use queryClient.setQueryData
    // For now, this is a placeholder for optimistic updates
  }, []);

/**
 * Handle page change (only used when page is not externally controlled)
   */
  const handleSetPage = useCallback((newPage: number) => {
    if (externalPage === undefined) {
      setInternalPage(newPage);
    }
  }, [externalPage]);

  /**
   * Manual refetch
   */
  const handleRefetch = useCallback(async () => {
    await refetch();
  }, [refetch]);

  return {
    papers,
    total,
    page,
    totalPages,
    loading: isLoading,
    error: errorMessage,
    setPage: handleSetPage,
    refetch: handleRefetch,
    updatePaperLocal,
  };
}

export type { UsePapersOptions, UsePapersReturn };