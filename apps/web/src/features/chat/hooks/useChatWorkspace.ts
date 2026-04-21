import { useMemo } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { useChatWorkspaceStore } from '@/features/chat/state/chatWorkspaceStore';

export function useChatWorkspace() {
  const {
    activeRun,
    rightPanelOpen,
    showDeleteConfirm,
    pendingDeleteSessionId,
    selectedRunId,
    selectedSessionId,
    selectedMessageId,
    mode,
    composerDraft,
    isPinnedToBottom,
    streamingMessageId,
    scope,
    activeRunStatus,
    pendingActions,
    timelinePanelOpen,
    recoveryBannerVisible,
    runArtifactsPanelOpen,
    setActiveRun,
    setScope,
    setMode,
    setRightPanelOpen,
    setShowDeleteConfirm,
    setPendingDeleteSessionId,
    setSelectedRunId,
    setSelectedSessionId,
    setSelectedMessageId,
    setComposerDraft,
    setIsPinnedToBottom,
    setStreamingMessageId,
    setActiveRunStatus,
    setPendingActions,
    setTimelinePanelOpen,
    setRecoveryBannerVisible,
    setRunArtifactsPanelOpen,
  } = useChatWorkspaceStore(
    useShallow((state) => ({
      activeRun: state.activeRun,
      rightPanelOpen: state.rightPanelOpen,
      showDeleteConfirm: state.showDeleteConfirm,
      pendingDeleteSessionId: state.pendingDeleteSessionId,
      selectedRunId: state.selectedRunId,
      selectedSessionId: state.selectedSessionId,
      selectedMessageId: state.selectedMessageId,
      mode: state.mode,
      composerDraft: state.composerDraft,
      isPinnedToBottom: state.isPinnedToBottom,
      streamingMessageId: state.streamingMessageId,
      scope: state.scope,
      activeRunStatus: state.activeRunStatus,
      pendingActions: state.pendingActions,
      timelinePanelOpen: state.timelinePanelOpen,
      recoveryBannerVisible: state.recoveryBannerVisible,
      runArtifactsPanelOpen: state.runArtifactsPanelOpen,
      setActiveRun: state.setActiveRun,
      setScope: state.setScope,
      setMode: state.setMode,
      setRightPanelOpen: state.setRightPanelOpen,
      setShowDeleteConfirm: state.setShowDeleteConfirm,
      setPendingDeleteSessionId: state.setPendingDeleteSessionId,
      setSelectedRunId: state.setSelectedRunId,
      setSelectedSessionId: state.setSelectedSessionId,
      setSelectedMessageId: state.setSelectedMessageId,
      setComposerDraft: state.setComposerDraft,
      setIsPinnedToBottom: state.setIsPinnedToBottom,
      setStreamingMessageId: state.setStreamingMessageId,
      setActiveRunStatus: state.setActiveRunStatus,
      setPendingActions: state.setPendingActions,
      setTimelinePanelOpen: state.setTimelinePanelOpen,
      setRecoveryBannerVisible: state.setRecoveryBannerVisible,
      setRunArtifactsPanelOpen: state.setRunArtifactsPanelOpen,
    }))
  );

  const scopeState = useMemo(() => ({
    paperId: scope.type === 'single_paper' ? scope.id : null,
    kbId: scope.type === 'full_kb' ? scope.id : null,
    scopeType: scope.type === 'error' ? null : scope.type,
    hasScopeError: scope.type === 'error',
  }), [scope.id, scope.type]);

  const openDeleteConfirm = (sessionId: string) => {
    setPendingDeleteSessionId(sessionId);
    setShowDeleteConfirm(true);
  };

  const closeDeleteConfirm = () => {
    setShowDeleteConfirm(false);
    setPendingDeleteSessionId(null);
  };

  const toggleRightPanel = () => {
    setRightPanelOpen(!rightPanelOpen);
  };

  return {
    activeRun,
    rightPanelOpen,
    showDeleteConfirm,
    pendingDeleteSessionId,
    selectedSessionId,
    selectedMessageId,
    selectedRunId,
    mode,
    composerDraft,
    isPinnedToBottom,
    streamingMessageId,
    activeRunStatus,
    pendingActions,
    timelinePanelOpen,
    recoveryBannerVisible,
    runArtifactsPanelOpen,
    setActiveRun,
    scope,
    scopeState,
    setScope,
    setRightPanelOpen,
    setShowDeleteConfirm,
    setPendingDeleteSessionId,
    setSelectedSessionId,
    setSelectedMessageId,
    setSelectedRunId,
    setMode,
    setComposerDraft,
    setIsPinnedToBottom,
    setStreamingMessageId,
    setActiveRunStatus,
    setPendingActions,
    setTimelinePanelOpen,
    setRecoveryBannerVisible,
    setRunArtifactsPanelOpen,
    toggleRightPanel,
    openDeleteConfirm,
    closeDeleteConfirm,
  };
}
