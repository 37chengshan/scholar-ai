import { beforeEach, describe, expect, it, vi } from 'vitest';

const apiClientMock = {
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
  defaults: { baseURL: '' },
};

vi.mock('@/utils/apiClient', () => ({
  default: apiClientMock,
}));

describe('papersApi contract adapters', () => {
  beforeEach(() => {
    apiClientMock.get.mockReset();
    apiClientMock.post.mockReset();
    apiClientMock.patch.mockReset();
    apiClientMock.delete.mockReset();
  });

  it('posts canonical star payload to the new route', async () => {
    apiClientMock.post.mockResolvedValue({
      data: {
        id: 'paper-1',
        title: 'Paper One',
        authors: [],
        status: 'completed',
        starred: true,
      },
    });

    const { toggleStar } = await import('./papersApi');
    const result = await toggleStar('paper-1', true);

    expect(apiClientMock.post).toHaveBeenCalledWith('/api/v1/papers/paper-1/star', {
      starred: true,
    });
    expect(result.starred).toBe(true);
  });

  it('sends snake_case batch delete payload and preserves traceable result lists', async () => {
    apiClientMock.post.mockResolvedValue({
      data: {
        deletedCount: 1,
        requestedCount: 2,
        deletedIds: ['paper-1'],
        failedIds: ['paper-2'],
        failures: [{ id: 'paper-2', reason: 'not_found_or_not_owned' }],
        message: 'done',
      },
    });

    const { batchDelete } = await import('./papersApi');
    const result = await batchDelete(['paper-1', 'paper-2']);

    expect(apiClientMock.post).toHaveBeenCalledWith('/api/v1/papers/batch-delete', {
      paper_ids: ['paper-1', 'paper-2'],
    });
    expect(result.deletedIds).toEqual(['paper-1']);
    expect(result.failures).toEqual([{ id: 'paper-2', reason: 'not_found_or_not_owned' }]);
  });
});
