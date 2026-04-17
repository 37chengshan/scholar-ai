import { useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router';
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
  } = useChatWorkspaceStore();

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
