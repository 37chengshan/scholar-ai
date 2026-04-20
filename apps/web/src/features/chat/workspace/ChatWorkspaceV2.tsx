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
import { motion, AnimatePresence } from "motion/react";
import { useLanguage } from "@/app/contexts/LanguageContext";
import { useSessions } from "@/app/hooks/useSessions";
import { ChatMessage as RichChatMessage } from "@/app/components/ChatMessageCard";
import { ThinkingStep } from "@/app/components/ThinkingProcess";
import { ConfirmationDialog } from "@/app/components/ConfirmationDialog";
import { ConfirmDialog } from "@/app/components/ConfirmDialog";
import { AgentUIState } from "@/app/components/AgentStateSidebar";
import {
  SSEService,
  SSEEventEnvelope,
} from "@/services/sseService";
import { API_BASE_URL } from "@/config/api";
import { toast } from "sonner";
import { ScopeBanner, ScopeType } from "@/app/components/ScopeBanner";
import * as papersApi from '@/services/papersApi';
import { kbApi } from '@/services/kbApi';
import { SessionSidebar } from '@/features/chat/components/session-sidebar/SessionSidebar';
import { MessageFeed } from '@/features/chat/components/message-feed/MessageFeed';
import { ComposerInput } from '@/features/chat/components/composer-input/ComposerInput';
import { ChatHeader } from '@/features/chat/components/ChatHeader';
import { ChatRightPanel } from '@/features/chat/components/ChatRightPanel';
import { usePinnedBottom } from '@/features/chat/hooks/usePinnedBottom';
import { useChatWorkspace } from '@/features/chat/hooks/useChatWorkspace';
import { useChatMessagesViewModel } from '@/features/chat/hooks/useChatMessagesViewModel';
import { useChatStreaming } from '@/features/chat/hooks/useChatStreaming';
import { useChatSend } from '@/features/chat/hooks/useChatSend';
import type {
  CitationItem,
  ExtendedChatMessage,
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
  } = useChatWorkspace();

  const { isPinnedToBottom, maybeFollowBottom, alignToBottom } = usePinnedBottom({
    containerRef: messageListRef,
    anchorRef: messagesEndRef,
  });

  useEffect(() => {
    setIsPinnedToBottom(isPinnedToBottom);
  }, [isPinnedToBottom, setIsPinnedToBottom]);

  // D-07: Single source of truth for scope (banner AND SSE body use same state)
  const [searchParams, setSearchParams] = useSearchParams();
  const paperId = searchParams.get('paperId');
  const kbId = searchParams.get('kbId');

  interface ChatScope {
    type: ScopeType;
    id: string | null;
    title?: string;
    errorMessage?: string;
  }

  const [scope, setScope] = useState<ChatScope>({ type: null, id: null });
  const [scopeLoading, setScopeLoading] = useState(false);

  const safeToolTimeline = (toolTimeline?: ToolTimelineItem[]) =>
    (toolTimeline ?? []).filter(Boolean);

  const safeCitations = (citations?: CitationItem[]) =>
    (citations ?? []).filter(Boolean);

  // Sprint 3: mode state for fast/slow path
  // - 'auto': complexity-based routing (default)
  // - 'rag': force fast path (RAG only, no agent tool loop)
  // - 'agent': force slow path (full agent orchestrator)

  // D-05 + D-07: Parse URL params once at component top, store in state
  useEffect(() => {
    let cancelled = false;

    const validateScope = async () => {
      if (!paperId && !kbId) {
        if (cancelled) {
          return;
        }
        setScope({ type: null, id: null });
        setWorkspaceScope({ type: null, id: null });
        setScopeLoading(false);
        return;
      }

      setScopeLoading(true);
      try {
        // D-08: Validate priority - paperId first, then kbId
        if (paperId) {
          // Validate paperId exists and user has access
          // papersApi.get returns Promise<Paper> (throws on error)
          try {
            const paper = await papersApi.get(paperId);
            if (cancelled) {
              return;
            }
            setScope({
              type: 'single_paper',
              id: paperId,
              title: paper.title || '未知论文',
            });
            setWorkspaceScope({
              type: 'single_paper',
              id: paperId,
              title: paper.title || '未知论文',
            });
          } catch (err) {
            if (cancelled) {
              return;
            }
            setScope({
              type: 'error',
              id: paperId,
              errorMessage: `${paperId} 不存在或无权访问`,
            });
            setWorkspaceScope({
              type: 'error',
              id: paperId,
              errorMessage: `${paperId} 不存在或无权访问`,
            });
          }
          return;
        }

        if (kbId) {
          // Validate kbId exists and user has access
          const kbRes = await kbApi.get(kbId);
          if (cancelled) {
            return;
          }
          setScope({
            type: 'full_kb',
            id: kbId,
            title: kbRes.name,
          });
          setWorkspaceScope({
            type: 'full_kb',
            id: kbId,
            title: kbRes.name,
          });
          return;
        }
      } catch (err) {
        if (cancelled) {
          return;
        }
        setScope({
          type: 'error',
          id: paperId || kbId,
          errorMessage: '作用域验证失败',
        });
        setWorkspaceScope({
          type: 'error',
          id: paperId || kbId,
          errorMessage: '作用域验证失败',
        });
      } finally {
        if (!cancelled) {
          setScopeLoading(false);
        }
      }
    };

    void validateScope();

    return () => {
      cancelled = true;
    };
  }, [paperId, kbId, setWorkspaceScope]);

  useEffect(() => {
    if (scope.type === 'single_paper' || scope.type === 'full_kb') {
      if (mode === 'auto') {
        setMode('rag');
      }
      return;
    }

    setMode('auto');
  }, [scope.type, scope.id, mode, setMode]);

  const { language } = useLanguage();

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

  const isZh = language === "zh";
  const safeSessions = useMemo(
    () => sessions.filter((session) => Boolean(session?.id)),
    [sessions],
  );
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

  const handleExitScope = useCallback(() => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('paperId');
    nextParams.delete('kbId');
    setSearchParams(nextParams);
    setScope({ type: null, id: null });
    setWorkspaceScope({ type: null, id: null });
    toast.info(isZh ? '已退出作用域模式' : 'Scope cleared');
  }, [isZh, searchParams, setSearchParams, setWorkspaceScope]);

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
    return () => {
      sseServiceRef.current?.disconnect();
    };
  }, []);

  const handleNewSession = useCallback(async () => {
    // Disconnect current SSE if connected
    if (sseServiceRef.current) {
      sseServiceRef.current.disconnect();
    }
    sendLockRef.current = false;
    const session = await createSession(isZh ? "新对话" : "New Chat");
    if (session) {
      setSessionSearchQuery('');
      resetForSessionSwitch();
      setSessionTokens(0); // 重置token计数
      setSessionCost(0); // 重置cost计数
      resetRun(); // Reset stream state
    }
  }, [createSession, isZh, resetForSessionSwitch, resetRun]);

  const handleSwitchSession = useCallback(
    async (sessionId: string) => {
      // Disconnect current SSE if connected
      if (sseServiceRef.current) {
        sseServiceRef.current.disconnect();
      }
      sendLockRef.current = false;
      await switchSession(sessionId);
      resetForSessionSwitch();
      setSessionTokens(0); // 重置token计数
      setSessionCost(0); // 重置cost计数
      resetRun(); // Reset stream state
    },
    [switchSession, resetForSessionSwitch, resetRun],
  );

  const handleDeleteSession = useCallback(
    async (sessionId: string, e: React.MouseEvent) => {
      e.stopPropagation();
      openDeleteConfirm(sessionId);
    },
    [openDeleteConfirm],
  );

  const confirmDeleteSession = useCallback(async () => {
    if (!sessionToDelete) return;
    try {
      await deleteSession(sessionToDelete);
      toast.success(isZh ? "对话已删除" : "Session deleted");
    } catch (err) {
      toast.error(isZh ? "删除失败" : "Delete failed");
    }
    closeDeleteConfirm();
  }, [sessionToDelete, deleteSession, isZh, closeDeleteConfirm]);

  const cancelDeleteSession = useCallback(() => {
    closeDeleteConfirm();
  }, [closeDeleteConfirm]);

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

  const { handleSend, handleStop } = useChatSend({
    input,
    sending,
    mode,
    scope,
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

  // Keep workspace-level streaming message id aligned with stream runtime source of truth.
  useEffect(() => {
    setStreamingMessageId(currentMessageId);
  }, [currentMessageId, setStreamingMessageId]);

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

  // Handle agent confirmation (approve/reject)
  const handleConfirmation = useCallback(async (approved: boolean) => {
    if (!confirmation) return;
    try {
      const url = `${API_BASE_URL}/api/v1/chat/confirm`;
      const body = {
        confirmation_id: confirmation.confirmation_id,
        approved,
        session_id: currentSession?.id || '',
      };

      if (!sseServiceRef.current) {
        sseServiceRef.current = new SSEService();
      }

      // The confirm endpoint returns an SSE stream with resumed agent output
      sseServiceRef.current.connect(url, {
        onEnvelope: (event: SSEEventEnvelope) => {
          const eventType = event.event || '';
          const eventMessageId = event.message_id || '';
          const eventData = event.data;

          // Feed events back into useChatStream
          handleSSEEvent({
            message_id: eventMessageId,
            event_type: eventType,
            data: eventData,
            timestamp: Date.now(),
          });

          syncStreamingMessage(currentMessageIdRef.current || eventMessageId);
        },
          onError: (error) => {
          console.error('[Chat] Confirmation stream error:', error);
          dispatch({
            type: 'ERROR',
            code: 'STREAM_ERROR',
            message: error.message,
          });
          toast.error(isZh ? '确认后恢复失败' : 'Failed to resume after confirmation');
        },
        onDone: () => {
          console.debug('[Chat] Confirmation stream done');
          dispatch({
            type: 'STREAM_COMPLETE',
            tokensUsed: streamStateRef.current.tokensUsed,
            cost: streamStateRef.current.cost,
            durationMs: streamStateRef.current.endedAt && streamStateRef.current.startedAt
              ? streamStateRef.current.endedAt - streamStateRef.current.startedAt
              : 0,
          });
        },
      }, body);

      resetConfirmation();
    } catch (err) {
      toast.error(approved ? (isZh ? '批准失败' : 'Approval failed') : (isZh ? '拒绝失败' : 'Rejection failed'));
      resetConfirmation();
    }
  }, [confirmation, currentSession, handleSSEEvent, resetConfirmation, isZh, syncStreamingMessage]);

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
          type={scope.type}
          title={scope.title}
          errorMessage={scope.errorMessage}
          onExitScope={handleExitScope}
        />

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
          scopeType={scope.type}
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
