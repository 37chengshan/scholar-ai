import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useKnowledgeRuns } from './useKnowledgeRuns';

vi.mock('@/services/kbReviewApi', () => ({
  kbReviewApi: {
    listRuns: vi.fn(),
  },
}));

import { kbReviewApi } from '@/services/kbReviewApi';

describe('useKnowledgeRuns', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads real KB runs and maps status/title', async () => {
    vi.mocked(kbReviewApi.listRuns).mockResolvedValue({
      items: [
        {
          id: 'run-1',
          knowledgeBaseId: 'kb-1',
          reviewDraftId: 'draft-1',
          status: 'completed',
          scope: 'full_kb',
          traceId: 'trace-1',
          createdAt: '2026-01-01T00:00:00Z',
          updatedAt: '2026-01-01T00:00:00Z',
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    } as any);

    const { result } = renderHook(() => useKnowledgeRuns('kb-1'));

    await waitFor(() => {
      expect(result.current.loadingRuns).toBe(false);
      expect(result.current.runs.length).toBe(1);
    });

    expect(result.current.runs[0].id).toBe('run-1');
    expect(result.current.runs[0].title).toContain('completed');
  });

  it('returns empty when kbId is missing', async () => {
    const { result } = renderHook(() => useKnowledgeRuns(undefined));

    await waitFor(() => {
      expect(result.current.runs).toEqual([]);
      expect(result.current.loadingRuns).toBe(false);
    });

    expect(vi.mocked(kbReviewApi.listRuns)).not.toHaveBeenCalled();
  });
});
