import { useMemo } from 'react';
import { useSessions } from '@/app/hooks/useSessions';

export function useChatSession() {
  const {
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
    updateCurrentSession,
  } = useSessions();

  return useMemo(() => ({
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
    updateCurrentSession,
  }), [
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
    updateCurrentSession,
  ]);
}
