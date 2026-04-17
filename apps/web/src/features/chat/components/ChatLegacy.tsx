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
  Plus,
  Search,
  Send,
  Bot,
  Trash2,
  AlertCircle,
  Loader2,
  User,
  MessageSquare,
  ChevronLeft,
  Square,
} from "lucide-react";
import { clsx } from "clsx";
import { useLanguage } from "@/app/contexts/LanguageContext";
import {
  useChatStream,
  ChatStreamState,
  StreamStatus,
} from "@/app/hooks/useChatStream";
import {
  useSessions,
  ChatMessage as SessionChatMessage,
} from "@/app/hooks/useSessions";
import { ChatMessage as RichChatMessage } from "@/app/components/ChatMessageCard";
import { ThinkingProcess, ThinkingStep } from "@/app/components/ThinkingProcess";
import { TypingText } from "@/app/components/TypingText";
import { ToolCallCard } from "@/app/components/ToolCallCard";
import {
  CitationsPanel,
  renderContentWithCitations,
} from "@/app/components/CitationsPanel";
import { TokenMonitor } from "@/app/components/TokenMonitor";
import { ConfirmationDialog } from "@/app/components/ConfirmationDialog";
import { ConfirmDialog } from "@/app/components/ConfirmDialog";
import {
  AgentStateSidebar,
  AgentUIState,
  ExecutionStep,
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

// ============================================================================
// Extended ChatMessage for UI State
// ============================================================================

/**
 * Tool timeline item for tracking tool calls
 */
interface ToolTimelineItem {
  id: string;
  tool: string;
  label: string;
  status: "pending" | "running" | "success" | "error";
  startedAt: number;
  completedAt?: number;
  duration?: number;
  summary?: string;
}

/**
 * Citation item for reference tracking
 */
interface CitationItem {
  paper_id: string;
  title: string;
  authors?: string[];
  year?: number;
  snippet?: string;
  page?: number;
  score?: number;
  content_type?: "text" | "table" | "figure";
  chunk_id?: string;
}

/**
 * Extended ChatMessage with streaming state
 * Used for placeholder message mechanism
 */
interface ExtendedChatMessage extends SessionChatMessage {
  /** Stream status for placeholder messages */
  streamStatus?: StreamStatus;
  /** Reasoning buffer for think panel */
  reasoningBuffer?: string;
  /** Whether thinking panel is expanded */
  isThinkingExpanded?: boolean;
  /** Tool timeline items */
  toolTimeline?: ToolTimelineItem[];
  /** Citations */
  citations?: CitationItem[];
  /** Token usage */
  tokensUsed?: number;
  /** Cost */
  cost?: number;
}

export function ChatLegacy() {
  const navigate = useNavigate();
  const [input, setInput] = useState("");
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

            // Update placeholder message with stream state
            // NOTE: Use currentMessageIdRef.current (synchronous ref) instead of
            // placeholderId/currentMessageId (stale closure state) for message matching.
            // Use getBufferedContent() for content (state + pending buffer) since
            // throttle delays the reducer dispatch.
            const streamingMsgId = currentMessageIdRef.current;
            const buffered = getBufferedContent();

            // DEBUG: Log matching
            console.debug("[Chat] setLocalMessages update, streamingMsgId:", streamingMsgId);

            setLocalMessages((prev) => {
              // DEBUG: Log prev messages
              console.debug("[Chat] setLocalMessages prev messages count:", prev.length);
              return prev.map((m) => {
                if (m.id !== streamingMsgId) return m;

                // Build updated message from buffered content (state + pending buffer)
                const updated: ExtendedChatMessage = {
                  ...m,
                  content: buffered.content,
                  reasoningBuffer: buffered.reasoning,
                  streamStatus: streamStateRef.current.streamStatus,
                  toolTimeline: safeToolTimeline(streamStateRef.current.toolTimeline).map((t) => ({
                    id: t.id,
                    tool: t.tool,
                    label: t.label,
                    status: t.status,
                    startedAt: t.startedAt,
                    completedAt: t.completedAt,
                    duration: t.duration,
                    summary: t.summary,
                  })),
                  citations: safeCitations(streamStateRef.current.citations).map((c) => ({
                    paper_id: c.paper_id,
                    title: c.title,
                    authors: c.authors,
                    year: c.year,
                    snippet: c.snippet,
                    page: c.page,
                    score: c.score,
                    content_type: c.content_type,
                  })),
                };

                console.debug("[Chat] Updated message:", updated.id);
                return updated;
              });
            });
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

  // Compute execution steps for sidebar from tool timeline
  const executionSteps = useMemo<ExecutionStep[]>(() => {
    return safeToolTimeline(streamState.toolTimeline).map((item) => ({
      tool: item.tool,
      action: item.label || item.tool,
      status:
        item.status === "running"
          ? "running"
          : item.status === "success"
            ? "completed"
            : item.status === "error"
              ? "failed"
              : "running",
      timestamp: item.startedAt,
      duration: item.completedAt
        ? item.completedAt - item.startedAt
        : undefined,
    }));
  }, [streamState.toolTimeline]);

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
          });
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
  }, [confirmation, currentSession, handleSSEEvent, resetConfirmation, isZh]);

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
    (index: number) => {
      // Get the citation at this index
      const citation = streamState.citations[index];
      if (citation) {
        if (!citation.paper_id) {
          toast.warning(isZh ? '引用缺少论文 ID，无法跳转' : 'Citation is missing paper id');
          return;
        }
        // Navigate to read page with the specific page number
        const page = citation.page || 1;
        navigate(`/read/${citation.paper_id}?page=${page}`);
      }
    },
    [streamState.citations, navigate, isZh],
  );

  // Toggle thinking panel expand/collapse
  const toggleExpand = useCallback((messageId: string) => {
    setLocalMessages((prev) =>
      prev.map((m) =>
        m.id === messageId
          ? { ...m, isThinkingExpanded: !m.isThinkingExpanded }
          : m,
      ),
    );
  }, []);

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString(isZh ? "zh-CN" : "en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="h-full flex font-sans bg-background text-foreground">
      {/* Left Sidebar: Sessions */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        className="w-[260px] border-r border-border/50 flex flex-col h-full bg-muted/20"
      >
        <div className="px-4 py-3 border-b border-border/50 flex items-center justify-between bg-background/80 backdrop-blur-md">
          <div>
            <h2 className="font-serif text-lg font-bold">{t.terminal}</h2>
            <p className="text-xs text-muted-foreground">{t.sessions}</p>
          </div>
          <button
            onClick={handleNewSession}
            className="w-8 h-8 rounded-lg border border-border hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all flex items-center justify-center"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        <div className="px-3 py-2 border-b border-border/50">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder={t.search}
              className="w-full bg-card border border-border rounded-lg pl-8 pr-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-2 px-2">
          <div className="text-xs font-medium text-muted-foreground mb-2 px-2">
            {t.history}
          </div>

          {loading && safeSessions.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : safeSessions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">
              {t.newChat}
            </div>
          ) : (
            <div className="space-y-1">
              {safeSessions.map((session) => (
                <div
                  key={session.id}
                  onClick={() => handleSwitchSession(session.id)}
                  className={clsx(
                    "w-full text-left px-3 py-2.5 rounded-lg transition-all group flex items-start gap-2 cursor-pointer",
                    currentSession?.id === session.id
                      ? "bg-primary/10 border border-primary/30"
                      : "hover:bg-muted border border-transparent",
                  )}
                >
                  <MessageSquare className="w-4 h-4 mt-0.5 text-muted-foreground flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div
                      className={clsx(
                        "text-sm font-medium truncate",
                        currentSession?.id === session.id
                          ? "text-primary"
                          : "text-foreground",
                      )}
                    >
                      {session.title}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {session.messageCount} {isZh ? "条消息" : "messages"}
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDeleteSession(session.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-destructive/20 rounded transition-opacity flex-shrink-0"
                  >
                    <Trash2 className="w-3.5 h-3.5 text-muted-foreground hover:text-destructive" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </motion.div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full bg-background min-w-0">
        <div className="px-6 py-3 border-b border-border/50 flex items-center justify-between bg-background/90 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <Bot className="w-5 h-5 text-primary" />
            <h2 className="font-serif text-base font-bold truncate">
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

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {localMessages.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center h-full text-center">
              <Bot className="w-16 h-16 text-primary/20 mb-4" />
              <p className="text-lg font-serif text-muted-foreground mb-2">
                {t.noMessages}
              </p>
              <p className="text-sm text-muted-foreground/60">{t.sendFirst}</p>
            </div>
          ) : (
            <div className="space-y-6 max-w-4xl mx-auto">
              {localMessages
                .filter((m) => m.role === "user" || m.role === "assistant")
                .map((msg) => {
                  const isStreaming = msg.streamStatus === "streaming";
                  const isPlaceholder =
                    msg.id.startsWith("placeholder-") ||
                    msg.id === currentMessageId;

                  return (
                    <div
                      key={msg.id}
                      className={clsx(
                        "flex gap-3",
                        msg.role === "user" ? "justify-end" : "justify-start",
                      )}
                    >
                      {msg.role === "assistant" && (
                        <div className="w-8 h-8 flex items-center justify-center flex-shrink-0 border-b border-ink/20 mt-4 mb-auto">
                          <span className="font-serif text-[10px] font-black uppercase tracking-widest text-ink">AI</span>
                        </div>
                      )}

                      <div className="flex-1 max-w-[80%] space-y-4">
                        {/* Thinking Process for streaming messages */}
                        {isStreaming &&
                          (msg.reasoningBuffer ||
                            streamState.reasoningBuffer) &&
                          msg.isThinkingExpanded && (
                            <div className="mt-4">
                            <ThinkingProcess
                              steps={thinkingSteps}
                              duration={
                                ((streamState.endedAt || Date.now()) -
                                (streamState.startedAt || Date.now())) / 1000
                              }
                              onComplete={() => {}}
                              autoCollapse={true}
                            />
                            </div>
                          )}

                        {/* Tool Call Cards for streaming messages */}
                        {isStreaming &&
                          ((msg.toolTimeline?.length ?? 0) > 0 ||
                            streamState.toolTimeline.length > 0) && (
                            <div className="space-y-2">
                              {safeToolTimeline(
                                msg.toolTimeline || streamState.toolTimeline
                              ).map((tc) => (
                                <ToolCallCard
                                  key={tc.id}
                                  toolCall={{
                                    id: tc.id,
                                    tool: tc.tool,
                                    parameters: {},
                                    status: tc.status,
                                    startedAt: tc.startedAt,
                                    completedAt: tc.completedAt,
                                    duration: tc.duration,
                                    result: tc.summary,
                                  }}
                                />
                              ))}
                            </div>
                          )}

                        {/* Message Content */}
                        <div
                           className={clsx(
                            "max-w-full font-serif text-[15px] leading-loose py-4 px-2",
                            msg.role === "user"
                              ? "font-bold text-right bg-transparent rounded-none shadow-none text-foreground text-lg leading-relaxed relative border-b-2 border-transparent"
                              : "bg-transparent text-foreground rounded-none shadow-none border-l-[1px] border-black pl-6 magazine-body max-w-prose mx-auto"
                          )}
                        >
                          {((msg.citations?.length ?? 0) > 0 ||
                            streamState.citations.length > 0) &&
                          msg.content ? (
                            renderContentWithCitations(
                              msg.content,
                              handleCitationClick,
                            )
                          ) : msg.content ? (
                            isStreaming ? (
                              <TypingText
                                text={msg.content}
                                className="text-[15px] leading-loose"
                              />
                            ) : (
                              <div className="text-[15px] leading-loose whitespace-pre-wrap">
                                {msg.content}
                              </div>
                            )
                          ) : isStreaming ? (
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <Loader2 className="w-4 h-4 animate-spin" />
                              {t.thinking}
                            </div>
                          ) : null}

                          <div
                            className={clsx(
                              "text-[10px] font-mono tracking-widest mt-2 uppercase",
                              msg.role === "user"
                                ? "text-ink/40"
                                : "text-ink/40",
                            )}
                          >
                            {formatTime(msg.created_at)}
                          </div>
                        </div>

                        {/* Citations Panel */}
                        {((msg.citations?.length ?? 0) > 0 ||
                          (isPlaceholder &&
                            streamState.citations.length > 0)) && (
                          <CitationsPanel
                            citations={safeCitations(
                              msg.citations || streamState.citations
                            ).map((c) => ({
                              paper_id: c.paper_id,
                              title: c.title,
                              authors: c.authors || [],
                              year: c.year || 0,
                              page: c.page || 0,
                              snippet: c.snippet || "",
                              score: c.score || 0,
                              content_type: c.content_type || "text",
                              chunk_id: c.chunk_id,
                            }))}
                          />
                        )}

                        {/* Message-level token usage */}
                        {(msg.tokensUsed || streamState.tokensUsed) &&
                          !isStreaming && (
                            <div className="text-xs text-muted-foreground font-mono mt-1">
                              Token:{" "}
                              {(
                                msg.tokensUsed || streamState.tokensUsed
                              ).toLocaleString()}
                              {(msg.cost || streamState.cost) > 0 &&
                                ` · ¥${(msg.cost || streamState.cost).toFixed(4)}`}
                            </div>
                          )}

                        {/* Stop button for streaming messages */}
                        {isStreaming && (
                          <button
                            onClick={handleStop}
                            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-muted hover:bg-muted/80 text-sm text-muted-foreground hover:text-foreground transition-colors"
                          >
                            <Square className="w-3 h-3" />
                            {t.stop}
                          </button>
                        )}
                      </div>

                      {msg.role === "user" && (
                        <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
                          <User className="w-4 h-4 text-muted-foreground" />
                        </div>
                      )}
                    </div>
                  );
                })}

              {/* Scroll anchor */}
              <div ref={messagesEndRef} />
            </div>
          )}

          {streamState.error && (
            <div className="flex items-center gap-2 text-destructive text-sm bg-destructive/10 px-4 py-2 rounded-lg mt-4 max-w-4xl mx-auto">
              <AlertCircle className="w-4 h-4" />
              {streamState.error.message}
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="px-6 py-4 border-t border-border/50 bg-background/80 backdrop-blur-md">
          <div className="max-w-4xl mx-auto">
            {/* Sprint 3: Mode selector */}
            {scope.type !== null && (
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs text-muted-foreground">
                  {isZh ? "模式" : "Mode"}:
                </span>
                <div className="flex rounded-lg border border-border overflow-hidden text-xs">
                  {[
                    { value: 'auto' as const, label: isZh ? '自动' : 'Auto' },
                    { value: 'rag' as const, label: isZh ? '快速问答' : 'Fast RAG' },
                    { value: 'agent' as const, label: isZh ? '深度分析' : 'Deep Agent' },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setMode(opt.value)}
                      disabled={streamState.streamStatus === "streaming"}
                      className={clsx(
                        "px-3 py-1 transition-colors",
                        mode === opt.value
                          ? "bg-primary text-primary-foreground"
                          : "bg-card hover:bg-muted text-muted-foreground"
                      )}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div className="flex items-end gap-3 bg-transparent rounded-none border-b border-ink/20 focus-within:border-ink/50 transition-colors p-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t.placeholder}
                className="flex-1 p-2 text-[15px] font-serif bg-transparent resize-none outline-none min-h-[40px] max-h-[160px] placeholder:font-sans placeholder:text-[13px] placeholder:uppercase placeholder:tracking-widest"
                rows={1}
                disabled={streamState.streamStatus === "streaming" || sending}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = "auto";
                  target.style.height = `${Math.min(target.scrollHeight, 160)}px`;
                }}
              />
              <button
                onClick={handleSend}
                disabled={
                  !input.trim() ||
                  streamState.streamStatus === "streaming" ||
                  sending
                }
                className={clsx(
                  "w-10 h-10 rounded-full flex items-center justify-center transition-all disabled:opacity-30",
                  input.trim() &&
                    streamState.streamStatus !== "streaming" &&
                    !sending
                    ? "bg-ink text-paper hover:bg-ink/80"
                    : "bg-muted text-muted-foreground",
                )}
              >
                {streamState.streamStatus === "streaming" || sending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4 -ml-0.5" />
                )}
              </button>
            </div>
            <div className="flex justify-between items-center mt-4 px-1 font-mono text-[9px] uppercase tracking-widest text-ink/40">
              <span className="flex items-center gap-1">
                <AlertCircle className="w-3 h-3" /> {t.verify}
              </span>
              <span>↵ {isZh ? "发送" : "TO SEND"}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right Sidebar: Agent State + Activity Panel */}
      <AnimatePresence>
        {showRightPanel && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="w-[320px] border-l border-border/50 flex-shrink-0 hidden xl:block flex flex-col"
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
          className="absolute right-4 top-4 w-8 h-8 rounded-lg border border-border bg-background hover:bg-muted flex items-center justify-center hidden xl:flex z-10"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
