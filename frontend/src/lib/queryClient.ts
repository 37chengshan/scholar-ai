import { QueryClient } from '@tanstack/react-query';

/**
 * React Query Client Configuration
 *
 * Settings per D-06:
 * - staleTime: 5 minutes (data is fresh for 5min)
 * - gcTime: 10 minutes (cache retained for 10min after unused)
 * - refetchOnWindowFocus: false (no automatic refetch on tab focus)
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false,
      retry: 1, // Retry failed requests once
      refetchOnReconnect: true, // Refetch when network reconnects
    },
    mutations: {
      retry: 1,
    },
  },
});