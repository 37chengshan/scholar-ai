import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router';
import { kbApi, KnowledgeBase, KBPaperListItem } from '@/services/kbApi';
import { ImportJob, importApi } from '@/services/importApi';
import { toast } from 'sonner';

interface RefreshOptions {
  silent?: boolean;
}

export function useKnowledgeBaseQueries() {
  const { id: kbId } = useParams<{ id: string }>();

  const [kb, setKB] = useState<KnowledgeBase | null>(null);
  const [papers, setPapers] = useState<KBPaperListItem[]>([]);
  const [importJobs, setImportJobs] = useState<ImportJob[]>([]);
  const [loadingKB, setLoadingKB] = useState(false);
  const [papersLoading, setPapersLoading] = useState(false);
  const [importJobsLoading, setImportJobsLoading] = useState(false);

  const loadKnowledgeBase = useCallback(async (options?: RefreshOptions) => {
    if (!kbId) {
      return;
    }

    if (!options?.silent) {
      setLoadingKB(true);
    }

    try {
      const response = await kbApi.get(kbId);
      setKB(response);
    } catch (error: any) {
      if (!options?.silent) {
        toast.error(error?.message || '加载知识库失败');
      }
    } finally {
      if (!options?.silent) {
        setLoadingKB(false);
      }
    }
  }, [kbId]);

  const loadPapers = useCallback(async (options?: RefreshOptions) => {
    if (!kbId) {
      return;
    }

    if (!options?.silent) {
      setPapersLoading(true);
    }

    try {
      const response = await kbApi.listPapers(kbId);
      setPapers(response.papers || []);
    } catch (error: any) {
      if (!options?.silent) {
        toast.error(error?.message || '加载论文失败');
      }
    } finally {
      if (!options?.silent) {
        setPapersLoading(false);
      }
    }
  }, [kbId]);

  const loadImportJobs = useCallback(async (options?: RefreshOptions) => {
    if (!kbId) {
      return;
    }

    if (!options?.silent) {
      setImportJobsLoading(true);
    }

    try {
      const response = await importApi.list(kbId, { limit: 50 });
      if (response.success && response.data) {
        setImportJobs(response.data.jobs || []);
      }
    } catch {
      // Keep silent to avoid noisy toasts during polling.
    } finally {
      if (!options?.silent) {
        setImportJobsLoading(false);
      }
    }
  }, [kbId]);

  const refreshAll = useCallback(async (options?: RefreshOptions) => {
    await Promise.all([
      loadKnowledgeBase(options),
      loadPapers(options),
      loadImportJobs(options),
    ]);
  }, [loadImportJobs, loadKnowledgeBase, loadPapers]);

  useEffect(() => {
    void refreshAll();
  }, [refreshAll]);

  return {
    kbId,
    kb,
    papers,
    importJobs,
    loadingKB,
    papersLoading,
    importJobsLoading,
    loadKnowledgeBase,
    loadPapers,
    loadImportJobs,
    refreshAll,
  };
}
