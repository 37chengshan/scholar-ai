import { create } from 'zustand';

interface ChatWorkspaceState {
  selectedSessionId: string | null;
  selectedMessageId: string | null;
  scope: {
    paperId: string | null;
    kbId: string | null;
  };
  mode: 'auto' | 'rag' | 'agent';
  composerDraft: string;
  rightPanelOpen: boolean;
  showDeleteConfirm: boolean;
  pendingDeleteSessionId: string | null;
  setSelectedSessionId: (id: string | null) => void;
  setSelectedMessageId: (id: string | null) => void;
  setScope: (scope: { paperId: string | null; kbId: string | null }) => void;
  setMode: (mode: 'auto' | 'rag' | 'agent') => void;
  setComposerDraft: (draft: string) => void;
  setRightPanelOpen: (open: boolean) => void;
  setShowDeleteConfirm: (show: boolean) => void;
  setPendingDeleteSessionId: (id: string | null) => void;
}

export const useChatWorkspaceStore = create<ChatWorkspaceState>((set) => ({
  selectedSessionId: null,
  selectedMessageId: null,
  scope: {
    paperId: null,
    kbId: null,
  },
  mode: 'auto',
  composerDraft: '',
  rightPanelOpen: true,
  showDeleteConfirm: false,
  pendingDeleteSessionId: null,
  setSelectedSessionId: (id) => set({ selectedSessionId: id }),
  setSelectedMessageId: (id) => set({ selectedMessageId: id }),
  setScope: (scope) => set({ scope }),
  setMode: (mode) => set({ mode }),
  setComposerDraft: (draft) => set({ composerDraft: draft }),
  setRightPanelOpen: (open) => set({ rightPanelOpen: open }),
  setShowDeleteConfirm: (show) => set({ showDeleteConfirm: show }),
  setPendingDeleteSessionId: (id) => set({ pendingDeleteSessionId: id }),
}));
