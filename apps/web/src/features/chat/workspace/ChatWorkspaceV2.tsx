/**
 * Chat Page - Placeholder Message + message_id Binding + SSE Event Handling
 *
 * LEGACY FREEZE (PR10):
 * - This component is in migration mode.
 * - Do not add new business logic here.
 * - New state/workflow changes must land in features/chat/hooks and workspace store.
 *
 * Main chat interface with:
 * - Placeholder message mechanism (HARD RULE 0.2)
 * - message_id binding for SSE events
 * - SSE streaming for real-time AI responses
 * - Session persistence (create, load, switch, delete)
 * - Agent activity panel (tool calls, thoughts, stats)
 * - Thinking process visualization with auto-collapse
 * - Citations panel with inline markers
 * - Token monitoring
 * - Confirmation dialog for agent approval
 *
 * HARD RULES:
 * - 0.2: Every SSE event MUST carry message_id, frontend MUST validate
 * - 0.3: State machine guards - completed/error/cancelled ignore streaming events
 * - 0.4: Separate buffers for reasoning (think panel) and content (assistant message)
 */

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useLanguage } from "@/app/contexts/LanguageContext";
import type { ScopeType } from "@/app/components/ScopeBanner";
import {
  SSEService,
} from "@/services/sseService";
import { toast } from "sonner";
import { usePinnedBottom } from '@/features/chat/hooks/usePinnedBottom';
import { useChatWorkspace } from '@/features/chat/hooks/useChatWorkspace';
import { useChatMessagesViewModel } from '@/features/chat/hooks/useChatMessagesViewModel';
import { useChatStreaming } from '@/features/chat/hooks/useChatStreaming';
import { useChatSend } from '@/features/chat/hooks/useChatSend';
import { useChatScopeController } from '@/features/chat/hooks/useChatScopeController';
import { useChatRuntimeBridge } from '@/features/chat/hooks/useChatRuntimeBridge';
import { useRuntime } from '@/features/chat/runtime/useRuntime';
import { useChatHandoff } from '@/features/chat/hooks/useChatHandoff';
import { ChatWorkspaceLayout } from '@/features/chat/workspace/ChatWorkspaceLayout';
import { applyScopeMetadataToSearchParams } from '@/features/chat/hooks/chatScopeQuery';
import { useChatSessionOrchestration } from '@/features/chat/workspace/useChatSessionOrchestration';
import { useChatSessionBinding } from '@/features/chat/workspace/useChatSessionBinding';
import { useChatStreamingSync } from '@/features/chat/workspace/useChatStreamingSync';
import { useChatWorkspaceViewState } from '@/features/chat/workspace/useChatWorkspaceViewState';

export function ChatWorkspaceV2() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { language } = useLanguage();
  const isZh = language === "zh";
  const [sending, setSending] = useState(false); // 防止重复发送
  const [sessionTokens, setSessionTokens] = useState(0); // 当前session的token
  const [sessionCost, setSessionCost] = useState(0); // 当前session的花费
  const [forceNewSessionForNextSend, setForceNewSessionForNextSend] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageListRef = useRef<HTMLDivElement>(null);
  const sseServiceRef = useRef<SSEService | null>(null);
  const currentMessageIdRef = useRef<string>(""); // ref for stale closure fix
  const sendLockRef = useRef(false); // Prevent duplicate send attempts while stream is active
  const handledNewChatRef = useRef(false);

  const {
    mode,
    composerDraft: input,
    rightPanelOpen: showRightPanel,
    showDeleteConfirm,
    pendingDeleteSessionId: sessionToDelete,
    streamingMessageId,
    setMode,
    setComposerDraft: setInput,
    setRightPanelOpen,
    closeDeleteConfirm,
    setStreamingMessageId,
    setIsPinnedToBottom,
    setScope: setWorkspaceScope,
    setActiveRun,
    setSelectedRunId,
    setActiveRunStatus,
    setPendingActions,
    setRecoveryBannerVisible,
    setRunArtifactsPanelOpen,
  } = useChatWorkspace();

  const { isPinnedToBottom, maybeFollowBottom, alignToBottom } = usePinnedBottom({
    containerRef: messageListRef,
    anchorRef: messagesEndRef,
  });

  useEffect(() => {
    setIsPinnedToBottom(isPinnedToBottom);
  }, [isPinnedToBottom, setIsPinnedToBottom]);

  const handoffBanner = useChatHandoff({
    isZh,
    setComposerDraft: setInput,
  });
  const comparePaperIds = useMemo(
    () =>
      (searchParams.get('paper_ids') || '')
        .split(',')
        .map((id) => id.trim())
        .filter(Boolean),
    [searchParams],
  );
  const runtime = useRuntime();

  // Feature-level streaming entry (state machine + buffer + throttle)
  const streamApi = useChatStreaming({
    throttleMs: 100,
    onPhaseChange: (phase, label) => {
      console.debug("[Chat] Phase changed:", phase, label);
    },
    onComplete: () => {
      console.debug("[Chat] Stream complete");
    },
    onError: (error) => {
      toast.error(isZh ? `错误: ${error.message}` : `Error: ${error.message}`);
    },
  });

  const {
    streamState,
    dispatch,
    resetRun,
    handleSSEEvent,
    getBufferedContent,
    currentMessageId,
    confirmation,
    resetConfirmation,
  } = streamApi;
  const streamStateRef = useRef(streamState); // ref for stale closure fix in onDone

  const {
    desiredSessionId,
    wantsNewSession,
    hasExplicitScopeInUrl,
    hasHandoffScopeWithoutSession,
    currentSession,
    messages: sessionMessages,
    loading,
    createSession,
    switchSession,
    deleteSession,
    clearCurrentSession,
    safeSessions,
  } = useChatSessionBinding(searchParams);
  const { scope, scopeLoading, handleExitScope } = useChatScopeController({
    mode,
    isZh,
    setMode,
    setWorkspaceScope,
    sessionScopeMetadata: currentSession?.metadata as Record<string, unknown> | null,
  });

  const {
    renderMessages,
    addUserMessage,
    addPlaceholderMessage,
    rebindSessionId,
    bindPlaceholderToMessageId,
    syncStreamingMessage: patchStreamingMessage,
    markStreamError,
    markStreamCancelled,
    completeStreamingMessage,
    removePlaceholderMessage,
    clearPlaceholder,
    resetForSessionSwitch,
  } = useChatMessagesViewModel({
    sessionMessages,
    streamState,
    streamingMessageId,
  });

  const uiScope = useMemo(() => ({
    ...scope,
    type: scope.type === 'general' ? null : scope.type as ScopeType,
  }), [scope]);

  // Initialize SSEService instance
  useEffect(() => {
    sseServiceRef.current = new SSEService();
  }, []);
  const { t, confirmDeleteSession, cancelDeleteSession } = useChatSessionOrchestration({
    isZh,
    sessionToDelete,
    switchSession,
    deleteSession,
    resetForSessionSwitch,
    resetRuntimeRun: runtime.resetRun,
    resetStreamingRun: resetRun,
    closeDeleteConfirm,
    setSessionTokens,
    setSessionCost,
    sendLockRef,
    sseServiceRef,
    wantsNewSession,
    desiredSessionId,
    currentSession: currentSession
      ? {
          id: currentSession.id,
          metadata: currentSession.metadata,
          updatedAt: currentSession.updatedAt,
          createdAt: currentSession.createdAt,
        }
      : null,
    searchParams,
    setSearchParams,
    clearCurrentSession,
    setInput,
    hasHandoffScopeWithoutSession,
    hasExplicitScopeInUrl,
    loading,
    safeSessions: safeSessions.map((session) => ({
      id: session.id,
      metadata: session.metadata,
      updatedAt: session.updatedAt,
      createdAt: session.createdAt,
    })),
    renderMessagesCount: renderMessages.length,
    sending,
    streamStatus: streamState.streamStatus,
    handledNewChatRef,
    setForceNewSessionForNextSend,
  });

  const syncStreamingMessage = useChatStreamingSync({
    getBufferedContent,
    patchStreamingMessage,
    streamStateRef,
  });

  const { ingestRuntimeEvent, handleConfirmation } = useChatRuntimeBridge({
    isZh,
    currentSessionId: currentSession?.id ?? null,
    currentMessageId,
    currentMessageIdRef,
    sseServiceRef,
    runtime,
    streamState,
    confirmation,
    resetConfirmation,
    handleSSEEvent,
    dispatch,
    syncStreamingMessage,
    setActiveRun,
    setSelectedRunId,
    setActiveRunStatus,
    setPendingActions,
    setRecoveryBannerVisible,
    setRunArtifactsPanelOpen,
    setStreamingMessageId,
  });

  const { handleSend, handleStop } = useChatSend({
    input,
    sending,
    mode,
    scope: uiScope,
    comparePaperIds,
    handoffEvidence: handoffBanner?.evidence,
    scopeLoading,
    currentSession,
    forceNewSessionForNextSend,
    isZh,
    setInput,
    setSending,
    setSessionTokens,
    setSessionCost,
    createSession,
    sendLockRef,
    sseServiceRef,
    currentMessageIdRef,
    streamStateRef,
    streamApi,
    addUserMessage,
    addPlaceholderMessage,
    rebindSessionId,
    bindPlaceholderToMessageId,
    syncStreamingMessage,
    ingestRuntimeEvent,
    markStreamError,
    markStreamCancelled,
    completeStreamingMessage,
    removePlaceholderMessage,
    clearPlaceholder,
    onSessionCreated: (session) => {
      setForceNewSessionForNextSend(false);
      const next = applyScopeMetadataToSearchParams(
        searchParams,
        (session.metadata as Record<string, unknown> | null) ?? undefined,
      );
      next.set('session', session.id);
      next.delete('new');
      setSearchParams(next, { replace: true });
    },
  });

  // ============================================================================
  // UI Effects
  // ============================================================================

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => {
      if (sseServiceRef.current) {
        sseServiceRef.current.disconnect();
        sseServiceRef.current = null;
      }
    };
  }, []); // Empty deps - only on unmount

  // Keep streamStateRef in sync with streamState for use in stale closures
  useEffect(() => {
    streamStateRef.current = streamState;
  }, [streamState]);

  const {
    thinkingSteps,
    deferredRun,
    panelStreamState,
    handleKeyDown,
    handleCitationClick,
    scopeHint,
    errorStage,
    formatTime,
  } = useChatWorkspaceViewState({
    isZh,
    mode,
    uiScope,
    streamState,
    runtimeRun: runtime.run,
    renderMessages,
    maybeFollowBottom,
    alignToBottom,
    navigate,
    onSend: handleSend,
  });

  return (
    <ChatWorkspaceLayout
      isZh={isZh}
      uiScope={uiScope}
      handoffBanner={
        handoffBanner
          ? {
              originLabel: handoffBanner.originLabel,
              evidenceCount: handoffBanner.evidenceCount,
            }
          : null
      }
      runtimeRun={runtime.run}
      showRightPanel={showRightPanel}
      renderMessages={renderMessages}
      streamState={streamState}
      streamingMessageId={streamingMessageId}
      thinkingSteps={thinkingSteps}
      messagesEndRef={messagesEndRef}
      messageListRef={messageListRef}
      handleCitationClick={handleCitationClick}
      handleStop={handleStop}
      handleSend={handleSend}
      setInput={setInput}
      formatTime={formatTime}
      errorStage={errorStage}
      scopeHint={scopeHint}
      mode={mode}
      input={input}
      scopeLoading={scopeLoading}
      sending={sending}
      setMode={setMode}
      handleKeyDown={handleKeyDown}
      panelStreamState={panelStreamState}
      deferredRun={deferredRun}
      sessionTokens={sessionTokens}
      sessionCost={sessionCost}
      setRightPanelOpen={setRightPanelOpen}
      handleExitScope={handleExitScope}
      confirmation={confirmation}
      handleConfirmation={handleConfirmation}
      showDeleteConfirm={showDeleteConfirm}
      confirmDeleteSession={confirmDeleteSession}
      cancelDeleteSession={cancelDeleteSession}
      labels={{
        noMessages: t.noMessages,
        sendFirst: t.sendFirst,
        thinking: t.thinking,
        stop: t.stop,
        placeholder: t.placeholder,
        verify: t.verify,
      }}
    />
  );
}
