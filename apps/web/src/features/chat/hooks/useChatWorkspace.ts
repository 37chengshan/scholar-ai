import { useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router';
import { useShallow } from 'zustand/react/shallow';
import { useChatWorkspaceStore } from '@/features/chat/state/chatWorkspaceStore';
import { useChatScope } from '@/features/chat/hooks/useChatScope';

export function useChatWorkspace() {
  const [searchParams] = useSearchParams();
  const {
    rightPanelOpen,
    showDeleteConfirm,
    pendingDeleteSessionId,
    selectedRunId,
    activeRunStatus,
    pendingActions,
    timelinePanelOpen,
    recoveryBannerVisible,
    runArtifactsPanelOpen,
    setScope,
    setMode,
    setRightPanelOpen,
    setShowDeleteConfirm,
    setPendingDeleteSessionId,
    setSelectedRunId,
    setActiveRunStatus,
    setPendingActions,
    setTimelinePanelOpen,
    setRecoveryBannerVisible,
    setRunArtifactsPanelOpen,
  } = useChatWorkspaceStore(
    useShallow((state) => ({
      rightPanelOpen: state.rightPanelOpen,
      showDeleteConfirm: state.showDeleteConfirm,
      pendingDeleteSessionId: state.pendingDeleteSessionId,
      selectedRunId: state.selectedRunId,
      activeRunStatus: state.activeRunStatus,
      pendingActions: state.pendingActions,
      timelinePanelOpen: state.timelinePanelOpen,
      recoveryBannerVisible: state.recoveryBannerVisible,
      runArtifactsPanelOpen: state.runArtifactsPanelOpen,
      setScope: state.setScope,
      setMode: state.setMode,
      setRightPanelOpen: state.setRightPanelOpen,
      setShowDeleteConfirm: state.setShowDeleteConfirm,
      setPendingDeleteSessionId: state.setPendingDeleteSessionId,
      setSelectedRunId: state.setSelectedRunId,
      setActiveRunStatus: state.setActiveRunStatus,
      setPendingActions: state.setPendingActions,
      setTimelinePanelOpen: state.setTimelinePanelOpen,
      setRecoveryBannerVisible: state.setRecoveryBannerVisible,
      setRunArtifactsPanelOpen: state.setRunArtifactsPanelOpen,
    }))
  );

  const scopeState = useChatScope();

  const scope = useMemo(() => ({
    paperId: searchParams.get('paperId'),
    kbId: searchParams.get('kbId'),
  }), [searchParams]);

  useEffect(() => {
    setScope(scope);
    if (scope.paperId || scope.kbId) {
      setMode('rag');
      return;
    }
    setMode('auto');
  }, [scope, setMode, setScope]);

  return {
    rightPanelOpen,
    showDeleteConfirm,
    pendingDeleteSessionId,
    selectedRunId,
    activeRunStatus,
    pendingActions,
    timelinePanelOpen,
    recoveryBannerVisible,
    runArtifactsPanelOpen,
    scope,
    scopeState,
    setRightPanelOpen,
    setShowDeleteConfirm,
    setPendingDeleteSessionId,
    setSelectedRunId,
    setActiveRunStatus,
    setPendingActions,
    setTimelinePanelOpen,
    setRecoveryBannerVisible,
    setRunArtifactsPanelOpen,
  };
}
