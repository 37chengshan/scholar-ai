import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useKnowledgeBaseWorkspace } from './useKnowledgeBaseWorkspace';

const mockSetSearchParams = vi.fn();
const mockRefreshAll = vi.fn().mockResolvedValue(undefined);
const mockSetActiveTab = vi.fn();
const mockSetImportDialogOpen = vi.fn();
const mockSetSearchDraft = vi.fn();
const mockSetSearchResults = vi.fn();
let mockLocationState: { importJobId?: string; justImported?: boolean; paperId?: string } | null = {
  importJobId: 'job-1',
  justImported: true,
  paperId: 'paper-1',
};

vi.mock('react-router', async () => {
  const actual = await vi.importActual<any>('react-router');
  return {
    ...actual,
    useSearchParams: () => [new URLSearchParams('tab=papers'), mockSetSearchParams],
    useLocation: () => ({
      pathname: '/knowledge-bases/kb-1',
      search: '?tab=papers',
      state: mockLocationState,
    }),
  };
});

vi.mock('@/features/kb/state/kbWorkspaceStore', () => ({
  useKBWorkspaceStore: () => ({
    activeTab: 'papers',
    isImportDialogOpen: false,
    searchDraft: '',
    searchResults: [],
    setActiveTab: mockSetActiveTab,
    setImportDialogOpen: mockSetImportDialogOpen,
    setSearchDraft: mockSetSearchDraft,
    setSearchResults: mockSetSearchResults,
  }),
}));

vi.mock('@/features/kb/hooks/useKnowledgeBaseQueries', () => ({
  useKnowledgeBaseQueries: () => ({
    kbId: 'kb-1',
    refreshAll: mockRefreshAll,
  }),
}));

vi.mock('@/features/kb/hooks/useKnowledgeBaseSearch', () => ({
  useKnowledgeBaseSearch: () => ({
    searchDraft: '',
    results: [],
  }),
}));

describe('useKnowledgeBaseWorkspace', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocationState = {
      importJobId: 'job-1',
      justImported: true,
      paperId: 'paper-1',
    };
  });

  it('silently refreshes the workspace once when arriving from a just-imported search flow', async () => {
    const { result } = renderHook(() => useKnowledgeBaseWorkspace());

    await waitFor(() => {
      expect(mockRefreshAll).toHaveBeenCalledWith({ silent: true });
    });

    expect(mockRefreshAll).toHaveBeenCalledTimes(1);
    expect(result.current.importedPaperId).toBe('paper-1');
  });

  it('refreshes again when a new just-imported signal arrives for the same knowledge base route', async () => {
    const { rerender } = renderHook(() => useKnowledgeBaseWorkspace());

    await waitFor(() => {
      expect(mockRefreshAll).toHaveBeenCalledTimes(1);
    });

    mockLocationState = {
      importJobId: 'job-2',
      justImported: true,
      paperId: 'paper-2',
    };

    rerender();

    await waitFor(() => {
      expect(mockRefreshAll).toHaveBeenCalledTimes(2);
    });
  });
});