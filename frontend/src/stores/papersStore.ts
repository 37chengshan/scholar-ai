/**
 * Papers Store - Zustand State Management
 *
 * Manages papers list and filters state:
 * - papers: List of papers with processing status
 * - selectedPaper: Currently selected paper (detail view)
 * - filters: Search and sort filters
 *
 * Used by Library and Upload pages.
 */

import { create } from 'zustand';
import type { PaperWithProgress } from '@/types';

/**
 * Papers state interface
 */
interface PapersState {
  papers: PaperWithProgress[];
  selectedPaper: PaperWithProgress | null;
  filters: {
    search: string;
    sortBy: 'createdAt' | 'updatedAt' | 'title' | 'year' | 'citations';
    sortOrder: 'asc' | 'desc';
  };

  // Actions
  setPapers: (papers: PaperWithProgress[]) => void;
  setSelectedPaper: (paper: PaperWithProgress | null) => void;
  setFilters: (filters: Partial<PapersState['filters']>) => void;
  clearPapers: () => void;
}

/**
 * Papers store
 *
 * Provides global papers state for Library and Upload pages.
 * Supports filtering, sorting, and selection.
 */
export const usePapersStore = create<PapersState>((set) => ({
  // Initial state
  papers: [],
  selectedPaper: null,
  filters: {
    search: '',
    sortBy: 'createdAt',
    sortOrder: 'desc',
  },

  // Set papers list
  setPapers: (papers) => set({ papers }),

  // Set selected paper (detail view)
  setSelectedPaper: (selectedPaper) => set({ selectedPaper }),

  // Update filters (partial update)
  setFilters: (filters) =>
    set((state) => ({
      filters: { ...state.filters, ...filters },
    })),

  // Clear papers (on logout)
  clearPapers: () =>
    set({
      papers: [],
      selectedPaper: null,
      filters: {
        search: '',
        sortBy: 'createdAt',
        sortOrder: 'desc',
      },
    }),
}));