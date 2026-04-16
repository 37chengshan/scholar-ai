import type { HttpClient } from '../client/http';
import type { PaperDto } from '@scholar-ai/types';

export interface PapersApi {
  list: (params?: Record<string, unknown>) => Promise<{ papers: PaperDto[]; total: number }>;
  get: (paperId: string) => Promise<PaperDto>;
}

export function createPapersApi(client: HttpClient): PapersApi {
  return {
    list: (params) => client.get<{ papers: PaperDto[]; total: number }>('/api/v1/papers', { params }),
    get: (paperId) => client.get<PaperDto>(`/api/v1/papers/${paperId}`),
  };
}
