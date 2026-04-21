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
import { useNavigate } from "react-router";
import { motion, AnimatePresence } from "motion/react";
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
import { SessionSidebar } from '@/features/chat/components/session-sidebar/SessionSidebar';
import { MessageFeed } from '@/features/chat/components/message-feed/MessageFeed';
import { ComposerInput } from '@/features/chat/components/composer-input/ComposerInput';
import { ChatHeader } from '@/features/chat/components/ChatHeader';
import { ChatRightPanel } from '@/features/chat/components/ChatRightPanel';
import { RunHeader } from '@/features/chat/components/workbench/RunHeader';
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
  const [sessionSearchQuery, setSessionSearchQuery] = useState('');
  const [agentUIState, setAgentUIState] = useState<AgentUIState>("IDLE");
  const [sending, setSending] = useState(false); // 防止重复发送
  const [sessionTokens, setSessionTokens] = useState(0); // 当前session的token
  const [sessionCost, setSessionCost] = useState(0); // 当前session的花费
  const [selectedMessage, setSelectedMessage] = useState<
    RichChatMessage | undefined
  >(undefined); // Phase 4.1: 选中的历史消息
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageListRef = useRef<HTMLDivElement>(null);
  const sseServiceRef = useRef<SSEService | null>(null);
  const currentMessageIdRef = useRef<string>(""); // ref for stale closure fix
  const sendLockRef = useRef(false); // Prevent duplicate send attempts while stream is active

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
  } = useSessions();

  const {
    renderMessages,
    placeholderId,
    addUserMessage,
    addPlaceholderMessage,
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
    bindPlaceholderToMessageId,
    syncStreamingMessage,
    ingestRuntimeEvent,
    markStreamError,
    markStreamCancelled,
    completeStreamingMessage,
    removePlaceholderMessage,
    clearPlaceholder,
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
      navigate(`/read/${citation.paper_id}?page=${page}`);
    },
    [navigate, isZh],
  );

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString(isZh ? "zh-CN" : "en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="h-[calc(100vh-3.5rem)] w-full flex font-sans bg-background text-foreground overflow-hidden">
      <div className="flex-shrink-0">
        <SessionSidebar
          sessions={filteredSessions}
          currentSessionId={currentSession?.id ?? null}
          loading={loading}
          isZh={isZh}
          labels={{
            terminal: t.terminal,
            sessions: t.sessions,
            search: t.search,
            history: t.history,
            newChat: t.newChat,
            noSearchResults: isZh ? '未找到匹配会话' : 'No matching sessions',
            messageSuffix: isZh ? '条消息' : 'messages',
          }}
          searchValue={sessionSearchQuery}
          onSearchChange={setSessionSearchQuery}
          onCreateSession={handleNewSession}
          onSwitchSession={handleSwitchSession}
          onDeleteSession={handleDeleteSession}
        />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-h-0 bg-background min-w-0">
        <ChatHeader
          title={currentSession?.title || t.newChat}
          showRightPanel={showRightPanel}
          isZh={isZh}
          onToggleRightPanel={() => setRightPanelOpen(!showRightPanel)}
        />

        {/* D-03: Scope banner - below header, above messages */}
        <ScopeBanner
          type={uiScope.type}
          title={uiScope.title}
          errorMessage={uiScope.errorMessage}
          onExitScope={handleExitScope}
        />

        <RunHeader run={runtime.run} />

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
          formatTime={formatTime}
          onSuggest={(text) => {
            setInput(text);
          }}
        />

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

      {/* Right Sidebar: Agent State + Activity Panel */}
      <AnimatePresence>
        {showRightPanel && (
          <ChatRightPanel
            selectedMessage={selectedMessage}
            streamState={streamState}
            activeRun={runtime.run}
            sessionTokens={sessionTokens}
            sessionCost={sessionCost}
            onStop={handleStop}
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
