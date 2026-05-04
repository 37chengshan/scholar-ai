import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useKnowledgeBaseSearch } from './useKnowledgeBaseSearch';
import { kbApi } from '@/services/kbApi';

vi.mock('@/services/kbApi', () => ({
  kbApi: {
    search: vi.fn(),
  },
}));

describe('useKnowledgeBaseSearch', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('clears draft and results when kbId changes', async () => {
    vi.mocked(kbApi.search).mockResolvedValue({
      results: [
        {
          id: 'hit-1',
          paperId: 'paper-1',
          paperTitle: 'Paper One',
          content: 'Snippet',
          page: 2,
          score: 0.9,
          sourceChunkId: 'chunk-1',
        },
      ],
      total: 1,
    } as any);

    const { result, rerender } = renderHook(({ kbId }) => useKnowledgeBaseSearch(kbId), {
      initialProps: { kbId: 'kb-1' as string | undefined },
    });

    act(() => {
      result.current.setSearchDraft('transformer');
    });
    await act(async () => {
      await result.current.search('transformer');
    });

    await waitFor(() => {
      expect(result.current.results).toHaveLength(1);
    });
    expect(result.current.searchDraft).toBe('transformer');

    rerender({ kbId: 'kb-2' });

    await waitFor(() => {
      expect(result.current.results).toBeNull();
    });
    expect(result.current.searchDraft).toBe('');
    expect(result.current.isSearching).toBe(false);
  });
});
