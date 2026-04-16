import apiClient from '@/utils/apiClient';

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

interface SessionListPayload {
  sessions: SessionRecord[];
  total: number;
  limit: number;
}

interface SessionMessagesPayload {
  session_id: string;
  messages: SessionMessageRecord[];
  total: number;
  limit: number;
}

export async function listSessions(limit = 50, status = 'active'): Promise<SessionRecord[]> {
  const response = await apiClient.get<SessionListPayload>(
    `/api/v1/sessions?limit=${limit}&status=${status}`,
  );

  return response.data.sessions || [];
}

export async function getSessionMessages(sessionId: string, limit = 100): Promise<SessionMessageRecord[]> {
  const response = await apiClient.get<SessionMessagesPayload>(
    `/api/v1/sessions/${sessionId}/messages?limit=${limit}`,
  );

  return response.data.messages || [];
}

export async function createSession(title = '新对话'): Promise<SessionRecord> {
  const response = await apiClient.post<SessionRecord>('/api/v1/sessions', {
    title,
    status: 'active',
  });

  return response.data;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/api/v1/sessions/${sessionId}`);
}

export async function updateSession(
  sessionId: string,
  updates: Partial<Pick<SessionRecord, 'title' | 'status'>>,
): Promise<SessionRecord> {
  const response = await apiClient.patch<SessionRecord>(`/api/v1/sessions/${sessionId}`, updates);
  return response.data;
}
