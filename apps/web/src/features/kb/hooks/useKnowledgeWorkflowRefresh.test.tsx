import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useKnowledgeWorkflowRefresh } from './useKnowledgeWorkflowRefresh';

type ImportJobFixture = {
  importJobId: string;
  status: string;
};

describe('useKnowledgeWorkflowRefresh', () => {
  it('refreshes import status on demand without refreshing derived artifacts', async () => {
    const loadImportJobs = vi.fn().mockResolvedValue([]);
    const loadPapers = vi.fn().mockResolvedValue(undefined);
    const loadKnowledgeBase = vi.fn().mockResolvedValue(undefined);
    const reloadRuns = vi.fn().mockResolvedValue(undefined);

    const { result } = renderHook(() =>
      useKnowledgeWorkflowRefresh({
        importJobs: [],
        loadImportJobs,
        loadPapers,
        loadKnowledgeBase,
        reloadRuns,
      })
    );

    await act(async () => {
      await result.current.refreshImportStatus();
    });

    expect(loadImportJobs).toHaveBeenCalledWith({ silent: true });
    expect(loadPapers).not.toHaveBeenCalled();
    expect(loadKnowledgeBase).not.toHaveBeenCalled();
    expect(reloadRuns).not.toHaveBeenCalled();
  });

  it('refreshes derived artifacts when an import job transitions to completed', async () => {
    const loadImportJobs = vi.fn().mockResolvedValue([]);
    const loadPapers = vi.fn().mockResolvedValue(undefined);
    const loadKnowledgeBase = vi.fn().mockResolvedValue(undefined);
    const reloadRuns = vi.fn().mockResolvedValue(undefined);

    const { rerender } = renderHook(
      ({ importJobs }) =>
        useKnowledgeWorkflowRefresh({
          importJobs,
          loadImportJobs,
          loadPapers,
          loadKnowledgeBase,
          reloadRuns,
        }),
      {
        initialProps: {
          importJobs: [{ importJobId: 'job-1', status: 'running' }],
        },
      }
    );

    await act(async () => {
      rerender({ importJobs: [{ importJobId: 'job-1', status: 'completed' }] });
    });

    expect(loadPapers).toHaveBeenCalledWith({ silent: true });
    expect(loadKnowledgeBase).toHaveBeenCalledWith({ silent: true });
    expect(reloadRuns).toHaveBeenCalledTimes(1);
  });

  it('does not refresh derived artifacts for initially completed jobs', async () => {
    const loadImportJobs = vi.fn().mockResolvedValue([]);
    const loadPapers = vi.fn().mockResolvedValue(undefined);
    const loadKnowledgeBase = vi.fn().mockResolvedValue(undefined);
    const reloadRuns = vi.fn().mockResolvedValue(undefined);

    renderHook(() =>
      useKnowledgeWorkflowRefresh({
        importJobs: [{ importJobId: 'job-1', status: 'completed' }],
        loadImportJobs,
        loadPapers,
        loadKnowledgeBase,
        reloadRuns,
      })
    );

    expect(loadPapers).not.toHaveBeenCalled();
    expect(loadKnowledgeBase).not.toHaveBeenCalled();
    expect(reloadRuns).not.toHaveBeenCalled();
  });

  it('does not refresh derived artifacts when the first hydrated server snapshot already contains completed jobs', async () => {
    const loadImportJobs = vi.fn().mockResolvedValue([]);
    const loadPapers = vi.fn().mockResolvedValue(undefined);
    const loadKnowledgeBase = vi.fn().mockResolvedValue(undefined);
    const reloadRuns = vi.fn().mockResolvedValue(undefined);

    const { rerender } = renderHook(
      ({ importJobs }) =>
        useKnowledgeWorkflowRefresh({
          importJobs,
          loadImportJobs,
          loadPapers,
          loadKnowledgeBase,
          reloadRuns,
        }),
      {
        initialProps: {
          importJobs: [] as ImportJobFixture[],
        },
      }
    );

    await act(async () => {
      rerender({ importJobs: [{ importJobId: 'job-1', status: 'completed' }] });
    });

    expect(loadPapers).not.toHaveBeenCalled();
    expect(loadKnowledgeBase).not.toHaveBeenCalled();
    expect(reloadRuns).not.toHaveBeenCalled();
  });

  it('does not refresh derived artifacts repeatedly when a job remains completed', async () => {
    const loadImportJobs = vi.fn().mockResolvedValue([]);
    const loadPapers = vi.fn().mockResolvedValue(undefined);
    const loadKnowledgeBase = vi.fn().mockResolvedValue(undefined);
    const reloadRuns = vi.fn().mockResolvedValue(undefined);

    const { rerender } = renderHook(
      ({ importJobs }) =>
        useKnowledgeWorkflowRefresh({
          importJobs,
          loadImportJobs,
          loadPapers,
          loadKnowledgeBase,
          reloadRuns,
        }),
      {
        initialProps: {
          importJobs: [{ importJobId: 'job-1', status: 'running' }],
        },
      }
    );

    await act(async () => {
      rerender({ importJobs: [{ importJobId: 'job-1', status: 'completed' }] });
    });

    expect(loadPapers).toHaveBeenCalledTimes(1);
    expect(loadKnowledgeBase).toHaveBeenCalledTimes(1);
    expect(reloadRuns).toHaveBeenCalledTimes(1);

    await act(async () => {
      rerender({ importJobs: [{ importJobId: 'job-1', status: 'completed' }] });
    });

    expect(loadPapers).toHaveBeenCalledTimes(1);
    expect(loadKnowledgeBase).toHaveBeenCalledTimes(1);
    expect(reloadRuns).toHaveBeenCalledTimes(1);
  });

  it('refreshes derived artifacts when an on-demand refresh already observes a completed job', async () => {
    const loadImportJobs = vi.fn().mockResolvedValue([{ importJobId: 'job-1', status: 'completed' }]);
    const loadPapers = vi.fn().mockResolvedValue(undefined);
    const loadKnowledgeBase = vi.fn().mockResolvedValue(undefined);
    const reloadRuns = vi.fn().mockResolvedValue(undefined);

    const { result } = renderHook(() =>
      useKnowledgeWorkflowRefresh({
        importJobs: [],
        loadImportJobs,
        loadPapers,
        loadKnowledgeBase,
        reloadRuns,
      })
    );

    await act(async () => {
      await result.current.refreshImportStatus({ refreshDerivedOnCompleted: true });
    });

    expect(loadImportJobs).toHaveBeenCalledWith({ silent: true });
    expect(loadPapers).toHaveBeenCalledWith({ silent: true });
    expect(loadKnowledgeBase).toHaveBeenCalledWith({ silent: true });
    expect(reloadRuns).toHaveBeenCalledTimes(1);
  });

  it('does not refresh derived artifacts when only historical completed jobs already existed before the on-demand refresh', async () => {
    const loadImportJobs = vi.fn().mockResolvedValue([
      { importJobId: 'job-old', status: 'completed' },
      { importJobId: 'job-new', status: 'running' },
    ]);
    const loadPapers = vi.fn().mockResolvedValue(undefined);
    const loadKnowledgeBase = vi.fn().mockResolvedValue(undefined);
    const reloadRuns = vi.fn().mockResolvedValue(undefined);

    const { result } = renderHook(() =>
      useKnowledgeWorkflowRefresh({
        importJobs: [
          { importJobId: 'job-old', status: 'completed' },
          { importJobId: 'job-new', status: 'created' },
        ],
        loadImportJobs,
        loadPapers,
        loadKnowledgeBase,
        reloadRuns,
      })
    );

    await act(async () => {
      await result.current.refreshImportStatus({ refreshDerivedOnCompleted: true });
    });

    expect(loadPapers).not.toHaveBeenCalled();
    expect(loadKnowledgeBase).not.toHaveBeenCalled();
    expect(reloadRuns).not.toHaveBeenCalled();
  });
});