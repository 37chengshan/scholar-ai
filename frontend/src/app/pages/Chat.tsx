/**
 * Chat Page - Placeholder Message + message_id Binding + SSE Event Handling
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

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router';
import { motion, AnimatePresence } from 'motion/react';
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
} from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';
import { useChatStream, ChatStreamState, StreamStatus } from '../hooks/useChatStream';
import { useSessions, ChatMessage as SessionChatMessage } from '../hooks/useSessions';
import { ChatMessage as RichChatMessage } from '../components/ChatMessageCard';
import { ThinkingProcess, ThinkingStep } from '../components/ThinkingProcess';
import { TypingText } from '../components/TypingText';
import { ToolCallCard } from '../components/ToolCallCard';
import { CitationsPanel, renderContentWithCitations } from '../components/CitationsPanel';
import { TokenMonitor } from '../components/TokenMonitor';
import { ConfirmationDialog } from '../components/ConfirmationDialog';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { AgentStateSidebar, AgentUIState, ExecutionStep } from '../components/AgentStateSidebar';
import { SSEService, SSEEvent, SSEEventEnvelope } from '../../services/sseService';
import { API_BASE_URL } from '@/config/api';
import { toast } from 'sonner';

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
  status: 'pending' | 'running' | 'success' | 'error';
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
  content_type?: 'text' | 'table' | 'figure';
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

export function Chat() {
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [agentUIState, setAgentUIState] = useState<AgentUIState>('IDLE');
  const [sending, setSending] = useState(false); // 防止重复发送
  const [sessionTokens, setSessionTokens] = useState(0); // 当前session的token
  const [sessionCost, setSessionCost] = useState(0); // 当前session的花费
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false); // 删除确认对话框
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null); // 待删除的会话ID
  const [currentMessageId, setCurrentMessageId] = useState<string>(''); // 当前流消息的 message_id (HARD RULE 0.2)
  const [selectedMessage, setSelectedMessage] = useState<RichChatMessage | undefined>(undefined); // Phase 4.1: 选中的历史消息
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sseServiceRef = useRef<SSEService | null>(null);

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
  } = useChatStream({
    throttleMs: 100,
    onPhaseChange: (phase, label) => {
      console.log('[Chat] Phase changed:', phase, label);
    },
    onComplete: (state) => {
      console.log('[Chat] Stream complete:', state);
    },
    onError: (error) => {
      toast.error(isZh ? `错误: ${error.message}` : `Error: ${error.message}`);
    },
  });

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

  const isZh = language === 'zh';

  const t = {
    terminal: isZh ? '终端对话' : 'Terminal',
    sessions: isZh ? '会话列表' : 'Sessions',
    search: isZh ? '搜索...' : 'Search...',
    history: isZh ? '历史记录' : 'History',
    newChat: isZh ? '新对话' : 'New Chat',
    placeholder: isZh ? '给 ScholarAI 发送消息...' : 'Message ScholarAI...',
    verify: isZh ? '请验证输出结果。' : 'Verify outputs.',
    noMessages: isZh ? '开始新对话' : 'Start a new conversation',
    sendFirst: isZh ? '发送您的第一条消息' : 'Send your first message',
    streaming: isZh ? '流式响应中...' : 'Streaming...',
    deleteConfirm: isZh ? '确定删除此对话？' : 'Delete this conversation?',
    stop: isZh ? '停止' : 'Stop',
    thinking: isZh ? '思考中...' : 'Thinking...',
  };

  // Initialize SSEService instance
  useEffect(() => {
    sseServiceRef.current = new SSEService();
    return () => {
      sseServiceRef.current?.disconnect();
    };
  }, []);

  // Sync localMessages with sessionMessages
  useEffect(() => {
    if (sessionMessages.length > 0) {
      setLocalMessages(sessionMessages.map(m => ({ ...m })));
    }
  }, [sessionMessages]);

  const handleNewSession = useCallback(async () => {
    // Disconnect current SSE if connected
    if (sseServiceRef.current) {
      sseServiceRef.current.disconnect();
    }
    const session = await createSession(isZh ? '新对话' : 'New Chat');
    if (session) {
      setLocalMessages([]);
      setPlaceholderId(null);
      setSessionTokens(0); // 重置token计数
      setSessionCost(0); // 重置cost计数
      reset(); // Reset stream state
    }
  }, [createSession, isZh, reset]);

  const handleSwitchSession = useCallback(async (sessionId: string) => {
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
  }, [switchSession, reset]);

  const handleDeleteSession = useCallback(async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSessionToDelete(sessionId);
    setShowDeleteConfirm(true);
  }, []);

  const confirmDeleteSession = useCallback(async () => {
    if (!sessionToDelete) return;
    try {
      await deleteSession(sessionToDelete);
      toast.success(isZh ? '对话已删除' : 'Session deleted');
    } catch (err) {
      toast.error(isZh ? '删除失败' : 'Delete failed');
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
    if (!input.trim() || streamState.streamStatus === 'streaming' || sending) return;

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
        role: 'user',
        content: input.trim(),
        created_at: new Date().toISOString(),
      };

      // Add to local state and session
      setLocalMessages(prev => [...prev, userMessage]);
      addMessage(userMessage as SessionChatMessage);

      // 2. Create placeholder assistant message (HARD RULE 0.2)
      const placeholderMessageId = `placeholder-${Date.now()}`;
      const placeholderMessage: ExtendedChatMessage = {
        id: placeholderMessageId,
        session_id: sessionId,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
        streamStatus: 'streaming',
        reasoningBuffer: '',
        isThinkingExpanded: true, // Streaming default expanded
        toolTimeline: [],
        citations: [],
      };

      setLocalMessages(prev => [...prev, placeholderMessage]);
      setPlaceholderId(placeholderMessageId);
      setCurrentMessageId(''); // Will be set from session_start event

      // Clear input
      setInput('');

      // 3. Start SSE connection
      const url = `${API_BASE_URL}/api/v1/chat/stream`;
      const body = {
        message: input.trim(),
        session_id: sessionId,
      };

      if (!sseServiceRef.current) {
        sseServiceRef.current = new SSEService();
      }

      sseServiceRef.current.connect(url, {
        onMessage: (event: SSEEvent | SSEEventEnvelope) => {
          // Handle both legacy SSEEvent and new SSEEventEnvelope format
          const legacyEvent = event as SSEEvent;
          const envelopeEvent = event as SSEEventEnvelope;

          // Get event type and message_id from either format
          const eventType = legacyEvent.type || envelopeEvent.event || '';
          const eventMessageId = legacyEvent.message_id || envelopeEvent.message_id || '';
          const eventData = legacyEvent.content || legacyEvent.data || envelopeEvent.data;

          console.log('[Chat] SSE event received:', eventType, eventMessageId);

          // HARD RULE 0.2: Validate message_id
          // On session_start, capture message_id and update placeholder
          if (eventType === 'session_start' && eventMessageId) {
            setCurrentMessageId(eventMessageId);
            setPlaceholderId(eventMessageId);

            // Update placeholder ID to real message_id
            setLocalMessages(prev => prev.map(m =>
              m.id === placeholderMessageId
                ? { ...m, id: eventMessageId }
                : m
            ));
            return;
          }

          // Skip events without message_id (except heartbeat)
          if (!eventMessageId && eventType !== 'heartbeat') {
            console.warn('[Chat] Event missing message_id, ignoring:', eventType);
            return;
          }

          // HARD RULE 0.2: Ignore events with wrong message_id
          if (eventMessageId && currentMessageId && eventMessageId !== currentMessageId) {
            console.warn('[Chat] Event message_id mismatch. Expected:', currentMessageId, 'Got:', eventMessageId);
            return;
          }

          // Convert to SSEEventEnvelope and handle
          handleSSEEvent({
            message_id: eventMessageId,
            event_type: eventType,
            data: eventData,
            timestamp: legacyEvent.timestamp ? new Date(legacyEvent.timestamp).getTime() : Date.now(),
          });

          // Update placeholder message with stream state
          setLocalMessages(prev => prev.map(m => {
            if (m.id !== (placeholderId || currentMessageId)) return m;

            // Build updated message from stream state
            const updated: ExtendedChatMessage = {
              ...m,
              content: streamState.contentBuffer,
              reasoningBuffer: streamState.reasoningBuffer,
              streamStatus: streamState.streamStatus,
              toolTimeline: streamState.toolTimeline.map(t => ({
                id: t.id,
                tool: t.tool,
                label: t.label,
                status: t.status,
                startedAt: t.startedAt,
                completedAt: t.completedAt,
                duration: t.duration,
                summary: t.summary,
              })),
              citations: streamState.citations.map(c => ({
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

            return updated;
          }));
        },
        onError: (error: Error) => {
          console.error('[Chat] SSE error:', error);
          forceFlush();

          // Update placeholder to error state
          setLocalMessages(prev => prev.map(m =>
            m.id === (placeholderId || currentMessageId)
              ? { ...m, streamStatus: 'error' }
              : m
          ));

          setAgentUIState('DONE');
          toast.error(isZh ? '发送消息失败' : 'Failed to send message');
        },
        onDone: (data) => {
          console.log('[Chat] SSE stream done');
          forceFlush();

          // Update placeholder to completed state
          setLocalMessages(prev => prev.map(m => {
            if (m.id !== (placeholderId || currentMessageId)) return m;

            const finalMessage: ExtendedChatMessage = {
              ...m,
              content: streamState.contentBuffer,
              reasoningBuffer: streamState.reasoningBuffer,
              streamStatus: 'completed',
              tokensUsed: data?.tokens_used || streamState.tokensUsed,
              cost: data?.cost || streamState.cost,
              toolTimeline: streamState.toolTimeline,
              citations: streamState.citations,
            };

            // Add to session as final message
            addMessage({
              id: m.id,
              session_id: m.session_id,
              role: 'assistant',
              content: streamState.contentBuffer,
              created_at: new Date().toISOString(),
            } as SessionChatMessage);

            return finalMessage;
          }));

          // Update session totals
          setSessionTokens(prev => prev + (data?.tokens_used || streamState.tokensUsed));
          setSessionCost(prev => prev + (data?.cost || streamState.cost));

          setPlaceholderId(null);
          setAgentUIState('DONE');
        },
      }, body);

    } catch (error) {
      console.error('[Chat] Send error:', error);
      toast.error(isZh ? '发送消息失败' : 'Failed to send message');

      // Remove placeholder on error
      setLocalMessages(prev => prev.filter(m => m.id !== placeholderId));
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
    isZh,
    placeholderId,
    currentMessageId,
  ]);

  // ============================================================================
  // UI Effects
  // ============================================================================

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [localMessages, streamState.contentBuffer]);

  // Update agent UI state based on stream state
  useEffect(() => {
    if (streamState.streamStatus === 'streaming') {
      setAgentUIState('RUNNING');
    } else if (streamState.streamStatus === 'completed') {
      setAgentUIState('DONE');
    } else if (streamState.streamStatus === 'error') {
      setAgentUIState('DONE');
    } else {
      setAgentUIState('IDLE');
    }
  }, [streamState.streamStatus]);

  // Compute thinking steps from reasoning buffer
  const thinkingSteps = useMemo<ThinkingStep[]>((): ThinkingStep[] => {
    if (!streamState.reasoningBuffer) return [];

    // Split reasoning buffer into steps
    const lines = streamState.reasoningBuffer.split('\n').filter(Boolean);
    return lines.map((line, idx) => ({
      type: 'thinking',
      content: line,
      timestamp: streamState.startedAt ? streamState.startedAt + idx * 100 : undefined,
    }));
  }, [streamState.reasoningBuffer, streamState.startedAt]);

  // Compute execution steps for sidebar from tool timeline
  const executionSteps = useMemo<ExecutionStep[]>(() => {
    return streamState.toolTimeline.map(item => ({
      tool: item.tool,
      action: item.label || item.tool,
      status: item.status === 'running' ? 'running' :
              item.status === 'success' ? 'completed' :
              item.status === 'error' ? 'failed' : 'running',
      timestamp: item.startedAt,
      duration: item.completedAt ? item.completedAt - item.startedAt : undefined,
    }));
  }, [streamState.toolTimeline]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Handle stop button click
  const handleStop = useCallback(() => {
    if (sseServiceRef.current) {
      sseServiceRef.current.disconnect();
      cancelStream('User stopped');
      forceFlush();

      // Update placeholder to cancelled state
      setLocalMessages(prev => prev.map(m =>
        m.id === (placeholderId || currentMessageId)
          ? { ...m, streamStatus: 'cancelled' }
          : m
      ));

      setAgentUIState('DONE');
      setPlaceholderId(null);
    }
  }, [cancelStream, forceFlush, placeholderId, currentMessageId]);

  // Citation click handler — navigate to read page with specific page
  const handleCitationClick = useCallback((index: number) => {
    // Get the citation at this index
    const citation = streamState.citations[index];
    if (citation) {
      // Navigate to read page with the specific page number
      const page = citation.page || 1;
      navigate(`/read/${citation.paper_id}?page=${page}`);
    }
  }, [streamState.citations, navigate]);

  // Toggle thinking panel expand/collapse
  const toggleExpand = useCallback((messageId: string) => {
    setLocalMessages(prev => prev.map(m =>
      m.id === messageId
        ? { ...m, isThinkingExpanded: !m.isThinkingExpanded }
        : m
    ));
  }, []);

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString(isZh ? 'zh-CN' : 'en-US', {
      hour: '2-digit',
      minute: '2-digit',
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
          
          {loading && sessions.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">
              {t.newChat}
            </div>
          ) : (
            <div className="space-y-1">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  onClick={() => handleSwitchSession(session.id)}
                  className={clsx(
                    'w-full text-left px-3 py-2.5 rounded-lg transition-all group flex items-start gap-2 cursor-pointer',
                    currentSession?.id === session.id
                      ? 'bg-primary/10 border border-primary/30'
                      : 'hover:bg-muted border border-transparent'
                  )}
                >
                  <MessageSquare className="w-4 h-4 mt-0.5 text-muted-foreground flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className={clsx(
                      'text-sm font-medium truncate',
                      currentSession?.id === session.id ? 'text-primary' : 'text-foreground'
                    )}>
                      {session.title}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {session.messageCount} {isZh ? '条消息' : 'messages'}
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

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {localMessages.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center h-full text-center">
              <Bot className="w-16 h-16 text-primary/20 mb-4" />
              <p className="text-lg font-serif text-muted-foreground mb-2">{t.noMessages}</p>
              <p className="text-sm text-muted-foreground/60">{t.sendFirst}</p>
            </div>
          ) : (
            <div className="space-y-4 max-w-4xl mx-auto">
              {localMessages.filter(m => m.role === 'user' || m.role === 'assistant').map((msg) => {
                const isStreaming = msg.streamStatus === 'streaming';
                const isPlaceholder = msg.id.startsWith('placeholder-') || msg.id === currentMessageId;

                return (
                  <div key={msg.id} className={clsx(
                    'flex gap-3',
                    msg.role === 'user' ? 'justify-end' : 'justify-start'
                  )}>
                    {msg.role === 'assistant' && (
                      <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <Bot className="w-4 h-4 text-primary" />
                      </div>
                    )}

                    <div className="flex-1 max-w-[80%] space-y-2">
                      {/* Thinking Process for streaming messages */}
                      {isStreaming && (msg.reasoningBuffer || streamState.reasoningBuffer) && msg.isThinkingExpanded && (
                        <ThinkingProcess
                          steps={thinkingSteps}
                          duration={(streamState.endedAt || Date.now()) - (streamState.startedAt || Date.now()) / 1000}
                          onComplete={() => {}}
                          autoCollapse={true}
                        />
                      )}

                      {/* Tool Call Cards for streaming messages */}
                      {isStreaming && ((msg.toolTimeline?.length ?? 0) > 0 || streamState.toolTimeline.length > 0) && (
                        <div className="space-y-2">
                          {(msg.toolTimeline || streamState.toolTimeline).map(tc => (
                            <ToolCallCard key={tc.id} toolCall={{
                              id: tc.id,
                              tool: tc.tool,
                              parameters: {},
                              status: tc.status,
                              startedAt: tc.startedAt,
                              completedAt: tc.completedAt,
                              duration: tc.duration,
                              result: tc.summary,
                            }} />
                          ))}
                        </div>
                      )}

                      {/* Message Content */}
                      <div className={clsx(
                        'max-w-[100%] rounded-2xl px-4 py-3',
                        msg.role === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted'
                      )}>
                        {((msg.citations?.length ?? 0) > 0 || streamState.citations.length > 0) && msg.content ? (
                          renderContentWithCitations(msg.content, handleCitationClick)
                        ) : msg.content ? (
                          isStreaming ? (
                            <TypingText text={msg.content} className="text-sm" />
                          ) : (
                            <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                          )
                        ) : isStreaming ? (
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            {t.thinking}
                          </div>
                        ) : null}

                        <div className={clsx(
                          'text-xs mt-1.5',
                          msg.role === 'user' ? 'text-primary-foreground/70' : 'text-muted-foreground'
                        )}>
                          {formatTime(msg.created_at)}
                        </div>
                      </div>

                      {/* Citations Panel */}
                      {((msg.citations?.length ?? 0) > 0 || (isPlaceholder && streamState.citations.length > 0)) && (
                        <CitationsPanel citations={(msg.citations || streamState.citations).map(c => ({
                          paper_id: c.paper_id,
                          title: c.title,
                          authors: c.authors || [],
                          year: c.year || 0,
                          page: c.page || 0,
                          snippet: c.snippet || '',
                          score: c.score || 0,
                          content_type: c.content_type || 'text',
                          chunk_id: c.chunk_id,
                        }))} />
                      )}

                      {/* Message-level token usage */}
                      {(msg.tokensUsed || streamState.tokensUsed) && !isStreaming && (
                        <div className="text-xs text-muted-foreground font-mono mt-1">
                          Token: {(msg.tokensUsed || streamState.tokensUsed).toLocaleString()}
                          {(msg.cost || streamState.cost) > 0 && ` · ¥${(msg.cost || streamState.cost).toFixed(4)}`}
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

                    {msg.role === 'user' && (
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
            <div className="flex items-end gap-3 bg-card rounded-xl border border-border p-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t.placeholder}
                className="flex-1 p-2 text-sm bg-transparent resize-none focus:outline-none min-h-[40px] max-h-[120px]"
                rows={1}
                disabled={streamState.streamStatus === 'streaming' || sending}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
                }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || streamState.streamStatus === 'streaming' || sending}
                className={clsx(
                  'w-10 h-10 rounded-lg flex items-center justify-center transition-all',
                  input.trim() && streamState.streamStatus !== 'streaming' && !sending
                    ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                    : 'bg-muted text-muted-foreground'
                )}
              >
                {streamState.streamStatus === 'streaming' || sending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </div>
            <div className="flex justify-between items-center mt-2 px-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <AlertCircle className="w-3 h-3" /> {t.verify}
              </span>
              <span>Return {isZh ? '发送' : 'to send'}</span>
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
              currentRunningState={streamState.streamStatus === 'streaming' ? streamState : undefined}
              onStop={handleStop}
            />

            {/* Token Monitor - session level */}
            {sessionTokens > 0 && (
              <div className="border-t border-border/50 p-4">
                <TokenMonitor tokens={sessionTokens} cost={sessionCost} limit={128000} />
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Confirmation Dialog for agent approval - TODO: implement with new state management */}
      {/* Delete Session Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title={isZh ? '删除对话' : 'Delete Session'}
        message={isZh ? '确定要删除这个对话吗？删除后将无法恢复。' : 'Are you sure you want to delete this session? This cannot be undone.'}
        confirmLabel={isZh ? '删除' : 'Delete'}
        cancelLabel={isZh ? '取消' : 'Cancel'}
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
