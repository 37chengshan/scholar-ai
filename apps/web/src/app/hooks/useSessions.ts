/**
 * useSessions Hook - Session Management
 *
 * Manages chat sessions with:
 * - Load session list
 * - Create new session
 * - Switch session
 * - Load session messages
 * - Delete session
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import * as sessionsApi from '@/services/sessionsApi';

export interface ChatSession {
  id: string;
  title: string;
  status: string;
  messageCount: number;
  createdAt: string;
  updatedAt?: string;
  metadata?: Record<string, unknown> | null;
}

function isValidSession(session: ChatSession | null | undefined): session is ChatSession {
  return Boolean(session && typeof session.id === 'string' && session.id.length > 0);
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'tool' | 'system';
  content: string;
  tool_name?: string;
  reasoning_content?: string | null;
  current_phase?: string | null;
  tool_timeline?: unknown;
  citations?: unknown;
  answer_contract?: unknown;
  stream_status?: string | null;
  tokens_used?: number | null;
  cost?: number | null;
  duration_ms?: number | null;
  response_type?: string | null;
  trace_id?: string | null;
  run_id?: string | null;
  reasoningBuffer?: string;
  toolTimeline?: unknown;
  answerContract?: unknown;
  streamStatus?: 'idle' | 'streaming' | 'completed' | 'error' | 'cancelled';
  tokensUsed?: number | null;
  responseType?: string;
  created_at: string;
}

interface UseSessionsReturn {
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  loadSessions: () => Promise<void>;
  createSession: (
    title?: string,
    metadata?: Record<string, unknown>,
  ) => Promise<ChatSession | null>;
  switchSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<boolean>;
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
  clearCurrentSession: () => void;
  updateCurrentSession: (updates: Partial<ChatSession>) => Promise<void>;
}

interface UseSessionsOptions {
  autoSelectLatest?: boolean;
  messageSessionId?: string | null;
  enabled?: boolean;
  loadMessages?: boolean;
}

export function useSessions(options: UseSessionsOptions = {}): UseSessionsReturn {
  const {
    autoSelectLatest = true,
    messageSessionId = undefined,
    enabled = true,
    loadMessages = true,
  } = options;
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const suppressAutoSelectRef = useRef(false);

  // Use ref for session-scoped optimistic update guard.
  const lastLocalMessageRef = useRef<{ sessionId: string | null; at: number }>({
    sessionId: null,
    at: 0,
  });
  // Grace period: 3 seconds to prevent API overwriting local message
  const LOCAL_MESSAGE_GRACE_PERIOD = 3000;

  const loadSessions = useCallback(async () => {
    if (!enabled) {
      setSessions([]);
      setCurrentSession(null);
      setMessages([]);
      setError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await sessionsApi.listSessions(50, 'active');
      const normalized = (data || []).filter((session) => isValidSession(session));
      setSessions(normalized);

      if (suppressAutoSelectRef.current || !autoSelectLatest) {
        setCurrentSession(null);
        return;
      }

      if (normalized.length > 0) {
        const lastSession = normalized[0];
        setCurrentSession(lastSession);
      } else {
        setCurrentSession(null);
      }
    } catch (err) {
      console.error('[useSessions] Load error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [autoSelectLatest, enabled]);

  const loadSessionMessages = useCallback(async (sessionId: string) => {
    // Skip reload only for the same session where optimistic local message was just added.
    const timeSinceLastLocalMessage = Date.now() - lastLocalMessageRef.current.at;
    const sameSessionOptimisticUpdate = lastLocalMessageRef.current.sessionId === sessionId;
    if (sameSessionOptimisticUpdate && timeSinceLastLocalMessage < LOCAL_MESSAGE_GRACE_PERIOD) {
      console.log('[useSessions] Skipping loadSessionMessages - optimistic message in same session', sessionId, timeSinceLastLocalMessage, 'ms ago');
      return;
    }
    try {
      const data = await sessionsApi.getSessionMessages(sessionId, 100);
      const msgs = (data || []).reverse();
      setMessages(msgs);
    } catch (err) {
      setMessages([]); // No messages yet, that's OK
    }
  }, []); // No dependency on lastLocalMessageRef - it's a ref

  const createSession = useCallback(async (
    title?: string,
    metadata?: Record<string, unknown>,
  ): Promise<ChatSession | null> => {
    setError(null);
    try {
      const session = await sessionsApi.createSession(title || '新对话', metadata || {});
      suppressAutoSelectRef.current = false;
      setSessions(prev => [session, ...prev]);
      setCurrentSession(session);
      setMessages([]); // New session has no messages
      return session;
    } catch (err) {
      console.error('[useSessions] Create error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    }
  }, []);

  const switchSession = useCallback(async (sessionId: string) => {
    const session = sessions.find(s => s.id === sessionId);
    if (session) {
      suppressAutoSelectRef.current = false;
      setCurrentSession(session);
    }
  }, [sessions]);

  const deleteSession = useCallback(async (sessionId: string): Promise<boolean> => {
    try {
      await sessionsApi.deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (currentSession?.id === sessionId) {
        setCurrentSession(null);
        setMessages([]);
      }
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    }
  }, [currentSession]);

  const addMessage = useCallback((message: ChatMessage) => {
    // Record timestamp to prevent loadSessionMessages from overwriting
    lastLocalMessageRef.current = {
      sessionId: message.session_id,
      at: Date.now(),
    };
    console.log('[useSessions] Adding local message, optimistic guard set to', lastLocalMessageRef.current);
    setMessages((prev) => {
      const existingIndex = prev.findIndex((item) => item.id === message.id);

      if (existingIndex === -1) {
        return [...prev, message];
      }

      const next = [...prev];
      next[existingIndex] = message;
      return next;
    });
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const clearCurrentSession = useCallback(() => {
    suppressAutoSelectRef.current = true;
    lastLocalMessageRef.current = {
      sessionId: null,
      at: 0,
    };
    setCurrentSession(null);
    setMessages([]);
  }, []);

  const updateCurrentSession = useCallback(async (updates: Partial<ChatSession>) => {
    if (!currentSession) return;
    
    try {
      const updated = await sessionsApi.updateSession(currentSession.id, {
        title: updates.title,
        status: updates.status,
        metadata: updates.metadata,
      });
      setCurrentSession(updated);
      setSessions(prev => prev.map(s => s.id === updated.id ? updated : s));
    } catch (err) {
      console.error('[useSessions] Failed to update session:', err);
    }
  }, [currentSession]);

  useEffect(() => {
    if (!enabled) {
      setSessions([]);
      setCurrentSession(null);
      setMessages([]);
      setError(null);
      setLoading(false);
      return;
    }

    loadSessions();
  }, [enabled, loadSessions]);

  useEffect(() => {
    if (!loadMessages) {
      setMessages([]);
      return;
    }

    const targetSessionId =
      messageSessionId === undefined ? currentSession?.id : messageSessionId;

    if (targetSessionId) {
      loadSessionMessages(targetSessionId);
      return;
    }

    if (messageSessionId === null) {
      setMessages([]);
    }
  }, [currentSession?.id, loadMessages, loadSessionMessages, messageSessionId]);

  return {
    sessions,
    currentSession,
    messages,
    loading,
    error,
    loadSessions,
    createSession,
    switchSession,
    deleteSession,
    addMessage,
    clearMessages,
    clearCurrentSession,
    updateCurrentSession
  };
}
