import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import { useKnowledgeBaseQueries } from './useKnowledgeBaseQueries';

vi.mock('react-router', () => ({
  useParams: () => ({ id: 'kb-1' }),
}));

vi.mock('@/services/kbApi', () => ({
  kbApi: {
    get: vi.fn(),
    listPapers: vi.fn(),
  },
}));

vi.mock('@/services/importApi', () => ({
  importApi: {
    list: vi.fn(),
  },
}));

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
  },
}));

import { kbApi } from '@/services/kbApi';
import { importApi } from '@/services/importApi';

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolver) => {
    resolve = resolver;
  });

  return { promise, resolve };
}

describe('useKnowledgeBaseQueries', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(kbApi.get).mockResolvedValue({ id: 'kb-1', name: 'KB' } as any);
    vi.mocked(kbApi.listPapers).mockResolvedValue({ papers: [] } as any);
  });

  it('keeps the latest import jobs response when an older request resolves later', async () => {
    const firstImportJobsRequest = createDeferred<any>();
    const secondImportJobsRequest = createDeferred<any>();

    vi.mocked(importApi.list)
      .mockReturnValueOnce(firstImportJobsRequest.promise)
      .mockReturnValueOnce(secondImportJobsRequest.promise);

    const { result } = renderHook(() => useKnowledgeBaseQueries());

    await act(async () => {
      const refreshPromise = result.current.loadImportJobs({ silent: true });
      secondImportJobsRequest.resolve({
        success: true,
        data: {
          jobs: [{ importJobId: 'job-new', status: 'running' }],
        },
      });
      await refreshPromise;
    });

    await waitFor(() => {
      expect(result.current.importJobs).toEqual([{ importJobId: 'job-new', status: 'running' }]);
    });

    await act(async () => {
      firstImportJobsRequest.resolve({
        success: true,
        data: {
          jobs: [{ importJobId: 'job-old', status: 'created' }],
        },
      });
      await Promise.resolve();
    });

    expect(result.current.importJobs).toEqual([{ importJobId: 'job-new', status: 'running' }]);
  });

  it('does not return stale import jobs from an older request that resolves later', async () => {
    const staleImportJobsRequest = createDeferred<any>();
    const latestImportJobsRequest = createDeferred<any>();

    vi.mocked(importApi.list)
      .mockResolvedValueOnce({ success: true, data: { jobs: [] } } as any)
      .mockReturnValueOnce(staleImportJobsRequest.promise)
      .mockReturnValueOnce(latestImportJobsRequest.promise);

    const { result } = renderHook(() => useKnowledgeBaseQueries());

    await waitFor(() => {
      expect(result.current.importJobs).toEqual([]);
    });

    const stalePromise = result.current.loadImportJobs({ silent: true });
    const latestPromise = result.current.loadImportJobs({ silent: true });

    let latestJobs: unknown;
    await act(async () => {
      latestImportJobsRequest.resolve({
        success: true,
        data: {
          jobs: [{ importJobId: 'job-new', status: 'completed' }],
        },
      });
      latestJobs = await latestPromise;
    });

    expect(latestJobs).toEqual([{ importJobId: 'job-new', status: 'completed' }]);

    let staleJobs: unknown;
    await act(async () => {
      staleImportJobsRequest.resolve({
        success: true,
        data: {
          jobs: [{ importJobId: 'job-old', status: 'created' }],
        },
      });
      staleJobs = await stalePromise;
    });

    expect(staleJobs).toBeUndefined();
    expect(result.current.importJobs).toEqual([{ importJobId: 'job-new', status: 'completed' }]);
  });

  it('keeps the latest papers response when an older request resolves later', async () => {
    const firstPapersRequest = createDeferred<any>();
    const secondPapersRequest = createDeferred<any>();

    vi.mocked(kbApi.listPapers)
      .mockReturnValueOnce(firstPapersRequest.promise)
      .mockReturnValueOnce(secondPapersRequest.promise);
    vi.mocked(importApi.list).mockResolvedValue({ success: true, data: { jobs: [] } } as any);

    const { result } = renderHook(() => useKnowledgeBaseQueries());

    await act(async () => {
      const refreshPromise = result.current.loadPapers({ silent: true });
      secondPapersRequest.resolve({
        papers: [{ id: 'paper-new', title: 'New Paper' }],
      });
      await refreshPromise;
    });

    await waitFor(() => {
      expect(result.current.papers).toEqual([{ id: 'paper-new', title: 'New Paper' }]);
    });

    await act(async () => {
      firstPapersRequest.resolve({
        papers: [{ id: 'paper-old', title: 'Old Paper' }],
      });
      await Promise.resolve();
    });

    expect(result.current.papers).toEqual([{ id: 'paper-new', title: 'New Paper' }]);
  });
});