import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import * as searchApi from '@/services/searchApi';
import { useSearch } from './useSearch';

vi.mock('@/services/searchApi', () => ({
  unified: vi.fn(),
}));

type UnifiedResponse = Awaited<ReturnType<typeof searchApi.unified>>;

function buildUnifiedResponse(query: string, offset: number, count: number, total = 60): UnifiedResponse {
  const results = Array.from({ length: count }, (_, index) => ({
    id: `${query}-${offset + index}`,
    title: `${query}-title-${offset + index}`,
    source: 'arxiv' as const,
    year: 2024,
  }));

  return {
    query,
    results,
    total,
    filters: {
      year_from: null,
      year_to: null,
    },
  };
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

afterEach(() => {
  vi.clearAllMocks();
});

describe('useSearch', () => {
  it('keeps previous page results visible while fetching next page', async () => {
    const unifiedMock = vi.mocked(searchApi.unified);
    unifiedMock.mockImplementation(async (query, limit, offset) => {
      await new Promise((resolve) => setTimeout(resolve, 20));
      return buildUnifiedResponse(query, offset ?? 0, limit ?? 20);
    });

    const { result } = renderHook(
      () => useSearch({ initialQuery: 'agent', debounceMs: 1 }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.results?.external[0]?.id).toBe('agent-0');
    });

    act(() => {
      result.current.nextPage();
    });

    expect(result.current.results?.external[0]?.id).toBe('agent-0');

    await waitFor(() => {
      expect(result.current.results?.external[0]?.id).toBe('agent-20');
    });
  });

  it('does not let stale response overwrite newer query', async () => {
    const unifiedMock = vi.mocked(searchApi.unified);
    const pendingResolvers: Record<string, (value: UnifiedResponse) => void> = {};

    unifiedMock.mockImplementation((query, limit, offset) => {
      const key = `${query}-${offset}`;
      return new Promise<UnifiedResponse>((resolve) => {
        pendingResolvers[key] = resolve;
      });
    });

    const { result } = renderHook(
      () => useSearch({ debounceMs: 1 }),
      { wrapper: createWrapper() },
    );

    act(() => {
      result.current.setQuery('first');
    });

    await waitFor(() => {
      expect(unifiedMock).toHaveBeenCalledTimes(1);
    });

    act(() => {
      result.current.setQuery('second');
    });

    await waitFor(() => {
      expect(unifiedMock).toHaveBeenCalledTimes(2);
    });

    await act(async () => {
      pendingResolvers['second-0'](buildUnifiedResponse('second', 0, 20));
    });

    await waitFor(() => {
      expect(result.current.results?.external[0]?.id).toBe('second-0');
    });

    await act(async () => {
      pendingResolvers['first-0'](buildUnifiedResponse('first', 0, 20));
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(result.current.results?.external[0]?.id).toBe('second-0');
  });

  it('reuses cached results immediately when switching back to a previous query', async () => {
    const unifiedMock = vi.mocked(searchApi.unified);
    unifiedMock.mockImplementation(async (query, limit, offset) => (
      buildUnifiedResponse(query, offset ?? 0, limit ?? 20)
    ));

    const wrapper = createWrapper();
    const first = renderHook(
      () => useSearch({ debounceMs: 1 }),
      { wrapper },
    );

    act(() => {
      first.result.current.setQuery('alpha');
    });

    await waitFor(() => {
      expect(first.result.current.results?.external[0]?.id).toBe('alpha-0');
    });

    first.unmount();

    const second = renderHook(
      () => useSearch({ debounceMs: 1, initialQuery: 'alpha' }),
      { wrapper },
    );

    expect(second.result.current.results?.external[0]?.id).toBe('alpha-0');
  });
});
