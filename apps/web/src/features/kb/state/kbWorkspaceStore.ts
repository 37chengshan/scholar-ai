import { create } from 'zustand';

interface KBSearchResultItem {
  id: string;
  paperId: string;
  paperTitle?: string | null;
  content: string;
  page?: number | null;
  score: number;
}

interface KBWorkspaceState {
  activeTab: string;
  isImportDialogOpen: boolean;
  selectedPaperIds: string[];
  searchDraft: string;
  searchResults: KBSearchResultItem[];
  selectedImportJobId: string | null;
  setActiveTab: (tab: string) => void;
  setImportDialogOpen: (open: boolean) => void;
  setSelectedPaperIds: (paperIds: string[]) => void;
  setSearchDraft: (searchDraft: string) => void;
  setSearchResults: (results: KBSearchResultItem[]) => void;
  setSelectedImportJobId: (jobId: string | null) => void;
}

export const useKBWorkspaceStore = create<KBWorkspaceState>((set) => ({
  activeTab: 'papers',
  isImportDialogOpen: false,
  selectedPaperIds: [],
  searchDraft: '',
  searchResults: [],
  selectedImportJobId: null,
  setActiveTab: (tab) => set({ activeTab: tab }),
  setImportDialogOpen: (open) => set({ isImportDialogOpen: open }),
  setSelectedPaperIds: (paperIds) => set({ selectedPaperIds: paperIds }),
  setSearchDraft: (searchDraft) => set({ searchDraft }),
  setSearchResults: (results) => set({ searchResults: results }),
  setSelectedImportJobId: (jobId) => set({ selectedImportJobId: jobId }),
}));
