import type { HttpClient } from '../client/http';
import type { MessageDto } from '@scholar-ai/types';

export interface ChatSessionsApi {
  getMessages: (sessionId: string) => Promise<MessageDto[]>;
  sendMessage: (sessionId: string, content: string) => Promise<MessageDto>;
}

export function createChatSessionsApi(client: HttpClient): ChatSessionsApi {
  return {
    getMessages: (sessionId: string) =>
      client.get<MessageDto[]>(`/api/v1/sessions/${sessionId}/messages`),
    sendMessage: (sessionId: string, content: string) =>
      client.post<MessageDto>(`/api/v1/sessions/${sessionId}/messages`, { content }),
  };
}
