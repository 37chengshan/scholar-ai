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
import {
  Bot,
  Loader2,
  ChevronLeft,
} from "lucide-react";
import { useLanguage } from "@/app/contexts/LanguageContext";
import {
  useChatStream,
  ChatStreamState,
} from "@/app/hooks/useChatStream";
import {
  useSessions,
  ChatMessage as SessionChatMessage,
} from "@/app/hooks/useSessions";
import { ChatMessage as RichChatMessage } from "@/app/components/ChatMessageCard";
import { ThinkingStep } from "@/app/components/ThinkingProcess";
import { TokenMonitor } from "@/app/components/TokenMonitor";
import { ConfirmationDialog } from "@/app/components/ConfirmationDialog";
import { ConfirmDialog } from "@/app/components/ConfirmDialog";
import {
  AgentStateSidebar,
  AgentUIState,
} from "@/app/components/AgentStateSidebar";
import {
  SSEService,
  SSEEvent,
  SSEEventEnvelope,
} from "@/services/sseService";
import { streamMessage as streamChatMessage } from "@/services/chatApi";
import { API_BASE_URL } from "@/config/api";
import { toast } from "sonner";
import { ScopeBanner, ScopeType } from "@/app/components/ScopeBanner";
import * as papersApi from '@/services/papersApi';
import { kbApi } from '@/services/kbApi';
import { SessionSidebar } from '@/features/chat/components/session-sidebar/SessionSidebar';
import { MessageFeed } from '@/features/chat/components/message-feed/MessageFeed';
import { ComposerInput } from '@/features/chat/components/composer-input/ComposerInput';
import type {
  CitationItem,
  ExtendedChatMessage,
  ToolTimelineItem,
} from '@/features/chat/components/workspaceTypes';

export function ChatWorkspaceV2() {
  const navigate = useNavigate();
  const [input, setInput] = useState("");
  const [sessionSearchQuery, setSessionSearchQuery] = useState('');
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [agentUIState, setAgentUIState] = useState<AgentUIState>("IDLE");
  const [sending, setSending] = useState(false); // 防止重复发送
  const [sessionTokens, setSessionTokens] = useState(0); // 当前session的token
  const [sessionCost, setSessionCost] = useState(0); // 当前session的花费
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false); // 删除确认对话框
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null); // 待删除的会话ID
  const [currentMessageId, setCurrentMessageId] = useState<string>(""); // 当前流消息的 message_id (HARD RULE 0.2)
  const [selectedMessage, setSelectedMessage] = useState<
    RichChatMessage | undefined
  >(undefined); // Phase 4.1: 选中的历史消息
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sseServiceRef = useRef<SSEService | null>(null);
  const currentMessageIdRef = useRef<string>(""); // ref for stale closure fix

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
  const [mode, setMode] = useState<'auto' | 'rag' | 'agent'>('auto');

  // D-05 + D-07: Parse URL params once at component top, store in state
  useEffect(() => {
    const validateScope = async () => {
      if (!paperId && !kbId) {
        setScope({ type: null, id: null });
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
            setScope({
              type: 'single_paper',
              id: paperId,
              title: paper.title || '未知论文',
            });
          } catch (err) {
            setScope({
              type: 'error',
              id: paperId,
              errorMessage: `${paperId} 不存在或无权访问`,
            });
          }
          setScopeLoading(false);
          return;
        }

        if (kbId) {
          // Validate kbId exists and user has access
          const kbRes = await kbApi.get(kbId);
          setScope({
            type: 'full_kb',
            id: kbId,
            title: kbRes.name,
          });
          setScopeLoading(false);
          return;
        }
      } catch (err) {
        setScope({
          type: 'error',
          id: paperId || kbId,
          errorMessage: '作用域验证失败',
        });
        setScopeLoading(false);
      }
    };

    void validateScope();
  }, [paperId, kbId]);

  useEffect(() => {
    if (scope.type === 'single_paper' || scope.type === 'full_kb') {
      setMode((current) => (current === 'auto' ? 'rag' : current));
      return;
    }

    setMode('auto');
  }, [scope.type, scope.id]);

  const { language } = useLanguage();

  // useChatStream hook for state machine + buffer + throttle (HARD RULE 0.3, 0.4)
  const {
    state: streamState,
    dispatch,
    startStream,
    handleSSEEvent,
    cancelStream,
    reset,
    forceFlush,
    getBufferedContent,
    confirmation,
    resetConfirmation,
  } = useChatStream({
    throttleMs: 100,
    onPhaseChange: (phase, label) => {
      console.debug("[Chat] Phase changed:", phase, label);
    },
    onComplete: (state) => {
      console.debug("[Chat] Stream complete");
    },
    onError: (error) => {
      toast.error(isZh ? `错误: ${error.message}` : `Error: ${error.message}`);
    },
  });
  const streamStateRef = useRef(streamState); // ref for stale closure fix in onDone

  const {
    sessions,
    currentSession,
    messages: sessionMessages,
    loading,
    createSession,
    switchSession,
    deleteSession,
    addMessage,
  } = useSessions();

  // Local messages state with placeholder support (HARD RULE 0.2)
  const [localMessages, setLocalMessages] = useState<ExtendedChatMessage[]>([]);
  const [placeholderId, setPlaceholderId] = useState<string | null>(null);

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
    toast.info(isZh ? '已退出作用域模式' : 'Scope cleared');
  }, [isZh, searchParams, setSearchParams]);

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

  // Sync localMessages with sessionMessages
  // NOTE: Skip sync when streaming (placeholderId is set) to prevent overwriting
  // the in-progress streaming message. After stream completes, the final message
  // is added via addMessage which triggers this sync, but we want to preserve
  // the localMessages state from onDone which has the buffered content.
  useEffect(() => {
    // Don't sync during streaming - localMessages has the streaming state
    if (placeholderId) return;

    if (sessionMessages.length > 0) {
      setLocalMessages(sessionMessages.map((m) => ({ ...m })));
    }
  }, [sessionMessages, placeholderId]);

  const handleNewSession = useCallback(async () => {
    // Disconnect current SSE if connected
    if (sseServiceRef.current) {
      sseServiceRef.current.disconnect();
    }
    const session = await createSession(isZh ? "新对话" : "New Chat");
    if (session) {
      setSessionSearchQuery('');
      setLocalMessages([]);
      setPlaceholderId(null);
      setSessionTokens(0); // 重置token计数
      setSessionCost(0); // 重置cost计数
      reset(); // Reset stream state
    }
  }, [createSession, isZh, reset]);

  const handleSwitchSession = useCallback(
    async (sessionId: string) => {
      // Disconnect current SSE if connected
      if (sseServiceRef.current) {
        sseServiceRef.current.disconnect();
      }
      await switchSession(sessionId);
      setLocalMessages([]);
      setPlaceholderId(null);
      setSessionTokens(0); // 重置token计数
      setSessionCost(0); // 重置cost计数
      reset(); // Reset stream state
    },
    [switchSession, reset],
  );

  const handleDeleteSession = useCallback(
    async (sessionId: string, e: React.MouseEvent) => {
      e.stopPropagation();
      setSessionToDelete(sessionId);
      setShowDeleteConfirm(true);
    },
    [],
  );

  const confirmDeleteSession = useCallback(async () => {
    if (!sessionToDelete) return;
    try {
      await deleteSession(sessionToDelete);
      toast.success(isZh ? "对话已删除" : "Session deleted");
    } catch (err) {
      toast.error(isZh ? "删除失败" : "Delete failed");
    }
    setShowDeleteConfirm(false);
    setSessionToDelete(null);
  }, [sessionToDelete, deleteSession, isZh]);

  const cancelDeleteSession = useCallback(() => {
    setShowDeleteConfirm(false);
    setSessionToDelete(null);
  }, []);

  // ============================================================================
  // Placeholder Message Mechanism (HARD RULE 0.2)
  // ============================================================================

  const syncStreamingMessage = useCallback((messageId: string) => {
    if (!messageId) {
      return;
    }

    const buffered = getBufferedContent();
    setLocalMessages((prev) =>
      prev.map((message) => {
        if (message.id !== messageId) {
          return message;
        }

        return {
          ...message,
          content: buffered.content,
          reasoningBuffer: buffered.reasoning,
          streamStatus: streamStateRef.current.streamStatus,
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
            title: citation.title,
            authors: citation.authors,
            year: citation.year,
            snippet: citation.snippet,
            page: citation.page,
            score: citation.score,
            content_type: citation.content_type,
          })),
        };
      }),
    );
  }, [getBufferedContent]);

  /**
   * Send message with placeholder assistant message
   *
   * Flow:
   * 1. Add user message to localMessages
   * 2. Create placeholder assistant message (temporary ID)
   * 3. Start SSE connection
   * 4. On session_start event, update placeholder with real message_id
   * 5. Stream events update placeholder in-place
   * 6. On done, finalize placeholder to completed message
   */
  const handleSend = useCallback(async () => {
    if (!input.trim() || streamState.streamStatus === "streaming" || sending)
      return;

    // D-08: Block SSE send if scope is invalid
    if (scope.type === 'error') {
      toast.error(scope.errorMessage || '当前作用域无效');
      return;
    }

    setSending(true);

    try {
      let sessionId = currentSession?.id;

      // Create session if needed
      if (!sessionId) {
        const newSession = await createSession(input.trim().substring(0, 50));
        if (!newSession) return;
        sessionId = newSession.id;
      }

      // 1. Add user message
      const userMessage: ExtendedChatMessage = {
        id: `user-${Date.now()}`,
        session_id: sessionId,
        role: "user",
        content: input.trim(),
        created_at: new Date().toISOString(),
      };

      // Add to local state and session
      setLocalMessages((prev) => [...prev, userMessage]);
      addMessage(userMessage as SessionChatMessage);

      // 2. Create placeholder assistant message (HARD RULE 0.2)
      const placeholderMessageId = `placeholder-${Date.now()}`;
      const placeholderMessage: ExtendedChatMessage = {
        id: placeholderMessageId,
        session_id: sessionId,
        role: "assistant",
        content: mode === 'agent'
          ? (isZh ? '正在分析...' : 'Analyzing...')
          : (isZh ? '正在检索...' : 'Retrieving...'),
        created_at: new Date().toISOString(),
        streamStatus: "streaming",
        reasoningBuffer: "",
        isThinkingExpanded: true, // Streaming default expanded
        toolTimeline: [],
        citations: [],
      };

      setLocalMessages((prev) => [...prev, placeholderMessage]);
      setPlaceholderId(placeholderMessageId);
      setCurrentMessageId(""); // Will be set from session_start event
      currentMessageIdRef.current = ""; // Reset ref too

      // Clear input
      setInput("");

      // 3. Start SSE connection (Sprint 3: unified API with mode + scope)
      // D-06: Add scope params to SSE body (no longer top-level paperId/kbId)
      if (!sseServiceRef.current) {
        sseServiceRef.current = new SSEService();
      }

      const streamScope =
        scope.type === 'single_paper' && scope.id
          ? {
              type: 'paper' as const,
              paper_id: scope.id,
            }
          : scope.type === 'full_kb' && scope.id
            ? {
                type: 'knowledge_base' as const,
                knowledge_base_id: scope.id,
              }
            : {
                type: 'general' as const,
              };

      streamChatMessage({
        sessionId,
        message: input.trim(),
        mode,
        scope: streamScope,
        context: {
          auto_confirm: false,
        },
        streamService: sseServiceRef.current,
        handlers: {
          onMessage: (event: SSEEvent | SSEEventEnvelope) => {
            // Handle both legacy SSEEvent and new SSEEventEnvelope format
            const legacyEvent = event as SSEEvent;
            const envelopeEvent = event as SSEEventEnvelope;

            // Get event type and message_id from either format
            const eventType = legacyEvent.type || envelopeEvent.event || "";
            const eventMessageId =
              legacyEvent.message_id || envelopeEvent.message_id || "";
            const eventData =
              legacyEvent.content || legacyEvent.data || envelopeEvent.data;

            console.debug(
              "[Chat] SSE event received:",
              eventType,
            );

            // HARD RULE 0.2: Validate message_id
            // On session_start, capture message_id and update placeholder
            if (eventType === "session_start" && eventMessageId) {
              setCurrentMessageId(eventMessageId);
              currentMessageIdRef.current = eventMessageId;
              setPlaceholderId(eventMessageId);

              // Initialize useChatStream's message_id tracking (HARD RULE 0.2)
              const sessionId = eventData?.session_id || "";
              const taskType = eventData?.task_type || "general";
              startStream(sessionId, taskType, eventMessageId);

              // Update placeholder ID to real message_id
              setLocalMessages((prev) =>
                prev.map((m) =>
                  m.id === placeholderMessageId
                    ? { ...m, id: eventMessageId }
                    : m,
                ),
              );
              return;
            }

            // Skip events without message_id (except heartbeat)
            if (!eventMessageId && eventType !== "heartbeat") {
              console.warn(
                "[Chat] Event missing message_id, ignoring:",
                eventType,
              );
              return;
            }

            // HARD RULE 0.2: Ignore events with wrong message_id
            if (
              eventMessageId &&
              currentMessageIdRef.current &&
              eventMessageId !== currentMessageIdRef.current
            ) {
              console.warn(
                "[Chat] Event message_id mismatch. Expected:",
                currentMessageId,
                "Got:",
                eventMessageId,
              );
              return;
            }

            // Convert to SSEEventEnvelope and handle
            handleSSEEvent({
              message_id: eventMessageId,
              event_type: eventType,
              data: eventData,
              timestamp: legacyEvent.timestamp
                ? new Date(legacyEvent.timestamp).getTime()
                : Date.now(),
            });
            syncStreamingMessage(currentMessageIdRef.current || eventMessageId);
          },
          onError: (error: Error) => {
            console.error("[Chat] SSE error:", error);
            forceFlush();

            // Update placeholder to error state
            const errorMsgId = currentMessageIdRef.current;
            setLocalMessages((prev) =>
              prev.map((m) =>
                m.id === errorMsgId
                  ? { ...m, streamStatus: "error" }
                  : m,
              ),
            );

            setAgentUIState("DONE");
            toast.error(isZh ? "发送消息失败" : "Failed to send message");
          },
          onDone: (data) => {
            console.debug("[Chat] SSE stream done");

            // Capture buffered content BEFORE forceFlush (which clears refs)
            const finalBuffered = getBufferedContent();
            console.debug("[Chat] onDone buffered content length:", finalBuffered.content.length);

            forceFlush();

            const doneMsgId = currentMessageIdRef.current;
            // Update placeholder to completed state
            setLocalMessages((prev) =>
              prev.map((m) => {
                if (m.id !== doneMsgId) return m;

                const finalContent = finalBuffered.content || streamStateRef.current.contentBuffer;
                const finalReasoning = finalBuffered.reasoning || streamStateRef.current.reasoningBuffer;

                const finalMessage: ExtendedChatMessage = {
                  ...m,
                  content: finalContent,
                  reasoningBuffer: finalReasoning,
                  streamStatus: "completed",
                  tokensUsed:
                    data?.tokens_used || streamStateRef.current.tokensUsed,
                  cost: data?.cost || streamStateRef.current.cost,
                  toolTimeline: streamStateRef.current.toolTimeline,
                  citations: streamStateRef.current.citations,
                };

                // Add to session as final message
                addMessage({
                  id: m.id,
                  session_id: m.session_id,
                  role: "assistant",
                  content: finalContent,
                  created_at: new Date().toISOString(),
                } as SessionChatMessage);

                return finalMessage;
              }),
            );

            // Update session totals
            setSessionTokens(
              (prev) =>
                prev + (data?.tokens_used || streamStateRef.current.tokensUsed),
            );
            setSessionCost(
              (prev) => prev + (data?.cost || streamStateRef.current.cost),
            );

            setPlaceholderId(null);
            setAgentUIState("DONE");
          },
        },
      });
    } catch (error) {
      console.error("[Chat] Send error:", error);
      toast.error(isZh ? "发送消息失败" : "Failed to send message");

      // Remove placeholder on error
      setLocalMessages((prev) => prev.filter((m) => m.id !== placeholderId));
      setPlaceholderId(null);
    } finally {
      setSending(false);
    }
  }, [
    input,
    streamState,
    sending,
    currentSession,
    createSession,
    addMessage,
    handleSSEEvent,
    forceFlush,
    getBufferedContent,
    isZh,
    placeholderId,
    currentMessageId,
    startStream,
    scope,
    mode,
  ]);

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

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [localMessages, streamState.contentBuffer]);

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
        onMessage: (event: SSEEvent | SSEEventEnvelope) => {
          const legacyEvent = event as SSEEvent;
          const envelopeEvent = event as SSEEventEnvelope;
          const eventType = legacyEvent.type || envelopeEvent.event || '';
          const eventMessageId = legacyEvent.message_id || envelopeEvent.message_id || '';
          const eventData = legacyEvent.content || legacyEvent.data || envelopeEvent.data;

          // Feed events back into useChatStream
          handleSSEEvent({
            message_id: eventMessageId,
            event_type: eventType,
            data: eventData,
            timestamp: legacyEvent.timestamp
              ? new Date(legacyEvent.timestamp).getTime()
              : Date.now(),
          });

          syncStreamingMessage(currentMessageIdRef.current || eventMessageId);
        },
        onError: (error) => {
          console.error('[Chat] Confirmation stream error:', error);
          toast.error(isZh ? '确认后恢复失败' : 'Failed to resume after confirmation');
        },
        onDone: () => {
          console.debug('[Chat] Confirmation stream done');
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

  // Handle stop button click
  const handleStop = useCallback(() => {
    if (sseServiceRef.current) {
      sseServiceRef.current.disconnect();
      cancelStream("User stopped");
      forceFlush();

      // Update placeholder to cancelled state
      const cancelMsgId = currentMessageIdRef.current;
      setLocalMessages((prev) =>
        prev.map((m) =>
          m.id === cancelMsgId
            ? { ...m, streamStatus: "cancelled" }
            : m,
        ),
      );

      setAgentUIState("DONE");
      setPlaceholderId(null);
    }
  }, [cancelStream, forceFlush, placeholderId, currentMessageId]);

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

      const page = citation.page || 1;
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
    <div className="h-full flex font-sans bg-background text-foreground">
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        className="flex-shrink-0"
      >
        <SessionSidebar
          sessions={filteredSessions}
          currentSessionId={currentSession?.id ?? null}
          loading={loading}
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
      </motion.div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full bg-background min-w-0">
        <div className="px-6 py-3 border-b border-zinc-200 flex items-center justify-between bg-background">
          <div className="flex items-center gap-3">
            <Bot className="w-4 h-4 text-primary" />
            <h2 className="font-serif text-[15px] font-bold truncate tracking-tight">
              {currentSession?.title || t.newChat}
            </h2>
          </div>
        </div>

        {/* D-03: Scope banner - below header, above messages */}
        <ScopeBanner
          type={scope.type}
          title={scope.title}
          errorMessage={scope.errorMessage}
          onExitScope={handleExitScope}
        />

        <MessageFeed
          localMessages={localMessages}
          streamState={streamState}
          currentMessageId={currentMessageId}
          thinkingSteps={thinkingSteps}
          labels={{
            noMessages: t.noMessages,
            sendFirst: t.sendFirst,
            thinking: t.thinking,
            stop: t.stop,
          }}
          messagesEndRef={messagesEndRef}
          onCitationClick={handleCitationClick}
          onStop={handleStop}
          formatTime={formatTime}
        />

        <ComposerInput
          scopeType={scope.type}
          isZh={isZh}
          mode={mode}
          input={input}
          disabled={streamState.streamStatus === 'streaming' || sending}
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
        />
      </div>

      {/* Right Sidebar: Agent State + Activity Panel */}
      <AnimatePresence>
        {showRightPanel && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="w-[300px] border-l border-zinc-200 flex-shrink-0 hidden xl:block bg-zinc-50/60"
          >
            {/* Agent State Sidebar - Phase 4.1: Data source priority */}
            <AgentStateSidebar
              selectedMessage={selectedMessage}
              currentRunningState={
                streamState.streamStatus === "streaming"
                  ? streamState
                  : undefined
              }
              onStop={handleStop}
            />

            {/* Token Monitor - session level */}
            {sessionTokens > 0 && (
              <div className="border-t border-border/50 p-4">
                <TokenMonitor
                  tokens={sessionTokens}
                  cost={sessionCost}
                  limit={128000}
                />
              </div>
            )}
          </motion.div>
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

      {/* Toggle Right Panel Button (when hidden) */}
      {!showRightPanel && (
        <button
          onClick={() => setShowRightPanel(true)}
          className="absolute right-4 top-4 w-8 h-8 border border-zinc-300 bg-white hover:bg-zinc-100 flex items-center justify-center hidden xl:flex z-10"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
