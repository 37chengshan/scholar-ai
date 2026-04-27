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

import { useState, useEffect, useCallback, useMemo, useRef, useDeferredValue } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { motion, AnimatePresence } from "motion/react";
import { PanelRightClose, PanelRightOpen } from "lucide-react";
import { useLanguage } from "@/app/contexts/LanguageContext";
import { useSessions } from "@/app/hooks/useSessions";
import { ChatMessage as RichChatMessage } from "@/app/components/ChatMessageCard";
import { ThinkingStep } from "@/app/components/ThinkingProcess";
import { ConfirmationDialog } from "@/app/components/ConfirmationDialog";
import { ConfirmDialog } from "@/app/components/ConfirmDialog";
import { AgentUIState } from "@/app/components/AgentStateSidebar";
import type { ScopeType } from "@/app/components/ScopeBanner";
import {
  SSEService,
} from "@/services/sseService";
import { toast } from "sonner";
import { ScopeBanner } from '@/app/components/ScopeBanner';
import { MessageFeed } from '@/features/chat/components/message-feed/MessageFeed';
import { ComposerInput } from '@/features/chat/components/composer-input/ComposerInput';
import { ChatRightPanel } from '@/features/chat/components/ChatRightPanel';
import { RunHeader } from '@/features/chat/components/workbench/RunHeader';
import { WorkflowShell } from '@/features/workflow/components/WorkflowShell';
import { usePinnedBottom } from '@/features/chat/hooks/usePinnedBottom';
import { useChatWorkspace } from '@/features/chat/hooks/useChatWorkspace';
import { useChatMessagesViewModel } from '@/features/chat/hooks/useChatMessagesViewModel';
import { useChatStreaming } from '@/features/chat/hooks/useChatStreaming';
import { useChatSend } from '@/features/chat/hooks/useChatSend';
import { useChatScopeController } from '@/features/chat/hooks/useChatScopeController';
import { useChatSessionController } from '@/features/chat/hooks/useChatSessionController';
import { useChatRuntimeBridge } from '@/features/chat/hooks/useChatRuntimeBridge';
import { useRuntime } from '@/features/chat/runtime/useRuntime';
import type {
  CitationItem,
  ToolTimelineItem,
} from '@/features/chat/components/workspaceTypes';

export function ChatWorkspaceV2() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [sessionSearchQuery, setSessionSearchQuery] = useState('');
  const [agentUIState, setAgentUIState] = useState<AgentUIState>("IDLE");
  const [sending, setSending] = useState(false); // 防止重复发送
  const [sessionTokens, setSessionTokens] = useState(0); // 当前session的token
  const [sessionCost, setSessionCost] = useState(0); // 当前session的花费
  const [forceNewSessionForNextSend, setForceNewSessionForNextSend] = useState(false);
  const [selectedMessage, setSelectedMessage] = useState<
    RichChatMessage | undefined
  >(undefined); // Phase 4.1: 选中的历史消息
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
    openDeleteConfirm,
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

  const safeToolTimeline = (toolTimeline?: ToolTimelineItem[]) =>
    (toolTimeline ?? []).filter(Boolean);

  const safeCitations = (citations?: CitationItem[]) =>
    (citations ?? []).filter(Boolean);

  const { language } = useLanguage();
  const isZh = language === "zh";
  const runtime = useRuntime();
  const { scope, scopeLoading, handleExitScope } = useChatScopeController({
    mode,
    isZh,
    setMode,
    setWorkspaceScope,
  });

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
    forceFlush,
    getBufferedContent,
    currentMessageId,
    confirmation,
    resetConfirmation,
  } = streamApi;
  const streamStateRef = useRef(streamState); // ref for stale closure fix in onDone

  const {
    sessions,
    currentSession,
    messages: sessionMessages,
    loading,
    createSession,
    switchSession,
    deleteSession,
    clearCurrentSession,
  } = useSessions();
  const desiredSessionId = searchParams.get('session');
  const wantsNewSession = searchParams.get('new') === '1';

  const {
    renderMessages,
    placeholderId,
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

  const safeSessions = useMemo(
    () => sessions.filter((session) => Boolean(session?.id)),
    [sessions],
  );
  const uiScope = useMemo(() => ({
    ...scope,
    type: scope.type === 'general' ? null : scope.type as ScopeType,
  }), [scope]);
  const normalizedSessionSearchQuery = sessionSearchQuery.trim().toLowerCase();
  const filteredSessions = useMemo(() => {
    const sortedSessions = [...safeSessions].sort((a, b) => {
      const left = new Date(a.updatedAt || a.createdAt).getTime();
      const right = new Date(b.updatedAt || b.createdAt).getTime();
      return right - left;
    });

    if (!normalizedSessionSearchQuery) {
      return sortedSessions;
    }

    return sortedSessions.filter((session) => {
      const title = session.title?.toLowerCase() || '';
      const messageCountText = String(session.messageCount || 0);
      return (
        title.includes(normalizedSessionSearchQuery)
        || messageCountText.includes(normalizedSessionSearchQuery)
      );
    });
  }, [normalizedSessionSearchQuery, safeSessions]);

  const t = {
    terminal: isZh ? "终端对话" : "Terminal",
    sessions: isZh ? "会话列表" : "Sessions",
    search: isZh ? "搜索..." : "Search...",
    history: isZh ? "历史记录" : "History",
    newChat: isZh ? "新对话" : "New Chat",
    placeholder: isZh ? "给 ScholarAI 发送消息..." : "Message ScholarAI...",
    verify: isZh ? "请验证输出结果。" : "Verify outputs.",
    noMessages: isZh ? "开始新对话" : "Start a new conversation",
    sendFirst: isZh ? "发送您的第一条消息" : "Send your first message",
    streaming: isZh ? "流式响应中..." : "Streaming...",
    deleteConfirm: isZh ? "确定删除此对话？" : "Delete this conversation?",
    stop: isZh ? "停止" : "Stop",
    thinking: isZh ? "思考中..." : "Thinking...",
  };

  // Initialize SSEService instance
  useEffect(() => {
    sseServiceRef.current = new SSEService();
  }, []);

  const {
    handleNewSession,
    handleSwitchSession,
    handleDeleteSession,
    confirmDeleteSession,
    cancelDeleteSession,
  } = useChatSessionController({
    isZh,
    sessionToDelete,
    createSession,
    switchSession,
    deleteSession,
    resetForSessionSwitch,
    resetRuntimeRun: runtime.resetRun,
    resetStreamingRun: resetRun,
    openDeleteConfirm,
    closeDeleteConfirm,
    setSessionSearchQuery,
    setSessionTokens,
    setSessionCost,
    sendLockRef,
    sseServiceRef,
  });

  useEffect(() => {
    if (!wantsNewSession) {
      handledNewChatRef.current = false;
      return;
    }

    if (handledNewChatRef.current) {
      return;
    }
    handledNewChatRef.current = true;

    setForceNewSessionForNextSend(true);

    sseServiceRef.current?.disconnect();
    sendLockRef.current = false;
    clearCurrentSession();
    resetForSessionSwitch();
    runtime.resetRun();
    resetRun();
    setSessionTokens(0);
    setSessionCost(0);
    setInput('');

    const next = new URLSearchParams(searchParams);
    next.delete('new');
    next.delete('session');
    setSearchParams(next, { replace: true });
  }, [clearCurrentSession, resetForSessionSwitch, resetRun, runtime, searchParams, setInput, setSearchParams, wantsNewSession]);

  useEffect(() => {
    if (desiredSessionId) {
      setForceNewSessionForNextSend(false);
    }
  }, [desiredSessionId]);

  useEffect(() => {
    if (!desiredSessionId || loading) {
      return;
    }

    if (currentSession?.id === desiredSessionId) {
      return;
    }

    if (!safeSessions.some((session) => session.id === desiredSessionId)) {
      return;
    }

    void handleSwitchSession(desiredSessionId);
  }, [currentSession?.id, desiredSessionId, handleSwitchSession, loading, safeSessions]);

  useEffect(() => {
    if (wantsNewSession || desiredSessionId || !currentSession?.id) {
      return;
    }

    const conversationStarted = renderMessages.length > 0 || sending || streamState.streamStatus === 'streaming';
    if (!conversationStarted) {
      return;
    }

    const next = new URLSearchParams(searchParams);
    next.set('session', currentSession.id);
    next.delete('new');

    if (next.toString() === searchParams.toString()) {
      return;
    }

    setSearchParams(next, { replace: true });
  }, [currentSession?.id, desiredSessionId, renderMessages.length, searchParams, sending, setSearchParams, streamState.streamStatus, wantsNewSession]);

  // ============================================================================
  // Placeholder Message Mechanism (HARD RULE 0.2)
  // ============================================================================

  const syncStreamingMessage = useCallback((messageId: string) => {
    if (!messageId) {
      return;
    }

    const buffered = getBufferedContent();
    patchStreamingMessage(messageId, {
      content: buffered.content,
      reasoning: buffered.reasoning,
      status: streamStateRef.current.streamStatus,
      toolTimeline: safeToolTimeline(streamStateRef.current.toolTimeline).map((timelineItem) => ({
        id: timelineItem.id,
        tool: timelineItem.tool,
        label: timelineItem.label,
        status: timelineItem.status,
        startedAt: timelineItem.startedAt,
        completedAt: timelineItem.completedAt,
        duration: timelineItem.duration,
        summary: timelineItem.summary,
      })),
      citations: safeCitations(streamStateRef.current.citations).map((citation) => ({
        paper_id: citation.paper_id,
        source_id: citation.source_id,
        page_num: citation.page_num,
        section_path: citation.section_path,
        anchor_text: citation.anchor_text,
        text_preview: citation.text_preview,
        title: citation.title,
        authors: citation.authors,
        year: citation.year,
        snippet: citation.snippet,
        page: citation.page,
        score: citation.score,
        content_type: citation.content_type,
      })),
    });
  }, [getBufferedContent, patchStreamingMessage]);

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
    scopeLoading,
    currentSession,
    forceNewSessionForNextSend,
    isZh,
    setInput,
    setSending,
    setAgentUIState,
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
    onSessionCreated: (sessionId) => {
      setForceNewSessionForNextSend(false);
      const next = new URLSearchParams(searchParams);
      next.set('session', sessionId);
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

  // Pinned-bottom auto-follow: only follow when user stays near bottom.
  useEffect(() => {
    const reason = streamState.streamStatus === 'streaming' ? 'stream' : 'message';
    maybeFollowBottom(reason);
  }, [renderMessages, streamState.contentBuffer, streamState.streamStatus, maybeFollowBottom]);

  // Final align at terminal state for better completion readability.
  useEffect(() => {
    if (
      streamState.streamStatus === 'completed'
      || streamState.streamStatus === 'cancelled'
      || streamState.streamStatus === 'error'
    ) {
      alignToBottom();
    }
  }, [streamState.streamStatus, alignToBottom]);

  // Update agent UI state based on stream state
  useEffect(() => {
    if (streamState.streamStatus === "streaming") {
      setAgentUIState("RUNNING");
    } else if (streamState.streamStatus === "completed") {
      setAgentUIState("DONE");
    } else if (streamState.streamStatus === "error") {
      setAgentUIState("DONE");
    } else {
      setAgentUIState("IDLE");
    }
  }, [streamState.streamStatus]);

  // Compute thinking steps from reasoning buffer
  const thinkingSteps = useMemo<ThinkingStep[]>((): ThinkingStep[] => {
    if (!streamState.reasoningBuffer) return [];

    // Split reasoning buffer into steps
    const lines = streamState.reasoningBuffer.split("\n").filter(Boolean);
    return lines.map((line, idx) => ({
      type: "thinking",
      content: line,
      timestamp: streamState.startedAt
        ? streamState.startedAt + idx * 100
        : undefined,
    }));
  }, [streamState.reasoningBuffer, streamState.startedAt]);

  const deferredRun = useDeferredValue(runtime.run);
  const panelStreamState = useMemo(() => {
    if (streamState.streamStatus !== 'streaming') {
      return streamState;
    }
    return {
      ...streamState,
      contentBuffer: '',
      reasoningBuffer: '',
    };
  }, [streamState]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Citation click handler — navigate to read page with specific page
  const handleCitationClick = useCallback(
    (citation: CitationItem | undefined) => {
      if (!citation) {
        return;
      }

      if (!citation.paper_id) {
        toast.warning(isZh ? '引用缺少论文 ID，无法跳转' : 'Citation is missing paper id');
        return;
      }

      const page = citation.page_num || citation.page || 1;
      if (!citation.page_num && !citation.page) {
        toast.warning(isZh ? '引用缺少页码，已跳转到第一页' : 'Citation has no page; opening first page');
      }
      navigate(`/read/${citation.paper_id}?page=${page}&source=chat&source_id=${citation.source_id || ''}`);
    },
    [navigate, isZh],
  );

  const scopeHint = useMemo(() => {
    const scopeLabel = uiScope.type === 'single_paper'
      ? (isZh ? '当前论文' : 'Current paper')
      : uiScope.type === 'full_kb'
        ? (isZh ? '当前知识库' : 'Current KB')
        : (isZh ? '全局' : 'Global');
    const modeLabel = mode === 'auto'
      ? (isZh ? '自动' : 'Auto')
      : mode === 'rag'
        ? (isZh ? '快速问答' : 'Fast RAG')
        : (isZh ? '深度分析' : 'Deep Agent');
    return `${isZh ? '范围' : 'Scope'}：${scopeLabel} · ${isZh ? '模式' : 'Mode'}：${modeLabel}`;
  }, [isZh, mode, uiScope.type]);

  const errorStage = useMemo(() => {
    if (streamState.streamStatus !== 'error') {
      return undefined;
    }
    const phase = runtime.run?.phase || runtime.run?.currentPhase || 'unknown';
    if (!isZh) {
      return phase;
    }
    if (phase === 'planning') return '规划';
    if (phase === 'executing') return '检索/执行';
    if (phase === 'verifying') return '验证';
    if (phase === 'failed') return '失败';
    return String(phase);
  }, [isZh, runtime.run?.currentPhase, runtime.run?.phase, streamState.streamStatus]);

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString(isZh ? "zh-CN" : "en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="relative flex h-full min-h-0 w-full overflow-hidden bg-background text-foreground">
      <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-background">
        <div className="shrink-0 border-b border-border/30 bg-background/60 backdrop-blur-sm">
          <WorkflowShell />
        </div>

        {uiScope.type && (
          <div className="shrink-0 border-b border-border/40 bg-muted/25">
            <ScopeBanner
              type={uiScope.type}
              title={uiScope.title}
              errorMessage={uiScope.errorMessage}
              onExitScope={handleExitScope}
            />
          </div>
        )}

        {runtime.run && (
          <div className="shrink-0 border-b border-border/40 bg-muted/20">
            <RunHeader run={runtime.run} />
          </div>
        )}

        <div className="min-h-0 min-w-0 flex flex-1 flex-col overflow-hidden bg-background">
          <div className="border-b border-border/30 bg-background/40 px-4 py-2.5 text-[11px] font-semibold text-muted-foreground sm:px-6">
            {isZh ? '对话' : 'Conversation'}
          </div>
          <MessageFeed
            renderMessages={renderMessages}
            streamState={streamState}
            currentMessageId={streamingMessageId || ''}
            thinkingSteps={thinkingSteps}
            labels={{
              noMessages: t.noMessages,
              sendFirst: t.sendFirst,
              thinking: t.thinking,
              stop: t.stop,
            }}
            isZh={isZh}
            messagesEndRef={messagesEndRef}
            scrollContainerRef={messageListRef}
            onCitationClick={handleCitationClick}
            onStop={handleStop}
            onRetry={handleSend}
            formatTime={formatTime}
            onSuggest={(text) => {
              setInput(text);
            }}
            errorStage={errorStage}
            recoverable={runtime.run?.recoverable}
            partialAnswerAvailable={Boolean(streamState.contentBuffer)}
          />
        </div>

        <div className="shrink-0 bg-background/75 backdrop-blur-md">
          <div className="px-4 pt-2 text-[11px] text-muted-foreground sm:px-6" aria-live="polite">
            {scopeHint}
          </div>
          <ComposerInput
            scopeType={uiScope.type}
            isZh={isZh}
            mode={mode}
            input={input}
            disabled={scopeLoading || sending}
            streaming={streamState.streamStatus === 'streaming'}
            placeholder={t.placeholder}
            labels={{
              mode: isZh ? '模式' : 'Mode',
              verify: t.verify,
              sendKeyHint: isZh ? '↵ 发送' : '↵ TO SEND',
            }}
            onModeChange={setMode}
            onInputChange={setInput}
            onKeyDown={handleKeyDown}
            onSend={handleSend}
            onStop={handleStop}
          />
        </div>
      </div>

      {!showRightPanel ? (
        <button
          type="button"
          onClick={() => setRightPanelOpen(true)}
          className="absolute right-5 top-20 z-20 hidden h-10 w-10 items-center justify-center rounded-2xl border border-border/70 bg-paper-1/94 text-foreground/60 transition-colors hover:border-primary/20 hover:text-primary xl:inline-flex"
          aria-label={isZh ? "展开右侧栏" : "Show panel"}
          title={isZh ? "展开右侧栏" : "Show panel"}
        >
          <PanelRightOpen className="h-4 w-4" />
        </button>
      ) : null}

      <AnimatePresence>
        {showRightPanel && (
          <ChatRightPanel
            selectedMessage={selectedMessage}
            streamState={panelStreamState}
            activeRun={deferredRun}
            sessionTokens={sessionTokens}
            sessionCost={sessionCost}
            onStop={handleStop}
            onClose={() => setRightPanelOpen(false)}
            isZh={isZh}
          />
        )}
      </AnimatePresence>

      {/* Confirmation Dialog for agent tool approval */}
      <ConfirmationDialog
        isOpen={!!confirmation}
        tool={confirmation?.tool || ''}
        params={confirmation?.params || {}}
        onApprove={() => handleConfirmation(true)}
        onReject={() => handleConfirmation(false)}
      />

      {/* Delete Session Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title={isZh ? "删除对话" : "Delete Session"}
        message={
          isZh
            ? "确定要删除这个对话吗？删除后将无法恢复。"
            : "Are you sure you want to delete this session? This cannot be undone."
        }
        confirmLabel={isZh ? "删除" : "Delete"}
        cancelLabel={isZh ? "取消" : "Cancel"}
        variant="danger"
        onConfirm={confirmDeleteSession}
        onCancel={cancelDeleteSession}
      />

    </div>
  );
}
