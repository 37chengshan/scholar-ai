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

import {
  sseService,
  SSEEvent,
  SSEHandlers,
  DoneEventData,
  SSEService,
} from './sseService';
import type { Session, Message } from '@/types';
import type { ChatMode, ChatScope } from '@scholar-ai/types';
import {
  createChatApi,
  createChatSessionsApi,
  buildChatStreamBody,
} from '@scholar-ai/sdk';
import { sdkHttpClient } from './sdkHttpClient';

const chatApiClient = createChatApi(sdkHttpClient);
const chatSessionsApiClient = createChatSessionsApi(sdkHttpClient);

/**
 * Create new chat session
 *
 * POST /api/v1/sessions
 * Creates a new conversation session
 *
 * @returns Created session
 */
export async function createSession(): Promise<Session> {
  const response = await sdkHttpClient.post('/api/v1/sessions', {
    title: '新对话',
    status: 'active',
    metadata: {},
  });
  return (response as { data?: Session }).data ?? (response as Session);
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
  const sessions = await chatApiClient.getSessions();
  return sessions as unknown as Session[];
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
  const response = await chatSessionsApiClient.getMessages(sessionId, {
    order: 'desc',
  });
  return response.data.messages as unknown as Message[];
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
  const message = await chatSessionsApiClient.sendMessage(sessionId, content);
  return message as unknown as Message;
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
  await chatApiClient.deleteSession(sessionId);
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
  const session = await chatApiClient.updateSession(sessionId, title);
  return session as unknown as Session;
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
  const { sessionId, message, mode = 'auto', scope, context, handlers, streamService } = params;
  const body = buildChatStreamBody({ sessionId, message, mode, scope, context });

  const service = streamService ?? sseService;
  service.connect('/api/v1/chat/stream', handlers, body);
}

/**
 * Stop streaming
 */
export function stopStream(): void {
  sseService.disconnect();
}
