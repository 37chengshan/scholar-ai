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
import {
  sseService,
  SSEEvent,
  SSEHandlers,
  DoneEventData,
  SSEService,
} from './sseService';
import type { Session, Message } from '@/types';

export type ChatMode = 'auto' | 'rag' | 'agent';

export interface ChatScope {
  type: 'paper' | 'knowledge_base' | 'general';
  paper_id?: string;
  knowledge_base_id?: string;
}

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
 * Sprint 3: New unified signature with explicit mode and scope.
 * Request body:
 * {
 *   session_id,
 *   message,
 *   mode,
 *   scope: {
 *     type: 'paper' | 'knowledge_base' | 'general',
 *     paper_id?,
 *     knowledge_base_id?
 *   },
 *   context?
 * }
 * No longer uses top-level paperId/kbId - these go in scope.
 *
 * @param params - Stream parameters
 * @param params.sessionId - Session ID
 * @param params.message - Message content
 * @param params.mode - Processing mode: 'auto' | 'rag' | 'agent'
 * @param params.scope - Query scope: { type: 'paper'|'kb', id: string }
 * @param params.handlers - SSE event handlers
 */
export function streamMessage(params: {
  sessionId: string;
  message: string;
  mode?: ChatMode;
  scope?: ChatScope | null;
  context?: Record<string, unknown>;
  handlers: SSEHandlers;
  streamService?: SSEService;
}): void {
  const {
    sessionId,
    message,
    mode = 'auto',
    scope,
    context,
    handlers,
    streamService,
  } = params;
  const body: Record<string, unknown> = {
    session_id: sessionId,
    message,
    mode,
  };
  if (scope) {
    body.scope = scope;
  }
  if (context) {
    body.context = context;
  }

  const service = streamService ?? sseService;
  service.connect('/api/v1/chat/stream', handlers, body);
}

/**
 * Stop streaming
 */
export function stopStream(): void {
  sseService.disconnect();
}