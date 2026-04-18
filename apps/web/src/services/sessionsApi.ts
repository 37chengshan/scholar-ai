import apiClient from '@/utils/apiClient';
import {
  createChatApi,
  createChatSessionsApi,
} from '@scholar-ai/sdk';
import { sdkHttpClient } from './sdkHttpClient';

export interface SessionRecord {
  id: string;
  title: string;
  status: string;
  messageCount: number;
  createdAt: string;
  updatedAt?: string;
}

export interface SessionMessageRecord {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'tool' | 'system';
  content: string;
  tool_name?: string;
  created_at: string;
}

const chatApiClient = createChatApi(sdkHttpClient);
const chatSessionsApiClient = createChatSessionsApi(sdkHttpClient);

interface SessionListPayload {
  sessions: SessionRecord[];
  total: number;
  limit: number;
}

export async function listSessions(limit = 50, status = 'active'): Promise<SessionRecord[]> {
  const response = await apiClient.get<SessionListPayload>(`/api/v1/sessions?limit=${limit}&status=${status}`);
  return response.data.sessions || [];
}

export async function getSessionMessages(sessionId: string, limit = 100): Promise<SessionMessageRecord[]> {
  const response = await chatSessionsApiClient.getMessages(sessionId, {
    limit,
    order: 'desc',
  });
  return response.data.messages as SessionMessageRecord[];
}

export async function createSession(title = '新对话'): Promise<SessionRecord> {
  const response = await apiClient.post<{ success: boolean; data: SessionRecord }>('/api/v1/sessions', {
    title,
    status: 'active',
    metadata: {},
  });
  return response.data.data;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await chatApiClient.deleteSession(sessionId);
}

export async function updateSession(
  sessionId: string,
  updates: Partial<Pick<SessionRecord, 'title' | 'status'>>,
): Promise<SessionRecord> {
  if (updates.title) {
    const session = await chatApiClient.updateSession(sessionId, updates.title);
    return session as unknown as SessionRecord;
  }
  const response = await apiClient.patch<SessionRecord>(`/api/v1/sessions/${sessionId}`, updates);
  return response.data;
}
