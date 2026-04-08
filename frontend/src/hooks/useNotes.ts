/**
 * useNotes Hook - Notes State Management
 *
 * Custom hook for managing notes list with:
 * - Filtering (by paper, by tag)
 * - Sorting (createdAt, updatedAt, title)
 * - Loading and error states
 *
 * Uses React Query for caching (staleTime: 5min, gcTime: 10min).
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as notesApi from '@/services/notesApi';
import { useAuth } from '@/contexts/AuthContext';
import type { GetNotesParams, CreateNotePayload, UpdateNotePayload, Note } from '@/services/notesApi';

/**
 * Hook options
 */
interface UseNotesOptions {
  paperId?: string;
  tag?: string;
  sortBy?: 'createdAt' | 'updatedAt' | 'title';
  order?: 'asc' | 'desc';
}

/**
 * Hook return type
 */
interface UseNotesReturn {
  notes: Note[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * useNotes Hook
 *
 * Manages notes list with filtering and sorting.
 * Uses React Query for caching (staleTime: 5min, gcTime: 10min).
 *
 * @param options - Hook options (paperId, tag, sortBy, order)
 * @returns Notes data and state
 */
export function useNotes(options?: UseNotesOptions): UseNotesReturn {
  const { isAuthenticated } = useAuth();

  const params: GetNotesParams = {
    paperId: options?.paperId,
    tag: options?.tag,
    sortBy: options?.sortBy || 'createdAt',
    order: options?.order || 'desc',
  };

  const { data, isLoading, error, refetch: queryRefetch } = useQuery({
    queryKey: ['notes', params],
    queryFn: () => notesApi.getNotes(params),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });

  const refetch = async () => {
    await queryRefetch();
  };

  return {
    notes: data || [],
    loading: isLoading,
    error: error?.message || null,
    refetch,
  };
}

/**
 * useCreateNote Hook
 *
 * Creates a new note and invalidates notes cache.
 */
export function useCreateNote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateNotePayload) => notesApi.createNote(payload),
    onSuccess: () => {
      // Invalidate all notes queries to refetch
      queryClient.invalidateQueries({ queryKey: ['notes'] });
    },
  });
}

/**
 * useUpdateNote Hook
 *
 * Updates existing note and invalidates notes cache.
 */
export function useUpdateNote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateNotePayload }) =>
      notesApi.updateNote(id, payload),
    onSuccess: (data) => {
      // Invalidate all notes queries
      queryClient.invalidateQueries({ queryKey: ['notes'] });
      // Update specific note in cache
      queryClient.setQueryData(['notes', { id: data.id }], data);
    },
  });
}

/**
 * useDeleteNote Hook
 *
 * Deletes note and invalidates notes cache.
 */
export function useDeleteNote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => notesApi.deleteNote(id),
    onSuccess: () => {
      // Invalidate all notes queries
      queryClient.invalidateQueries({ queryKey: ['notes'] });
    },
  });
}