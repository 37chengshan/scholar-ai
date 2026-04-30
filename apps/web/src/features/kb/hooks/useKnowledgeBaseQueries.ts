import { useCallback, useEffect, useRef, useState } from 'react';
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
  const kbRequestIdRef = useRef(0);
  const papersRequestIdRef = useRef(0);
  const importJobsRequestIdRef = useRef(0);

  const loadKnowledgeBase = useCallback(async (options?: RefreshOptions) => {
    if (!kbId) {
      return;
    }

    const requestId = ++kbRequestIdRef.current;

    if (!options?.silent) {
      setLoadingKB(true);
    }

    try {
      const response = await kbApi.get(kbId);
      if (requestId === kbRequestIdRef.current) {
        setKB(response);
      }
    } catch (error: any) {
      if (!options?.silent) {
        toast.error(error?.message || '加载知识库失败');
      }
    } finally {
      if (requestId === kbRequestIdRef.current) {
        setLoadingKB(false);
      }
    }
  }, [kbId]);

  const loadPapers = useCallback(async (options?: RefreshOptions) => {
    if (!kbId) {
      return;
    }

    const requestId = ++papersRequestIdRef.current;

    if (!options?.silent) {
      setPapersLoading(true);
    }

    try {
      const response = await kbApi.listPapers(kbId);
      if (requestId === papersRequestIdRef.current) {
        setPapers(response.papers || []);
      }
    } catch (error: any) {
      if (!options?.silent) {
        toast.error(error?.message || '加载论文失败');
      }
    } finally {
      if (requestId === papersRequestIdRef.current) {
        setPapersLoading(false);
      }
    }
  }, [kbId]);

  const loadImportJobs = useCallback(async (options?: RefreshOptions) => {
    if (!kbId) {
      return undefined;
    }

    const requestId = ++importJobsRequestIdRef.current;

    if (!options?.silent) {
      setImportJobsLoading(true);
    }

    try {
      const response = await importApi.list(kbId, { limit: 50 });
      if (response.success && response.data) {
        const jobs = response.data.jobs || [];
        if (requestId === importJobsRequestIdRef.current) {
          setImportJobs(jobs);
          return jobs;
        }
      }
    } catch {
      // Keep silent to avoid noisy toasts during polling.
    } finally {
      if (requestId === importJobsRequestIdRef.current) {
        setImportJobsLoading(false);
      }
    }

    return undefined;
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
