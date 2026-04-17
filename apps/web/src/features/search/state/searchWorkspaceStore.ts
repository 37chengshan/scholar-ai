import { create } from 'zustand';

interface SearchWorkspaceState {
  activeSource: string;
  sortBy: 'relevance' | 'date';
  selectedAuthorId: string | null;
  pendingImportPaper: any | null;
  selectedKnowledgeBaseId: string | null;
  setActiveSource: (activeSource: string) => void;
  setSortBy: (sortBy: 'relevance' | 'date') => void;
  setSelectedAuthorId: (authorId: string | null) => void;
  setPendingImportPaper: (paper: any | null) => void;
  setSelectedKnowledgeBaseId: (knowledgeBaseId: string | null) => void;
}

export const useSearchWorkspaceStore = create<SearchWorkspaceState>((set) => ({
  activeSource: 'all',
  sortBy: 'relevance',
  selectedAuthorId: null,
  pendingImportPaper: null,
  selectedKnowledgeBaseId: null,
  setActiveSource: (activeSource) => set({ activeSource }),
  setSortBy: (sortBy) => set({ sortBy }),
  setSelectedAuthorId: (authorId) => set({ selectedAuthorId: authorId }),
  setPendingImportPaper: (paper) => set({ pendingImportPaper: paper }),
  setSelectedKnowledgeBaseId: (knowledgeBaseId) => set({ selectedKnowledgeBaseId: knowledgeBaseId }),
}));
