import { create } from 'zustand';

interface KBWorkspaceState {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const useKBWorkspaceStore = create<KBWorkspaceState>((set) => ({
  activeTab: 'papers',
  setActiveTab: (tab) => set({ activeTab: tab }),
}));
