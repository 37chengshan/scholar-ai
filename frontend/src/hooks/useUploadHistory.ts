/**
 * useUploadHistory Hook
 *
 * Manages upload history with:
 * - Pagination (limit, offset, total)
 * - React Query for caching and state management
 * - Delete mutation with optimistic updates
 *
 * Per D-01: User isolation - only fetches current user's history
 * Per D-02: Poll existing status endpoint, 2s polling for active uploads
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { uploadHistoryApi } from '@/services/uploadHistoryApi';
import { useAuth } from '@/contexts/AuthContext';

/**
 * Hook options
 */
interface UseUploadHistoryOptions {
  limit?: number;
  offset?: number;
}

/**
 * Hook return type
 */
interface UseUploadHistoryReturn {
  records: import('@/services/uploadHistoryApi').UploadHistoryRecord[];
  total: number;
  isLoading: boolean;
  error: string | null;
  deleteRecord: (id: string) => void;
  refetch: () => Promise<void>;
}

/**
 * useUploadHistory Hook
 *
 * Manages upload history list with pagination.
 * Uses React Query for caching (staleTime: 30s per D-02).
 *
 * @param options - Hook options (limit, offset)
 * @returns Upload history state and actions
 */
export function useUploadHistory(options: UseUploadHistoryOptions = {}): UseUploadHistoryReturn {
  const { limit = 50, offset = 0 } = options;
  const { user } = useAuth();
  const queryClient = useQueryClient();

  // React Query hook for upload history
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['uploadHistory', limit, offset, user?.id],
    queryFn: async () => {
      if (!user) {
        return { records: [], total: 0 };
      }

      const response = await uploadHistoryApi.getList(limit, offset);

      if (response.success && response.data) {
        return {
          records: response.data.records,
          total: response.data.total,
        };
      }

      return { records: [], total: 0 };
    },
    enabled: !!user, // Only fetch when user is authenticated
    staleTime: 30 * 1000, // 30 seconds per D-02
    refetchInterval: (query) => {
      const records = query.state.data?.records || [];
      return records.some((record: { status: string }) => record.status === 'PROCESSING')
        ? 2000
        : false;
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: uploadHistoryApi.delete,
    onSuccess: () => {
      // Invalidate and refetch upload history
      queryClient.invalidateQueries({ queryKey: ['uploadHistory'] });
    },
  });

  // Extract values from query result
  const records = data?.records || [];
  const total = data?.total || 0;

  // Error handling
  const errorMessage = error ? (error as Error).message : null;

  /**
   * Delete upload history record
   */
  const handleDeleteRecord = (id: string) => {
    deleteMutation.mutate(id);
  };

  /**
   * Manual refetch
   */
  const handleRefetch = async () => {
    await refetch();
  };

  return {
    records,
    total,
    isLoading,
    error: errorMessage,
    deleteRecord: handleDeleteRecord,
    refetch: handleRefetch,
  };
}

export type { UseUploadHistoryOptions, UseUploadHistoryReturn };
