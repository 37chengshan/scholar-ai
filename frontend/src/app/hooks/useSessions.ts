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

import { useState, useEffect, useCallback } from 'react';
import apiClient from '../../utils/apiClient';

export interface ChatSession {
  id: string;
  title: string;
  status: string;
  message_count: number;
  created_at: string;
  updated_at?: string;
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

  const loadSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/api/v1/sessions?limit=50&status=active');
      const data = response.data.data || response.data;
      console.log('[useSessions] Loaded sessions:', data);
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
    try {
      const response = await apiClient.get(`/api/v1/sessions/${sessionId}/messages?limit=100`);
      const data = response.data.data || response.data;
      console.log('[useSessions] Loaded messages:', data);
      const msgs = (data.messages || []).reverse();
      setMessages(msgs);
    } catch (err) {
      console.log('[useSessions] No messages yet for this session');
      setMessages([]); // No messages yet, that's OK
    }
  }, []);

  const createSession = useCallback(async (title?: string): Promise<ChatSession | null> => {
    setError(null);
    try {
      const response = await apiClient.post('/api/v1/sessions', {
        title: title || '新对话',
        status: 'active'
      });
      
      const session = response.data.data || response.data;
      console.log('[useSessions] Created session:', session);
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
    setMessages(prev => [...prev, message]);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const updateCurrentSession = useCallback(async (updates: Partial<ChatSession>) => {
    if (!currentSession) return;
    
    try {
      const response = await apiClient.patch(`/api/v1/sessions/${currentSession.id}`, updates);
      const updated = response.data.data || response.data;
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