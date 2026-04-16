import type { HttpClient } from '../client/http';
import type { SessionDto } from '@scholar-ai/types';

export interface ChatApi {
  createSession: () => Promise<SessionDto>;
  getSessions: () => Promise<SessionDto[]>;
  updateSession: (sessionId: string, title: string) => Promise<SessionDto>;
  deleteSession: (sessionId: string) => Promise<void>;
}

export function createChatApi(client: HttpClient): ChatApi {
  return {
    createSession: () => client.post<SessionDto>('/api/v1/sessions'),
    getSessions: () => client.get<SessionDto[]>('/api/v1/sessions'),
    updateSession: (sessionId: string, title: string) =>
      client.patch<SessionDto>(`/api/v1/sessions/${sessionId}`, { title }),
    deleteSession: async (sessionId: string) => {
      await client.delete<void>(`/api/v1/sessions/${sessionId}`);
    },
  };
}
