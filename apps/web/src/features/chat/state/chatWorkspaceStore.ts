import { create } from 'zustand';

interface ChatWorkspaceState {
  rightPanelOpen: boolean;
  setRightPanelOpen: (open: boolean) => void;
}

export const useChatWorkspaceStore = create<ChatWorkspaceState>((set) => ({
  rightPanelOpen: true,
  setRightPanelOpen: (open) => set({ rightPanelOpen: open }),
}));
