import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSearchImportFlow } from './useSearchImportFlow';

const mockNavigate = vi.fn();

vi.mock('react-router', async () => {
  const actual = await vi.importActual<any>('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('@/services/kbApi', () => ({
  kbApi: {
    list: vi.fn(),
  },
}));

vi.mock('@/services/importApi', () => ({
  importApi: {
    create: vi.fn(),
    get: vi.fn(),
  },
}));

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

import { kbApi } from '@/services/kbApi';
import { importApi } from '@/services/importApi';

describe('useSearchImportFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('imports an external paper and navigates to read page when job completes', async () => {
    vi.mocked(kbApi.list).mockResolvedValue({
      knowledgeBases: [{ id: 'kb-1', name: 'KB One', paperCount: 3 }],
    } as any);

    vi.mocked(importApi.create).mockResolvedValue({
      data: {
        importJobId: 'job-1',
      },
    } as any);

    vi.mocked(importApi.get).mockResolvedValue({
      data: {
        status: 'completed',
        paper: { paperId: 'paper-42' },
      },
    } as any);

    const { result } = renderHook(() => useSearchImportFlow());

    await act(async () => {
      await result.current.startImportSelection({
        id: 'ext-1',
        title: 'External Paper',
        source: 'arxiv',
        externalId: 'arXiv:2401.00001',
      });
    });

    await act(async () => {
      await result.current.importToKnowledgeBase('kb-1');
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/read/paper-42');
    });
  });
});
