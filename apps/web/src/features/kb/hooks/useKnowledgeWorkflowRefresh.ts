import { useCallback, useEffect, useRef } from 'react';

type RefreshOptions = {
  silent?: boolean;
  refreshDerivedOnCompleted?: boolean;
};

type ImportJobLike = {
  importJobId: string;
  status: string;
};

interface UseKnowledgeWorkflowRefreshOptions {
  importJobs: ImportJobLike[];
  loadImportJobs: (options?: RefreshOptions) => Promise<ImportJobLike[] | void>;
  loadPapers: (options?: RefreshOptions) => Promise<void>;
  loadKnowledgeBase: (options?: RefreshOptions) => Promise<void>;
  reloadRuns: () => Promise<void>;
}

function toStatusMap(importJobs: ImportJobLike[]) {
  return importJobs.reduce<Record<string, string>>((accumulator, job) => {
    return {
      ...accumulator,
      [job.importJobId]: job.status,
    };
  }, {});
}

export function useKnowledgeWorkflowRefresh({
  importJobs,
  loadImportJobs,
  loadPapers,
  loadKnowledgeBase,
  reloadRuns,
}: UseKnowledgeWorkflowRefreshOptions) {
  const previousStatusesRef = useRef<Record<string, string>>({});
  const hasInitializedRef = useRef(false);
  const hasHydratedInitialSnapshotRef = useRef(false);
  const currentStatuses = toStatusMap(importJobs);

  const refreshDerivedArtifacts = useCallback(async () => {
    await Promise.all([
      loadPapers({ silent: true }),
      loadKnowledgeBase({ silent: true }),
      reloadRuns(),
    ]);
  }, [loadKnowledgeBase, loadPapers, reloadRuns]);

  const refreshImportStatus = useCallback(async (options?: RefreshOptions) => {
    const latestJobs = (await loadImportJobs({ silent: true })) ?? [];
    const hasNewlyCompletedJob = latestJobs.some((job) => job.status === 'completed' && currentStatuses[job.importJobId] !== 'completed');

    if (options?.refreshDerivedOnCompleted && hasNewlyCompletedJob) {
      await refreshDerivedArtifacts();
    }
  }, [currentStatuses, loadImportJobs, refreshDerivedArtifacts]);

  useEffect(() => {
    const nextStatuses = toStatusMap(importJobs);

    if (!hasInitializedRef.current) {
      previousStatusesRef.current = nextStatuses;
      hasInitializedRef.current = true;
      return;
    }

    if (!hasHydratedInitialSnapshotRef.current && importJobs.length > 0 && Object.keys(previousStatusesRef.current).length === 0) {
      previousStatusesRef.current = nextStatuses;
      hasHydratedInitialSnapshotRef.current = true;
      return;
    }

    const hasNewlyCompletedJob = importJobs.some((job) => {
      const previousStatus = previousStatusesRef.current[job.importJobId];
      return job.status === 'completed' && previousStatus !== 'completed';
    });

    previousStatusesRef.current = nextStatuses;
    hasHydratedInitialSnapshotRef.current = true;

    if (hasNewlyCompletedJob) {
      void refreshDerivedArtifacts();
    }
  }, [importJobs, refreshDerivedArtifacts]);

  return {
    refreshImportStatus,
    refreshDerivedArtifacts,
  };
}