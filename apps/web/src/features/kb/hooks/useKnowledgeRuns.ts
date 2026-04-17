import { useCallback, useEffect, useState } from 'react';
import apiClient from '@/utils/apiClient';
import type { KnowledgeRunSummary } from '@/features/kb/types/workspace';

function toRunSummary(session: { id: string; title?: string; updatedAt?: string }): KnowledgeRunSummary {
  return {
    id: session.id,
    title: session.title || `Run ${session.id.slice(0, 8)}`,
    updatedAt: session.updatedAt,
  };
}

export function useKnowledgeRuns() {
  const [runs, setRuns] = useState<KnowledgeRunSummary[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(false);

  const loadRuns = useCallback(async () => {
    setLoadingRuns(true);
    try {
      const response = await apiClient.get('/api/v1/sessions');
      const sessions = Array.isArray(response.data) ? response.data : [];
      setRuns(sessions.map((session) => toRunSummary(session)));
    } finally {
      setLoadingRuns(false);
    }
  }, []);

  useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  return {
    runs,
    loadingRuns,
    reloadRuns: loadRuns,
  };
}
