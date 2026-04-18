import { describe, it, expect, vi } from 'vitest';
import { createKnowledgeBaseApi } from '../../../../packages/sdk/src/kb/api';
import type { HttpClient } from '../../../../packages/sdk/src/client/http';

describe('createKnowledgeBaseApi', () => {
  it('uses trailing-slash collection endpoints for list/create to avoid FastAPI 307 redirects', async () => {
    const client: HttpClient = {
      get: vi.fn().mockResolvedValue({ knowledgeBases: [], total: 0, limit: 50 }),
      post: vi.fn().mockResolvedValue({ id: 'kb-1', name: 'KB', description: '', category: '其他', paperCount: 0, chunkCount: 0, entityCount: 0, embeddingModel: 'bge-m3', parseEngine: 'docling', chunkStrategy: 'by-paragraph', enableGraph: false, enableImrad: true, enableChartUnderstanding: false, enableMultimodalSearch: false, enableComparison: false, createdAt: '', updatedAt: '', userId: 'u-1' }),
      put: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    };

    const api = createKnowledgeBaseApi(client);

    await api.list({ search: '', sortBy: 'updated', limit: 50, offset: 0 });
    await api.create({ name: 'KB' });

    expect(client.get).toHaveBeenCalledWith('/api/v1/knowledge-bases/', {
      params: { search: '', sortBy: 'updated', limit: 50, offset: 0 },
    });
    expect(client.post).toHaveBeenCalledWith('/api/v1/knowledge-bases/', { name: 'KB' });
  });
});
