import { describe, expect, it, vi } from 'vitest';
import { createKnowledgeReviewApi } from '../../../../packages/sdk/src/kb/review';

describe('createKnowledgeReviewApi', () => {
  it('consumes already-unwrapped draft list payloads from sdkHttpClient', async () => {
    const client = {
      get: vi.fn().mockResolvedValue({
        items: [{ id: 'draft-1', title: 'Draft 1' }],
        meta: { total: 1, limit: 50, offset: 0 },
      }),
      post: vi.fn(),
      put: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    };

    const api = createKnowledgeReviewApi(client as any);
    const response = await api.listDrafts('kb-1', { limit: 50, offset: 0 });

    expect(response.items).toEqual([{ id: 'draft-1', title: 'Draft 1' }]);
    expect(response.total).toBe(1);
    expect(client.get).toHaveBeenCalledWith('/api/v1/knowledge-bases/kb-1/review-drafts', {
      params: { limit: 50, offset: 0 },
    });
  });

  it('consumes already-unwrapped run list payloads from sdkHttpClient', async () => {
    const client = {
      get: vi.fn().mockResolvedValue({
        items: [{ id: 'run-1', status: 'completed' }],
        meta: { total: 1, limit: 20, offset: 0 },
      }),
      post: vi.fn(),
      put: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    };

    const api = createKnowledgeReviewApi(client as any);
    const response = await api.listRuns('kb-1');

    expect(response.items).toEqual([{ id: 'run-1', status: 'completed' }]);
    expect(response.total).toBe(1);
  });
});
