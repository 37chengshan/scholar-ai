import type { HttpClient } from '../client/http';
import type {
  MessageDto,
  MessageOrder,
  SessionMessagesResponse,
} from '@scholar-ai/types';

export interface GetSessionMessagesParams {
  limit?: number;
  offset?: number;
  order?: MessageOrder;
}

export interface ChatSessionsApi {
  getMessages: (
    sessionId: string,
    params?: GetSessionMessagesParams
  ) => Promise<SessionMessagesResponse>;
  sendMessage: (sessionId: string, content: string) => Promise<MessageDto>;
}

export function createChatSessionsApi(client: HttpClient): ChatSessionsApi {
  return {
    getMessages: (sessionId: string, params?: GetSessionMessagesParams) =>
      client.get<SessionMessagesResponse>(`/api/v1/sessions/${sessionId}/messages`, {
        params: params as Record<string, unknown> | undefined,
      }),
    sendMessage: (sessionId: string, content: string) =>
      client.post<MessageDto>(`/api/v1/sessions/${sessionId}/messages`, { content }),
  };
}
