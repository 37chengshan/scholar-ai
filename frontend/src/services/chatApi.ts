/**
 * Chat/Session API Service
 *
 * Chat session management API calls:
 * - createSession(): Create new chat session
 * - getSessions(): List user's sessions
 * - getMessages(): Get session messages
 * - streamMessage(): SSE streaming for real-time responses
 *
 * Note: SSE streaming implemented using sseService
 */

import apiClient from '@/utils/apiClient';
import { sseService, SSEEvent, SSEHandlers, DoneEventData } from './sseService';
import type { Session, Message } from '@/types';

/**
 * Create new chat session
 *
 * POST /api/v1/sessions
 * Creates a new conversation session
 *
 * @returns Created session
 */
export async function createSession(): Promise<Session> {
  const response = await apiClient.post<Session>('/api/v1/sessions');

  return response.data;
}

/**
 * Get user's chat sessions
 *
 * GET /api/v1/sessions
 * Returns all user's sessions (active + expired)
 *
 * @returns Sessions list
 */
export async function getSessions(): Promise<Session[]> {
  const response = await apiClient.get<Session[]>('/api/v1/sessions');

  return response.data;
}

/**
 * Get session messages
 *
 * GET /api/v1/sessions/:id/messages
 * Returns all messages in a session
 *
 * @param sessionId - Session ID
 * @returns Messages list
 */
export async function getMessages(sessionId: string): Promise<Message[]> {
  const response = await apiClient.get<Message[]>(`/api/v1/sessions/${sessionId}/messages`);

  return response.data;
}

/**
 * Send message to session
 *
 * POST /api/v1/sessions/:id/messages
 * Creates user message and triggers AI response
 *
 * Note: Phase 15 will implement SSE streaming for real-time responses
 *
 * @param sessionId - Session ID
 * @param content - Message content
 * @returns Created message + AI response (if non-streaming)
 */
export async function sendMessage(
  sessionId: string,
  content: string
): Promise<Message> {
  const response = await apiClient.post<Message>(`/api/v1/sessions/${sessionId}/messages`, {
    content,
  });

  return response.data;
}

/**
 * Delete session
 *
 * DELETE /api/v1/sessions/:id
 * Removes session and all messages
 *
 * @param sessionId - Session ID
 */
export async function deleteSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/api/v1/sessions/${sessionId}`);
}

/**
 * Update session title
 *
 * PATCH /api/v1/sessions/:id
 * Updates session metadata (e.g., title)
 *
 * @param sessionId - Session ID
 * @param title - New title
 * @returns Updated session
 */
export async function updateSession(
  sessionId: string,
  title: string
): Promise<Session> {
  const response = await apiClient.patch<Session>(`/api/v1/sessions/${sessionId}`, {
    title,
  });

  return response.data;
}

/**
 * Stream message to session using SSE
 *
 * POST /api/v1/chat/stream
 * Creates user message and returns SSE stream for real-time AI responses
 *
 * @param sessionId - Session ID
 * @param content - Message content
 * @param handlers - SSE event handlers
 * @returns void (events delivered via handlers)
 */
export function streamMessage(
  sessionId: string,
  content: string,
  handlers: SSEHandlers
): void {
  sseService.connect(
    '/api/v1/chat/stream',
    handlers,
    {
      session_id: sessionId,
      message: content,
    }
  );
}

/**
 * Stop streaming
 */
export function stopStream(): void {
  sseService.disconnect();
}