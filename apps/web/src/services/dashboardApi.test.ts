import { beforeEach, describe, expect, it, vi } from 'vitest';

const apiGetMock = vi.fn();

vi.mock('@/utils/apiClient', () => ({
  default: {
    get: apiGetMock,
  },
}));

describe('dashboardApi.getRecentPapers', () => {
  beforeEach(() => {
    apiGetMock.mockReset();
  });

  it('consumes already-unwrapped recent papers payloads from apiClient', async () => {
    apiGetMock.mockResolvedValue({
      data: [
        {
          id: 'paper-1',
          title: 'A Paper',
          currentPage: 4,
        },
      ],
    });

    const { getRecentPapers } = await import('./dashboardApi');
    const papers = await getRecentPapers(3);

    expect(papers).toEqual([{ id: 'paper-1', title: 'A Paper', currentPage: 4 }]);
    expect(apiGetMock).toHaveBeenCalledWith('/api/v1/dashboard/recent-papers', {
      params: { limit: 3 },
    });
  });
});
