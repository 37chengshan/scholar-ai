import { renderHook, act, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useChatScopeController } from './useChatScopeController';
import { parseScopeFromQuery } from './chatScopeQuery';

const mocks = vi.hoisted(() => ({
  setSearchParams: vi.fn(),
  paperGet: vi.fn(),
  knowledgeBaseGet: vi.fn(),
  toastInfo: vi.fn(),
  searchParams: new URLSearchParams(),
}));

vi.mock('react-router', async () => {
  const actual = await vi.importActual<any>('react-router');
  return {
    ...actual,
    useSearchParams: () => [mocks.searchParams, mocks.setSearchParams],
  };
});

vi.mock('@/services/papersApi', () => ({
  get: mocks.paperGet,
}));

vi.mock('@/services/kbApi', () => ({
  kbApi: {
    get: mocks.knowledgeBaseGet,
  },
}));

vi.mock('sonner', () => ({
  toast: {
    info: mocks.toastInfo,
  },
}));

describe('useChatScopeController', () => {
  beforeEach(() => {
    mocks.searchParams = new URLSearchParams();
    mocks.setSearchParams.mockReset();
    mocks.paperGet.mockReset();
    mocks.knowledgeBaseGet.mockReset();
    mocks.toastInfo.mockReset();
  });

  it('marks query as error when paperId and kbId coexist', () => {
    const scope = parseScopeFromQuery(new URLSearchParams('paperId=paper-1&kbId=kb-1'));

    expect(scope.type).toBe('error');
    expect(scope.errorMessage).toContain('cannot coexist');
  });

  it('loads paper scope and forces rag mode for scoped sessions', async () => {
    mocks.searchParams = new URLSearchParams('paperId=paper-1');
    mocks.paperGet.mockResolvedValue({ title: 'Paper One' });

    const setMode = vi.fn();
    const setWorkspaceScope = vi.fn();

    const { result } = renderHook(() => useChatScopeController({
      mode: 'auto',
      isZh: true,
      setMode,
      setWorkspaceScope,
    }));

    await waitFor(() => {
      expect(result.current.scope.type).toBe('single_paper');
    });

    expect(result.current.scope.title).toBe('Paper One');
    expect(setWorkspaceScope).toHaveBeenCalledWith(expect.objectContaining({
      type: 'single_paper',
      id: 'paper-1',
      title: 'Paper One',
    }));
    expect(setMode).toHaveBeenCalledWith('rag');
  });

  it('degrades to a usable single-paper scope when paper validation fails', async () => {
    mocks.searchParams = new URLSearchParams('paperId=paper-1');
    mocks.paperGet.mockRejectedValue(new Error('timeout'));

    const setMode = vi.fn();
    const setWorkspaceScope = vi.fn();

    const { result } = renderHook(() => useChatScopeController({
      mode: 'auto',
      isZh: true,
      setMode,
      setWorkspaceScope,
    }));

    await waitFor(() => {
      expect(result.current.scope.type).toBe('single_paper');
    });

    expect(result.current.scope.title).toBe('单论文对话');
    expect(result.current.scopeLoading).toBe(false);
    expect(setWorkspaceScope).toHaveBeenCalledWith(expect.objectContaining({
      type: 'single_paper',
      id: 'paper-1',
      title: '单论文对话',
    }));
    expect(setMode).toHaveBeenCalledWith('rag');
  });

  it('recognizes compare paper_ids as durable chat scope and upgrades mode', async () => {
    mocks.searchParams = new URLSearchParams('paper_ids=paper-1,paper-2,paper-3');

    const setMode = vi.fn();
    const setWorkspaceScope = vi.fn();

    const { result } = renderHook(() => useChatScopeController({
      mode: 'auto',
      isZh: true,
      setMode,
      setWorkspaceScope,
    }));

    await waitFor(() => {
      expect(result.current.scope.type).toBe('general');
    });

    expect(result.current.scope.title).toBe('对比论文集 (3)');
    expect(setWorkspaceScope).toHaveBeenCalledWith(expect.objectContaining({
      type: 'general',
      id: 'paper-1,paper-2,paper-3',
    }));
    expect(setMode).toHaveBeenCalledWith('rag');
  });

  it('clears scoped params on exit', async () => {
    mocks.searchParams = new URLSearchParams('kbId=kb-1');
    mocks.knowledgeBaseGet.mockResolvedValue({ name: 'KB One' });

    const setMode = vi.fn();
    const setWorkspaceScope = vi.fn();

    const { result } = renderHook(() => useChatScopeController({
      mode: 'rag',
      isZh: false,
      setMode,
      setWorkspaceScope,
    }));

    await waitFor(() => {
      expect(mocks.knowledgeBaseGet).toHaveBeenCalledWith('kb-1');
    });

    act(() => {
      result.current.handleExitScope();
    });

    expect(mocks.setSearchParams).toHaveBeenCalledTimes(1);
    expect(setWorkspaceScope).toHaveBeenCalledWith({ type: null, id: null });
    expect(mocks.toastInfo).toHaveBeenCalledWith('Scope cleared');
  });
});
