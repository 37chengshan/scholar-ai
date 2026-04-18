import type { HttpClient } from '../client/http';
import type {
  KnowledgeBaseCreateDto,
  KnowledgeBaseDto,
  KnowledgeBaseListParams,
  KnowledgeBaseListResponse,
  KnowledgeBasePaperDto,
  KnowledgeBaseSearchHitDto,
  StorageStatsDto,
} from '@scholar-ai/types';

export interface KnowledgeBaseApi {
  list: (params?: KnowledgeBaseListParams) => Promise<KnowledgeBaseListResponse>;
  create: (data: KnowledgeBaseCreateDto) => Promise<KnowledgeBaseDto>;
  get: (id: string) => Promise<KnowledgeBaseDto>;
  update: (id: string, data: Partial<KnowledgeBaseCreateDto>) => Promise<KnowledgeBaseDto>;
  delete: (id: string) => Promise<{ deleted: boolean }>;
  listPapers: (kbId: string) => Promise<{ papers: KnowledgeBasePaperDto[]; total: number; limit: number; offset: number }>;
  search: (kbId: string, query: string, topK?: number) => Promise<{ results: KnowledgeBaseSearchHitDto[]; total: number }>;
  getStorageStats: () => Promise<StorageStatsDto>;
}

export function createKnowledgeBaseApi(client: HttpClient): KnowledgeBaseApi {
  return {
    list: (params) =>
      client.get<KnowledgeBaseListResponse>('/api/v1/knowledge-bases/', {
        params: params as Record<string, unknown> | undefined,
      }),
    create: (data) => client.post<KnowledgeBaseDto>('/api/v1/knowledge-bases/', data),
    get: (id) => client.get<KnowledgeBaseDto>(`/api/v1/knowledge-bases/${id}`),
    update: (id, data) => client.patch<KnowledgeBaseDto>(`/api/v1/knowledge-bases/${id}`, data),
    delete: (id) => client.delete<{ deleted: boolean }>(`/api/v1/knowledge-bases/${id}`),
    listPapers: (kbId) => client.get<{ papers: KnowledgeBasePaperDto[]; total: number; limit: number; offset: number }>(`/api/v1/knowledge-bases/${kbId}/papers`),
    search: (kbId, query, topK) =>
      client.post<{ results: KnowledgeBaseSearchHitDto[]; total: number }>(`/api/v1/knowledge-bases/${kbId}/search`, { query, topK }),
    getStorageStats: () => client.get<StorageStatsDto>('/api/v1/knowledge-bases/storage-stats'),
  };
}
