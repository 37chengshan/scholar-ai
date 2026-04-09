/**
 * Chat Page - SSE Streaming with Citations & Session Persistence
 *
 * Main chat interface with:
 * - SSE streaming for real-time AI responses (MarkdownRenderer, D-01)
 * - Session persistence (create, load, switch, delete)
 * - Agent activity panel (tool calls, thoughts, stats)
 * - Thinking process visualization with auto-collapse (D-02, D-03)
 * - Tool call cards (D-04)
 * - Citations panel with inline markers (D-05)
 * - Token monitoring (D-06)
 * - Confirmation dialog for agent approval
 *
 * Part of Agent-Native architecture (D-18, D-19, D-20, D-21)
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
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
} from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';
import { useSSE } from '../hooks/useSSE';
import { useSessions, ChatMessage } from '../hooks/useSessions';
import { ThinkingProcess, ThinkingStep } from '../components/ThinkingProcess';
import { MarkdownRenderer } from '../components/MarkdownRenderer';
import { ToolCallCard } from '../components/ToolCallCard';
import { CitationsPanel, renderContentWithCitations } from '../components/CitationsPanel';
import { TokenMonitor } from '../components/TokenMonitor';
import { ConfirmationDialog } from '../components/ConfirmationDialog';
import { AgentStateSidebar, AgentUIState, ExecutionStep } from '../components/AgentStateSidebar';
import { SSEEvent } from '@/services/sseService';

export function Chat() {
  const [input, setInput] = useState('');
  const [streamingMessage, setStreamingMessage] = useState<string>('');
  const [agentEvents, setAgentEvents] = useState<SSEEvent[]>([]);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [agentUIState, setAgentUIState] = useState<AgentUIState>('IDLE');
  const [sending, setSending] = useState(false); // 防止重复发送
  const [sessionTokens, setSessionTokens] = useState(0); // 当前session的token
  const [sessionCost, setSessionCost] = useState(0); // 当前session的花费
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { language } = useLanguage();
  const { isConnected, messages, error, connect, disconnect, totalTimeMs,
          toolCalls, confirmation, citations, currentMessageTokens, resetConfirmation } = useSSE();
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
  };

  const handleNewSession = useCallback(async () => {
    if (isConnected) disconnect();
    const session = await createSession(isZh ? '新对话' : 'New Chat');
    if (session) {
      setStreamingMessage('');
      setAgentEvents([]);
      setSessionTokens(0); // 重置token计数
      setSessionCost(0); // 重置cost计数
    }
  }, [isConnected, disconnect, createSession, isZh]);

  const handleSwitchSession = useCallback(async (sessionId: string) => {
    if (isConnected) disconnect();
    await switchSession(sessionId);
    setStreamingMessage('');
    setAgentEvents([]);
    setSessionTokens(0); // 重置token计数
    setSessionCost(0); // 重置cost计数
  }, [isConnected, disconnect, switchSession]);

  const handleDeleteSession = useCallback(async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm(t.deleteConfirm)) {
      await deleteSession(sessionId);
    }
  }, [deleteSession, t.deleteConfirm]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || isConnected || sending) return;

    setSending(true); // 防止重复发送
    
    try {
      let sessionId = currentSession?.id;
      
      if (!sessionId) {
        const newSession = await createSession(input.trim().substring(0, 50));
        if (!newSession) return;
        sessionId = newSession.id;
      }

      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        session_id: sessionId,
        role: 'user',
        content: input.trim(),
        created_at: new Date().toISOString(),
      };
      
      addMessage(userMessage);

      const message = encodeURIComponent(input.trim());
      
      // Connect directly to Node.js backend to bypass Vite proxy
      // This ensures cookies are sent with EventSource requests
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:4000';
      const url = `${apiUrl}/api/chat/stream?message=${message}&session_id=${sessionId}`;
      
      connect(url);
      setInput('');
    } catch (error) {
      console.error('Send message failed:', error);
    } finally {
      setSending(false);
    }
  }, [input, isConnected, sending, currentSession, createSession, addMessage, connect]);

  useEffect(() => {
    if (messages.length === 0) return;

    const latestMessage = messages[messages.length - 1];

    if (latestMessage.type === 'message') {
      setStreamingMessage(prev => prev + (latestMessage.content || ''));
    }

    if (latestMessage.type === 'thought' || 
        latestMessage.type === 'tool_call' || 
        latestMessage.type === 'tool_result') {
      setAgentEvents(prev => [...prev, latestMessage]);
    }

    // Capture token usage from done event
    if (latestMessage.type === 'done') {
      const tokensUsed = latestMessage.content?.tokens_used || 0;
      const cost = latestMessage.content?.cost || 0;
      
      setSessionTokens(prev => prev + tokensUsed);
      setSessionCost(prev => prev + cost);
    }
  }, [messages]);

  useEffect(() => {
    if (!isConnected && streamingMessage && currentSession) {
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        session_id: currentSession.id,
        role: 'assistant',
        content: streamingMessage,
        created_at: new Date().toISOString(),
      };
      addMessage(assistantMessage);
      setStreamingMessage('');
    }
  }, [isConnected, streamingMessage, currentSession, addMessage]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [sessionMessages, streamingMessage, messages]);

  // Update agent UI state based on connection and events
  useEffect(() => {
    if (isConnected || sending) {
      setAgentUIState('RUNNING');
    } else if (agentEvents.length > 0) {
      // Check if waiting for confirmation
      const hasConfirmation = agentEvents.some(e => e.type === 'confirmation_required');
      if (hasConfirmation) {
        setAgentUIState('WAITING');
      } else {
        setAgentUIState('DONE');
      }
    } else {
      setAgentUIState('IDLE');
    }
  }, [isConnected, sending, agentEvents]);

  // Compute thinking steps from agent events
  const thinkingSteps = useMemo<ThinkingStep[]>(() => {
    return agentEvents
      .filter(e => e.type === 'thought')
      .map(e => ({
        type: (e.content?.type || 'analyze') as 'analyze' | 'plan' | 'execute' | 'verify',
        content: typeof e.content === 'string' ? e.content : (e.content?.content || e.content?.thought || ''),
        timestamp: e.timestamp ? new Date(e.timestamp).getTime() : undefined,
      }));
  }, [agentEvents]);

  // Compute execution steps for sidebar
  const executionSteps = useMemo<ExecutionStep[]>(() => {
    const steps: ExecutionStep[] = [];
    agentEvents.forEach(event => {
      if (event.type === 'tool_call') {
        steps.push({
          tool: event.tool,
          action: event.tool || 'Tool call',
          status: 'running',
          timestamp: event.timestamp ? new Date(event.timestamp).getTime() : undefined,
        });
      } else if (event.type === 'tool_result') {
        // Update the last running step with matching tool
        const lastRunningIdx = steps.map(s => s.tool).lastIndexOf(event.tool);
        if (lastRunningIdx >= 0) {
          steps[lastRunningIdx].status = event.result?.success ? 'completed' : 'failed';
        }
      }
    });
    return steps;
  }, [agentEvents]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Handle stop button click
  const handleStop = useCallback(() => {
    if (isConnected) {
      disconnect();
      setAgentUIState('DONE');
    }
  }, [isConnected, disconnect]);

  // Citation click handler — scroll to or highlight citation in CitationsPanel
  const handleCitationClick = useCallback((index: number) => {
    console.log('Citation clicked:', index);
    // Future: scroll CitationsPanel to the clicked citation, expand if collapsed
  }, []);

  // Send confirmation response (approve/reject) to backend
  const sendConfirmationResponse = useCallback(async (approved: boolean) => {
    if (!confirmation) return;
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:4000';
      const response = await fetch(`${apiUrl}/api/chat/confirmation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          sessionId: currentSession?.id,
          tool: confirmation.tool,
          approved,
        }),
      });
      if (!response.ok) {
        console.error('Failed to send confirmation response', { status: response.status });
      }
    } catch (error) {
      console.error('Error sending confirmation response', { error });
    } finally {
      resetConfirmation();
    }
  }, [confirmation, currentSession, resetConfirmation]);

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
                      {session.message_count} {isZh ? '条消息' : 'messages'}
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
          {sessionMessages.length === 0 && !streamingMessage ? (
            <div className="flex-1 flex flex-col items-center justify-center h-full text-center">
              <Bot className="w-16 h-16 text-primary/20 mb-4" />
              <p className="text-lg font-serif text-muted-foreground mb-2">{t.noMessages}</p>
              <p className="text-sm text-muted-foreground/60">{t.sendFirst}</p>
            </div>
          ) : (
            <div className="space-y-4 max-w-4xl mx-auto">
              {sessionMessages.filter(m => m.role === 'user' || m.role === 'assistant').map((msg) => (
                <div key={msg.id} className={clsx(
                  'flex gap-3',
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                )}>
                  {msg.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <Bot className="w-4 h-4 text-primary" />
                    </div>
                  )}
                  <div className={clsx(
                    'max-w-[80%] rounded-2xl px-4 py-3',
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted'
                  )}>
                    <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                    <div className={clsx(
                      'text-xs mt-1.5',
                      msg.role === 'user' ? 'text-primary-foreground/70' : 'text-muted-foreground'
                    )}>
                      {formatTime(msg.created_at)}
                    </div>
                  </div>
                  {msg.role === 'user' && (
                    <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
                      <User className="w-4 h-4 text-muted-foreground" />
                    </div>
                  )}
                </div>
              ))}
              
              {streamingMessage && (
                <div className="flex gap-3 justify-start">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-primary" />
                  </div>
                  <div className="flex-1 max-w-[80%] space-y-2">
                    {/* Thinking Process - inline above AI answer (D-02, D-03) */}
                    {thinkingSteps.length > 0 && (
                      <ThinkingProcess
                        steps={thinkingSteps}
                        duration={totalTimeMs / 1000}
                        onComplete={() => {}}
                        autoCollapse={true}
                      />
                    )}

                    {/* Tool Call Cards (D-04) */}
                    {toolCalls.length > 0 && (
                      <div className="space-y-2">
                        {toolCalls.map(tc => (
                          <ToolCallCard key={tc.id} toolCall={tc} />
                        ))}
                      </div>
                    )}

                    {/* Answer with MarkdownRenderer (D-01) */}
                    <motion.div
                      initial={{ opacity: 0.7 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.05 }}
                    >
                      <div className="rounded-2xl px-4 py-3 bg-muted">
                        {citations.length > 0 ? (
                          renderContentWithCitations(streamingMessage, handleCitationClick)
                        ) : (
                          <MarkdownRenderer content={streamingMessage} className="text-sm" />
                        )}
                      </div>
                    </motion.div>

                    {/* Citations Panel (D-05) */}
                    {citations.length > 0 && (
                      <CitationsPanel citations={citations} />
                    )}

                    {/* Message-level token usage (D-06) */}
                    {currentMessageTokens && (
                      <div className="text-xs text-muted-foreground font-mono mt-1">
                        Token: {currentMessageTokens.tokensUsed.toLocaleString()}
                        {currentMessageTokens.cost > 0 && ` · ¥${currentMessageTokens.cost.toFixed(4)}`}
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {/* Scroll anchor */}
              <div ref={messagesEndRef} />
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 text-destructive text-sm bg-destructive/10 px-4 py-2 rounded-lg mt-4 max-w-4xl mx-auto">
              <AlertCircle className="w-4 h-4" />
              {error}
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
                disabled={isConnected || sending}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
                }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isConnected || sending}
                className={clsx(
                  'w-10 h-10 rounded-lg flex items-center justify-center transition-all',
                  input.trim() && !isConnected && !sending
                    ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                    : 'bg-muted text-muted-foreground'
                )}
              >
                {isConnected || sending ? (
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
            {/* Agent State Sidebar - 4-state visualization (D-04, D-05, D-06) */}
            <AgentStateSidebar
              state={agentUIState}
              currentStep={isConnected ? 'Processing...' : undefined}
              totalTime={totalTimeMs}
              steps={executionSteps}
              onStop={handleStop}
            />

            {/* Token Monitor - session level (D-06) */}
            {sessionTokens > 0 && (
              <div className="border-t border-border/50 p-4">
                <TokenMonitor tokens={sessionTokens} cost={sessionCost} limit={128000} />
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Confirmation Dialog for agent approval */}
      <ConfirmationDialog
        tool={confirmation?.tool || ''}
        params={confirmation?.params || {}}
        isOpen={confirmation !== null}
        onApprove={() => sendConfirmationResponse(true)}
        onReject={() => sendConfirmationResponse(false)}
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