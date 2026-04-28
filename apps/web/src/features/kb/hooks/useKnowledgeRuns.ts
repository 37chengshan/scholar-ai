import { useCallback, useEffect, useState } from 'react';
import { kbReviewApi } from '@/services/kbReviewApi';
import type { KnowledgeRunSummary } from '@/features/kb/types/workspace';

function toRunSummary(run: { id: string; status?: string; updatedAt?: string }): KnowledgeRunSummary {
  return {
    id: run.id,
    title: run.status ? `Run ${run.id.slice(0, 8)} (${run.status})` : `Run ${run.id.slice(0, 8)}`,
    status: run.status,
    updatedAt: run.updatedAt,
  };
}

export function useKnowledgeRuns(kbId?: string | null) {
  const [runs, setRuns] = useState<KnowledgeRunSummary[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(false);

  const loadRuns = useCallback(async () => {
    if (!kbId) {
      setRuns([]);
      return;
    }
    setLoadingRuns(true);
    try {
      const response = await kbReviewApi.listRuns(kbId, { limit: 50, offset: 0 });
      const items = Array.isArray(response.items) ? response.items : [];
      setRuns(items.map((run) => toRunSummary(run)));
    } catch {
      setRuns([]);
    } finally {
      setLoadingRuns(false);
    }
  }, [kbId]);

  useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  return {
    runs,
    loadingRuns,
    reloadRuns: loadRuns,
  };
}
