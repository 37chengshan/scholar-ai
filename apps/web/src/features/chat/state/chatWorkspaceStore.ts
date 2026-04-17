import { create } from 'zustand';
import type { PendingAction, RunStatus } from '@/features/chat/types/run';

interface ChatWorkspaceState {
  selectedSessionId: string | null;
  selectedMessageId: string | null;
  selectedRunId: string | null;
  activeRunStatus: RunStatus;
  pendingActions: PendingAction[];
  timelinePanelOpen: boolean;
  recoveryBannerVisible: boolean;
  runArtifactsPanelOpen: boolean;
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
  setSelectedRunId: (id: string | null) => void;
  setActiveRunStatus: (status: RunStatus) => void;
  setPendingActions: (actions: PendingAction[]) => void;
  setTimelinePanelOpen: (open: boolean) => void;
  setRecoveryBannerVisible: (visible: boolean) => void;
  setRunArtifactsPanelOpen: (open: boolean) => void;
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
  selectedRunId: null,
  activeRunStatus: 'idle',
  pendingActions: [],
  timelinePanelOpen: false,
  recoveryBannerVisible: false,
  runArtifactsPanelOpen: false,
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
  setSelectedRunId: (id) => set({ selectedRunId: id }),
  setActiveRunStatus: (status) => set({ activeRunStatus: status }),
  setPendingActions: (actions) => set({ pendingActions: actions }),
  setTimelinePanelOpen: (open) => set({ timelinePanelOpen: open }),
  setRecoveryBannerVisible: (visible) => set({ recoveryBannerVisible: visible }),
  setRunArtifactsPanelOpen: (open) => set({ runArtifactsPanelOpen: open }),
  setScope: (scope) => set({ scope }),
  setMode: (mode) => set({ mode }),
  setComposerDraft: (draft) => set({ composerDraft: draft }),
  setRightPanelOpen: (open) => set({ rightPanelOpen: open }),
  setShowDeleteConfirm: (show) => set({ showDeleteConfirm: show }),
  setPendingDeleteSessionId: (id) => set({ pendingDeleteSessionId: id }),
}));
