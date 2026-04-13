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
import apiClient from '../../utils/apiClient';

export interface ChatSession {
  id: string;
  title: string;
  status: string;
  messageCount: number;
  createdAt: string;
  updatedAt?: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'tool' | 'system';
  content: string;
  tool_name?: string;
  created_at: string;
}

interface UseSessionsReturn {
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  loadSessions: () => Promise<void>;
  createSession: (title?: string) => Promise<ChatSession | null>;
  switchSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<boolean>;
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
  updateCurrentSession: (updates: Partial<ChatSession>) => Promise<void>;
}

export function useSessions(): UseSessionsReturn {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use ref for timestamp to prevent race condition (doesn't trigger re-render or callback recreation)
  const lastLocalMessageTime = useRef<number>(0);
  // Grace period: 3 seconds to prevent API overwriting local message
  const LOCAL_MESSAGE_GRACE_PERIOD = 3000;

  const loadSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/api/v1/sessions?limit=50&status=active');
      const data = response.data;
      setSessions(data.sessions || []);
      
      if (data.sessions && data.sessions.length > 0) {
        const lastSession = data.sessions[0];
        setCurrentSession(lastSession);
      }
    } catch (err) {
      console.error('[useSessions] Load error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSessionMessages = useCallback(async (sessionId: string) => {
    // Skip reload if we recently added a local message (race condition prevention)
    const timeSinceLastLocalMessage = Date.now() - lastLocalMessageTime.current;
    if (timeSinceLastLocalMessage < LOCAL_MESSAGE_GRACE_PERIOD) {
      console.log('[useSessions] Skipping loadSessionMessages - local message added', timeSinceLastLocalMessage, 'ms ago');
      return;
    }
    try {
      const response = await apiClient.get(`/api/v1/sessions/${sessionId}/messages?limit=100`);
      const data = response.data;
      const msgs = (data.messages || []).reverse();
      setMessages(msgs);
    } catch (err) {
      setMessages([]); // No messages yet, that's OK
    }
  }, []); // No dependency on lastLocalMessageTime - it's a ref

  const createSession = useCallback(async (title?: string): Promise<ChatSession | null> => {
    setError(null);
    try {
      const response = await apiClient.post('/api/v1/sessions', {
        title: title || '新对话',
        status: 'active'
      });
      
      const session = response.data;
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
      setCurrentSession(session);
    }
  }, [sessions]);

  const deleteSession = useCallback(async (sessionId: string): Promise<boolean> => {
    try {
      await apiClient.delete(`/api/v1/sessions/${sessionId}`);
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
    lastLocalMessageTime.current = Date.now();
    console.log('[useSessions] Adding local message, timestamp set to', lastLocalMessageTime.current);
    setMessages(prev => [...prev, message]);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const updateCurrentSession = useCallback(async (updates: Partial<ChatSession>) => {
    if (!currentSession) return;
    
    try {
      const response = await apiClient.patch(`/api/v1/sessions/${currentSession.id}`, updates);
      const updated = response.data;
      setCurrentSession(updated);
      setSessions(prev => prev.map(s => s.id === updated.id ? updated : s));
    } catch (err) {
      console.error('[useSessions] Failed to update session:', err);
    }
  }, [currentSession]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    if (currentSession?.id) {
      loadSessionMessages(currentSession.id);
    }
  }, [currentSession?.id, loadSessionMessages]);

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
    updateCurrentSession
  };
}
