import { create } from 'zustand';

interface KBWorkspaceState {
  activeTab: string;
  isImportDialogOpen: boolean;
  selectedPaperIds: string[];
  selectedImportJobId: string | null;
  setActiveTab: (tab: string) => void;
  setImportDialogOpen: (open: boolean) => void;
  setSelectedPaperIds: (paperIds: string[]) => void;
  setSelectedImportJobId: (jobId: string | null) => void;
}

export const useKBWorkspaceStore = create<KBWorkspaceState>((set) => ({
  activeTab: 'papers',
  isImportDialogOpen: false,
  selectedPaperIds: [],
  selectedImportJobId: null,
  setActiveTab: (tab) => set({ activeTab: tab }),
  setImportDialogOpen: (open) => set({ isImportDialogOpen: open }),
  setSelectedPaperIds: (paperIds) => set({ selectedPaperIds: paperIds }),
  setSelectedImportJobId: (jobId) => set({ selectedImportJobId: jobId }),
}));
