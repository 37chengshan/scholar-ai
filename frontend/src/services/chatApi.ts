/**
 * Chat/Session API Service
 *
 * Chat session management API calls:
 * - createSession(): Create new chat session
 * - getSessions(): List user's sessions
 * - getMessages(): Get session messages
 *
 * Note: SSE streaming will be implemented in Phase 15
 */

import apiClient from '@/utils/apiClient';
import type { Session, Message } from '@/types';

/**
 * Create new chat session
 *
 * POST /api/sessions
 * Creates a new conversation session
 *
 * @returns Created session
 */
export async function createSession(): Promise<Session> {
  const response = await apiClient.post<{
    success: boolean;
    data: Session;
  }>('/api/sessions');

  return response.data.data;
}

/**
 * Get user's chat sessions
 *
 * GET /api/sessions
 * Returns all user's sessions (active + expired)
 *
 * @returns Sessions list
 */
export async function getSessions(): Promise<Session[]> {
  const response = await apiClient.get<{
    success: boolean;
    data: Session[];
  }>('/api/sessions');

  return response.data.data;
}

/**
 * Get session messages
 *
 * GET /api/sessions/:id/messages
 * Returns all messages in a session
 *
 * @param sessionId - Session ID
 * @returns Messages list
 */
export async function getMessages(sessionId: string): Promise<Message[]> {
  const response = await apiClient.get<{
    success: boolean;
    data: Message[];
  }>(`/api/sessions/${sessionId}/messages`);

  return response.data.data;
}

/**
 * Send message to session
 *
 * POST /api/sessions/:id/messages
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
  const response = await apiClient.post<{
    success: boolean;
    data: Message;
  }>(`/api/sessions/${sessionId}/messages`, {
    content,
  });

  return response.data.data;
}

/**
 * Delete session
 *
 * DELETE /api/sessions/:id
 * Removes session and all messages
 *
 * @param sessionId - Session ID
 */
export async function deleteSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/api/sessions/${sessionId}`);
}

/**
 * Update session title
 *
 * PATCH /api/sessions/:id
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
  const response = await apiClient.patch<{
    success: boolean;
    data: Session;
  }>(`/api/sessions/${sessionId}`, {
    title,
  });

  return response.data.data;
}