/**
 * Chat Page - SSE Streaming with Citations
 *
 * Main chat interface with:
 * - SSE streaming for real-time AI responses
 * - Citations panel in right sidebar (D-07)
 * - Session management in left sidebar
 * - Auto-reconnect on disconnect (D-05)
 *
 * Uses:
 * - useSSE hook for connection management
 * - CitationsPanel for source display
 * - MessageBubble for message rendering
 */

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'motion/react';
import {
  Plus,
  Search,
  Send,
  Bot,
  AlignLeft,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';
import { useSSE } from '../hooks/useSSE';
import { CitationsPanel, Citation } from '../components/CitationsPanel';
import { MessageBubble } from '../components/MessageBubble';

/**
 * Chat message type
 */
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
}

/**
 * Chat session type
 */
interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  lastMessage?: string;
}

/**
 * Paper selector item
 */
interface PaperItem {
  id: string;
  title: string;
}

export function Chat() {
  // State
  const [input, setInput] = useState('');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [sessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [selectedPapers] = useState<PaperItem[]>([]);
  const [citations, setCitations] = useState<Citation[]>([]);

  // Hooks
  const { language } = useLanguage();
  const { isConnected, messages, error, connect, clearMessages } = useSSE();

  const isZh = language === 'zh';

  // Translations
  const t = {
    terminal: isZh ? '终端对话' : 'Terminal',
    sessions: isZh ? '会话列表' : 'Sessions',
    search: isZh ? '搜索...' : 'Search...',
    history: isZh ? '历史记录' : 'History',
    context: isZh ? '上下文' : 'Context',
    addContext: isZh ? '添加上下文' : 'Add Context',
    placeholder: isZh ? '给 ScholarAI 发送消息...' : 'Message ScholarAI...',
    verify: isZh ? '请验证输出结果。' : 'Verify outputs.',
    shortcuts: isZh ? 'Return 发送 · Shift+Return 换行' : 'Return to send · Shift+Return for new line',
    inspector: isZh ? '检查器' : 'Inspector',
    activeContext: isZh ? '活动上下文' : 'Active Context',
    newChat: isZh ? '新对话' : 'New Chat',
    noMessages: isZh ? '开始新对话' : 'Start a new conversation',
    sendFirst: isZh ? '发送您的第一条消息' : 'Send your first message',
  };

  /**
   * Handle sending message
   */
  const handleSend = useCallback(() => {
    if (!input.trim() || isConnected) return;

    // Create user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    // Add user message to list
    setChatMessages((prev) => [...prev, userMessage]);

    // Build SSE URL
    const message = encodeURIComponent(input.trim());
    const paperIds = selectedPapers.map((p) => p.id).join(',');
    const url = `/api/chat/stream?message=${message}${paperIds ? `&paper_ids=${paperIds}` : ''}`;

    // Connect SSE
    connect(url);

    // Clear input
    setInput('');

    // Clear previous citations
    setCitations([]);
  }, [input, isConnected, selectedPapers, connect]);

  /**
   * Process SSE messages
   */
  useEffect(() => {
    if (messages.length === 0) return;

    const latestMessage = messages[messages.length - 1];

    // Handle message events
    if (latestMessage.type === 'message') {
      setChatMessages((prev) => {
        const lastMessage = prev[prev.length - 1];

        // If last message is assistant, append content (streaming)
        if (lastMessage?.role === 'assistant') {
          return [
            ...prev.slice(0, -1),
            {
              ...lastMessage,
              content: lastMessage.content + (latestMessage.content || ''),
            },
          ];
        }

        // Create new assistant message
        return [
          ...prev,
          {
            id: `assistant-${Date.now()}`,
            role: 'assistant' as const,
            content: latestMessage.content || '',
            timestamp: new Date().toISOString(),
            isStreaming: true,
          },
        ];
      });
    }

    // Handle tool_result events (extract citations from RAG search)
    if (latestMessage.type === 'tool_result' && latestMessage.tool === 'rag_search') {
      const result = latestMessage.result;
      if (result?.sources && Array.isArray(result.sources)) {
        const newCitations: Citation[] = result.sources.map((source: any) => ({
          paper_id: source.paperId || source.paper_id || '',
          paper_title: source.paperTitle || source.paper_title || 'Unknown',
          page: source.pageNumber || source.page,
          snippet: source.content || source.snippet || '',
          score: source.score || 0,
          type: source.type || 'text',
        }));
        setCitations(newCitations);
      }
    }
  }, [messages]);

  /**
   * Mark streaming complete when done
   */
  useEffect(() => {
    if (!isConnected && chatMessages.length > 0) {
      const lastMessage = chatMessages[chatMessages.length - 1];
      if (lastMessage.role === 'assistant' && lastMessage.isStreaming) {
        setChatMessages((prev) =>
          prev.map((msg, idx) =>
            idx === prev.length - 1 ? { ...msg, isStreaming: false } : msg
          )
        );
      }
    }
  }, [isConnected, chatMessages]);

  /**
   * Handle keyboard shortcuts
   */
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  /**
   * Create new session
   */
  const handleNewSession = () => {
    setCurrentSessionId(null);
    setChatMessages([]);
    setCitations([]);
    clearMessages();
  };

  return (
    <div className="h-full flex font-sans bg-background text-foreground relative selection:bg-primary selection:text-primary-foreground">
      {/* Left Sidebar: Sessions */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="w-[200px] border-r border-border/50 flex flex-col h-full bg-muted/20 flex-shrink-0"
      >
        {/* Header */}
        <div className="px-4 py-3.5 border-b border-border/50 flex items-center justify-between bg-background/80 backdrop-blur-md sticky top-0 z-10">
          <div className="flex flex-col">
            <h2 className="font-serif text-lg font-black tracking-tight leading-none mb-1">
              {t.terminal}
            </h2>
            <p className="text-[8px] font-bold tracking-[0.2em] uppercase text-primary">
              {t.sessions}
            </p>
          </div>
          <button
            onClick={handleNewSession}
            className="w-6 h-6 rounded-sm border border-foreground/20 flex items-center justify-center hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all duration-300 shadow-sm bg-card"
          >
            <Plus className="w-3 h-3" />
          </button>
        </div>

        {/* Search */}
        <div className="px-3 py-3 border-b border-border/50">
          <div className="relative">
            <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder={t.search}
              className="w-full bg-card border border-border/50 rounded-sm pl-7 pr-2 py-1.5 text-[10px] font-sans placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 transition-all shadow-sm"
            />
          </div>
        </div>

        {/* Session List */}
        <div className="flex-1 overflow-y-auto py-3 px-2 flex flex-col gap-1">
          <div className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-1.5 px-1.5 pb-1 border-b border-border/50">
            {t.history}
          </div>
          {sessions.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-[10px] text-muted-foreground">{t.newChat}</p>
            </div>
          ) : (
            sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => setCurrentSessionId(session.id)}
                className={clsx(
                  'text-left flex flex-col gap-1 px-2.5 py-2 rounded-sm transition-all duration-300 border border-transparent group',
                  currentSessionId === session.id
                    ? 'bg-primary/10 border-primary/20'
                    : 'hover:bg-card hover:border-border/50'
                )}
              >
                <span
                  className={clsx(
                    'text-[10px] font-bold uppercase tracking-widest truncate',
                    currentSessionId === session.id
                      ? 'text-primary'
                      : 'text-foreground/80 group-hover:text-primary'
                  )}
                >
                  {session.title}
                </span>
                <span className="text-[8px] font-mono text-muted-foreground">
                  {session.lastMessage || t.newChat}
                </span>
              </button>
            ))
          )}
        </div>
      </motion.div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full bg-background min-w-[500px] relative border-r border-border/50">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-border/50 flex items-center justify-between bg-background/90 backdrop-blur-md sticky top-0 z-10 shadow-sm">
          <div className="flex items-center gap-3">
            <Bot className="w-4 h-4 text-primary" />
            <h2 className="font-serif text-base font-bold tracking-tight leading-none truncate max-w-[200px]">
              {currentSessionId ? sessions.find((s) => s.id === currentSessionId)?.title : t.newChat}
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[8px] font-bold tracking-[0.2em] uppercase border border-primary text-primary px-1.5 py-0.5 rounded-sm bg-primary/5 flex items-center gap-1">
              <span
                className={clsx(
                  'w-1.5 h-1.5 rounded-full',
                  isConnected ? 'bg-primary animate-pulse' : 'bg-muted-foreground'
                )}
              />
              ScholarAI
            </span>
            <button className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground hover:text-foreground transition-colors border border-border/50 px-1.5 py-0.5 rounded-sm flex items-center gap-1 hover:bg-muted shadow-sm bg-card hidden sm:flex">
              <AlignLeft className="w-3 h-3" /> {t.context}
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 lg:px-8 py-6 flex flex-col gap-6 max-w-4xl mx-auto w-full">
          {chatMessages.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center">
              <Bot className="w-12 h-12 text-primary/20 mb-4" />
              <p className="text-lg font-serif text-muted-foreground mb-2">{t.noMessages}</p>
              <p className="text-sm text-muted-foreground/60">{t.sendFirst}</p>
            </div>
          ) : (
            chatMessages.map((msg) => (
              <MessageBubble
                key={msg.id}
                role={msg.role}
                content={msg.content}
                timestamp={msg.timestamp}
                isStreaming={msg.isStreaming}
              />
            ))
          )}

          {/* Error display */}
          {error && (
            <div className="flex items-center gap-2 text-destructive text-sm bg-destructive/10 px-3 py-2 rounded-sm">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="px-5 py-3 border-t border-border/50 bg-background/80 backdrop-blur-md flex-shrink-0 z-20 shadow-[0_-4px_12px_rgba(0,0,0,0.05)]">
          <div className="max-w-4xl mx-auto w-full flex flex-col gap-1.5 relative">
            {/* Model indicator */}
            <div className="flex items-center gap-2 mb-0.5 px-1">
              <span className="text-[8px] font-bold tracking-[0.2em] uppercase text-primary flex items-center gap-1">
                {isConnected ? (
                  <>
                    <Loader2 className="w-2.5 h-2.5 animate-spin" /> Streaming...
                  </>
                ) : (
                  <>
                    <Bot className="w-2.5 h-2.5" /> ScholarAI
                  </>
                )}
              </span>
              <div className="w-px h-2 bg-border/50" />
              <button className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground hover:text-primary transition-colors flex items-center gap-1">
                <Plus className="w-2.5 h-2.5" /> {t.addContext}
              </button>
            </div>

            {/* Input field */}
            <div className="relative flex items-end bg-card rounded-sm border border-primary/20 shadow-sm focus-within:shadow-md focus-within:border-primary/50 transition-all duration-300">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t.placeholder}
                className="flex-1 p-3 font-sans text-[11px] md:text-[13px] font-medium placeholder:text-muted-foreground focus:outline-none resize-none min-h-[36px] max-h-[120px] bg-transparent leading-relaxed"
                rows={1}
                disabled={isConnected}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
                }}
              />

              <div className="p-1.5 pr-2">
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isConnected}
                  className={clsx(
                    'w-6 h-6 rounded-sm flex items-center justify-center transition-all duration-300 shadow-sm',
                    input.trim() && !isConnected
                      ? 'bg-primary text-primary-foreground hover:bg-secondary'
                      : 'bg-muted text-muted-foreground border border-border/50'
                  )}
                >
                  {isConnected ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Send className="w-3 h-3" />
                  )}
                </button>
              </div>
            </div>

            {/* Shortcuts hint */}
            <div className="flex justify-between items-center px-1 mt-0.5">
              <div className="text-[7px] uppercase tracking-[0.2em] text-muted-foreground flex items-center gap-1">
                <AlertCircle className="w-2 h-2" /> {t.verify}
              </div>
              <div className="text-[7px] font-mono text-muted-foreground">{t.shortcuts}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Sidebar: Citations Panel */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="hidden xl:flex"
      >
        <CitationsPanel citations={citations} />
      </motion.div>
    </div>
  );
}