import { useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router';
import { useShallow } from 'zustand/react/shallow';
import { useChatWorkspaceStore } from '@/features/chat/state/chatWorkspaceStore';
import { useChatScope } from '@/features/chat/hooks/useChatScope';
import type { WorkspaceScope } from '@/features/chat/state/chatWorkspaceStore';

function parseScopeFromQuery(searchParams: URLSearchParams): WorkspaceScope {
  const paperId = searchParams.get('paperId');
  const kbId = searchParams.get('kbId');

  if (paperId && kbId) {
    return {
      type: 'error',
      id: paperId,
      errorMessage: 'paperId and kbId cannot coexist',
    };
  }

  if (paperId) {
    return {
      type: 'single_paper',
      id: paperId,
    };
  }

  if (kbId) {
    return {
      type: 'full_kb',
      id: kbId,
    };
  }

  return {
    type: null,
    id: null,
  };
}

export function useChatWorkspace() {
  const [searchParams] = useSearchParams();
  const {
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

  const scopeState = useChatScope();

  const queryScope = useMemo(() => parseScopeFromQuery(searchParams), [searchParams]);

  useEffect(() => {
    setScope(queryScope);
    if (queryScope.type === 'single_paper' || queryScope.type === 'full_kb') {
      setMode('rag');
      return;
    }
    if (queryScope.type === null || queryScope.type === 'general') {
      setMode('auto');
    }
  }, [queryScope, setMode, setScope]);

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
    scope,
    queryScope,
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
