/**
 * Chat Store - Zustand State Management
 *
 * Manages chat sessions and messages state:
 * - sessions: List of chat sessions
 * - activeSession: Currently active session
 * - messages: Messages for active session
 *
 * Used by Chat page.
 */

import { create } from 'zustand';
import type { Session, Message } from '@/types';

/**
 * Chat state interface
 */
interface ChatState {
  sessions: Session[];
  activeSession: Session | null;
  messages: Message[];

  // Actions
  setSessions: (sessions: Session[]) => void;
  setActiveSession: (session: Session | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  clearChat: () => void;
}

/**
 * Chat store
 *
 * Provides global chat state for Chat page.
 * Manages sessions and messages separately for efficiency.
 */
export const useChatStore = create<ChatState>((set) => ({
  // Initial state
  sessions: [],
  activeSession: null,
  messages: [],

  // Set sessions list
  setSessions: (sessions) => set({ sessions }),

  // Set active session (clears messages)
  setActiveSession: (activeSession) =>
    set({
      activeSession,
      messages: [], // Clear messages when switching sessions
    }),

  // Set messages for active session
  setMessages: (messages) => set({ messages }),

  // Add message to current session (for real-time updates)
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  // Clear chat (on logout)
  clearChat: () =>
    set({
      sessions: [],
      activeSession: null,
      messages: [],
    }),
}));