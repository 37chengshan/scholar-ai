import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { importApi } from '@/services/importApi';
import { kbApi } from '@/services/kbApi';
import { toast } from 'sonner';
import { trackImportEvent, trackSearchEvent } from '@/lib/observability/telemetry';

const IMPORT_JOB_STORAGE_KEY = 'search_import_active_job';

type ImportRuntimeStatus = {
  jobId: string;
  status: string;
  stage: string;
  error: string | null;
  nextAction: Record<string, unknown> | null;
};

interface SearchImportNavigationState {
  importJobId: string;
  justImported: true;
  paperId?: string;
}

export function useSearchImportFlow() {
  const navigate = useNavigate();
  const requestIdRef = useRef(0);
  const isMountedRef = useRef(true);
  const streamUnsubscribeRef = useRef<(() => void) | null>(null);
  const fallbackPollingRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [showKBSelectModal, setShowKBSelectModal] = useState(false);
  const [pendingImportPaper, setPendingImportPaper] = useState<any>(null);
  const [knowledgeBases, setKnowledgeBases] = useState<any[]>([]);
  const [loadingKBs, setLoadingKBs] = useState(false);
  const [importingPaperId, setImportingPaperId] = useState<string | null>(null);
  const [runtimeStatus, setRuntimeStatus] = useState<ImportRuntimeStatus | null>(null);

  const navigateToKnowledgeBase = useCallback((kbId: string, state: SearchImportNavigationState) => {
    navigate(`/knowledge-bases/${kbId}?tab=papers`, { state });
  }, [navigate]);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      requestIdRef.current += 1;
      streamUnsubscribeRef.current?.();
      streamUnsubscribeRef.current = null;
      if (fallbackPollingRef.current) {
        clearTimeout(fallbackPollingRef.current);
        fallbackPollingRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const raw = window.sessionStorage.getItem(IMPORT_JOB_STORAGE_KEY);
    if (!raw) {
      return;
    }

    try {
      const persisted = JSON.parse(raw) as { jobId?: string; kbId?: string; paperId?: string };
      if (!persisted.jobId || !persisted.kbId) {
        return;
      }

      void importApi.get(persisted.jobId).then((res) => {
        if (!isMountedRef.current) {
          return;
        }
        const job = res.data;
        setRuntimeStatus({
          jobId: persisted.jobId as string,
          status: job.status,
          stage: job.stage,
          error: job.error?.message ?? null,
          nextAction: job.nextAction,
        });
        if (job.status === 'completed' && job.paper?.paperId) {
          navigateToKnowledgeBase(persisted.kbId as string, {
            importJobId: persisted.jobId as string,
            justImported: true,
            paperId: job.paper.paperId,
          });
          window.sessionStorage.removeItem(IMPORT_JOB_STORAGE_KEY);
        }
      }).catch(() => {
        window.sessionStorage.removeItem(IMPORT_JOB_STORAGE_KEY);
      });
    } catch {
      window.sessionStorage.removeItem(IMPORT_JOB_STORAGE_KEY);
    }
  }, [navigateToKnowledgeBase]);

  const clearTracking = useCallback(() => {
    streamUnsubscribeRef.current?.();
    streamUnsubscribeRef.current = null;
    if (fallbackPollingRef.current) {
      clearTimeout(fallbackPollingRef.current);
      fallbackPollingRef.current = null;
    }
  }, []);

  const pollUntilTerminal = useCallback(
    async (jobId: string, kbId: string, isActiveRequest: () => boolean) => {
      const runOnce = async () => {
        if (!isActiveRequest()) {
          return;
        }
        try {
          const jobResponse = await importApi.get(jobId);
          if (!isActiveRequest()) {
            return;
          }

          const job = jobResponse.data;
          setRuntimeStatus({
            jobId,
            status: job.status,
            stage: job.stage,
            error: job.error?.message ?? null,
            nextAction: job.nextAction,
          });

          if (job.status === 'completed' && job.paper?.paperId) {
            trackImportEvent({ event: 'import_completed', jobId, paperId: job.paper.paperId });
            navigateToKnowledgeBase(kbId, {
              importJobId: jobId,
              justImported: true,
              paperId: job.paper.paperId,
            });
            window.sessionStorage.removeItem(IMPORT_JOB_STORAGE_KEY);
            return;
          }

          if (job.status === 'failed' || job.status === 'cancelled') {
            const errorMessage = job.error?.message || '导入任务失败';
            toast.error(errorMessage);
            window.sessionStorage.removeItem(IMPORT_JOB_STORAGE_KEY);
            return;
          }

          fallbackPollingRef.current = setTimeout(() => {
            void runOnce();
          }, 2000);
        } catch {
          fallbackPollingRef.current = setTimeout(() => {
            void runOnce();
          }, 2000);
        }
      };

      await runOnce();
    },
    [navigateToKnowledgeBase]
  );

  const trackImportJob = useCallback(
    async (jobId: string, kbId: string, isActiveRequest: () => boolean) => {
      clearTracking();

      window.sessionStorage.setItem(
        IMPORT_JOB_STORAGE_KEY,
        JSON.stringify({ jobId, kbId })
      );

      try {
        const bootstrap = await importApi.get(jobId);
        const snapshot = bootstrap.data;
        setRuntimeStatus({
          jobId,
          status: snapshot.status,
          stage: snapshot.stage,
          error: snapshot.error?.message ?? null,
          nextAction: snapshot.nextAction,
        });

        if (snapshot.status === 'completed' && snapshot.paper?.paperId) {
          navigateToKnowledgeBase(kbId, {
            importJobId: jobId,
            justImported: true,
            paperId: snapshot.paper.paperId,
          });
          window.sessionStorage.removeItem(IMPORT_JOB_STORAGE_KEY);
          return;
        }
      } catch {
        // Ignore bootstrap failure and continue with stream/fallback.
      }

      streamUnsubscribeRef.current = importApi.subscribeImportJob(jobId, {
        onStatusUpdate: (payload) => {
          if (!isActiveRequest()) {
            return;
          }
          setRuntimeStatus((prev) => ({
            jobId,
            status: payload.status,
            stage: payload.stage,
            error: prev?.error ?? null,
            nextAction: payload.nextAction ?? prev?.nextAction ?? null,
          }));
        },
        onStageChange: (payload) => {
          if (!isActiveRequest()) {
            return;
          }
          setRuntimeStatus((prev) => ({
            jobId,
            status: prev?.status ?? 'running',
            stage: payload.stage,
            error: prev?.error ?? null,
            nextAction: prev?.nextAction ?? null,
          }));
        },
        onProgress: () => {
          // Kept for telemetry expansion; status/stage is the source of truth.
        },
        onCompleted: (payload) => {
          if (!isActiveRequest()) {
            return;
          }
          const paperId = payload.paperId;
          trackImportEvent({ event: 'import_completed', jobId, paperId: paperId || 'unknown' });
          navigateToKnowledgeBase(kbId, {
            importJobId: jobId,
            justImported: true,
            paperId,
          });
          window.sessionStorage.removeItem(IMPORT_JOB_STORAGE_KEY);
          clearTracking();
        },
        onError: (payload) => {
          if (!isActiveRequest()) {
            return;
          }
          const message = payload.message || '导入失败';
          setRuntimeStatus((prev) => ({
            jobId,
            status: 'failed',
            stage: prev?.stage || 'failed',
            error: message,
            nextAction: prev?.nextAction ?? null,
          }));
          toast.error(message);
          window.sessionStorage.removeItem(IMPORT_JOB_STORAGE_KEY);
          clearTracking();
        },
        onCancelled: () => {
          if (!isActiveRequest()) {
            return;
          }
          setRuntimeStatus((prev) => ({
            jobId,
            status: 'cancelled',
            stage: prev?.stage || 'cancelled',
            error: null,
            nextAction: prev?.nextAction ?? null,
          }));
          window.sessionStorage.removeItem(IMPORT_JOB_STORAGE_KEY);
          clearTracking();
        },
        onStreamError: () => {
          if (!isActiveRequest()) {
            return;
          }
          trackImportEvent({ event: 'import_sse_fallback_polling', jobId });
          clearTracking();
          void pollUntilTerminal(jobId, kbId, isActiveRequest);
        },
      });
    },
    [clearTracking, navigateToKnowledgeBase, pollUntilTerminal]
  );

  const loadKnowledgeBases = useCallback(async () => {
    setLoadingKBs(true);
    trackSearchEvent({ event: 'import_kb_list_loading_started' });
    try {
      const response = await kbApi.list({ limit: 100 });
      setKnowledgeBases(response.knowledgeBases || []);
      trackSearchEvent({
        event: 'import_kb_list_loaded',
        count: response.knowledgeBases?.length || 0,
      });
    } catch {
      toast.error('加载知识库列表失败');
      trackSearchEvent({ event: 'import_kb_list_load_failed' });
    } finally {
      setLoadingKBs(false);
    }
  }, []);

  const startImportSelection = useCallback(async (paper: any) => {
    trackImportEvent({ event: 'import_selection_started', paperId: paper?.id });
    setPendingImportPaper(paper);
    setShowKBSelectModal(true);
    await loadKnowledgeBases();
  }, [loadKnowledgeBases]);

  const importToKnowledgeBase = useCallback(async (kbId: string) => {
    if (!pendingImportPaper) {
      return;
    }

    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;

    const isActiveRequest = () => isMountedRef.current && requestIdRef.current === requestId;

    try {
      clearTracking();
      setImportingPaperId(pendingImportPaper.id);

      let sourceType: 'arxiv' | 'pdf_url';
      let payload: Record<string, unknown>;

      if (pendingImportPaper.source === 'arxiv' && pendingImportPaper.externalId) {
        const arxivId = pendingImportPaper.externalId.replace('arXiv:', '');
        sourceType = 'arxiv';
        payload = {
          arxivId,
          input: arxivId,
        };
      } else if (pendingImportPaper.pdfUrl) {
        sourceType = 'pdf_url';
        payload = {
          input: pendingImportPaper.pdfUrl,
          url: pendingImportPaper.pdfUrl,
        };
      } else {
        toast.error('无法导入：缺少 PDF URL 或 arXiv ID');
        return;
      }

      const createResponse = await importApi.create(kbId, { sourceType, payload });
      if (!isActiveRequest()) {
        return;
      }
      const jobId = createResponse.data.importJobId;
      trackImportEvent({ event: 'import_job_created', jobId, kbId });

      toast.success('论文导入任务已创建');
      setShowKBSelectModal(false);
      setPendingImportPaper(null);

      if (createResponse.data.paper?.paperId) {
        navigateToKnowledgeBase(kbId, {
          importJobId: jobId,
          justImported: true,
          paperId: createResponse.data.paper.paperId,
        });
        return;
      }

      await trackImportJob(jobId, kbId, isActiveRequest);
    } catch (error: any) {
      if (isActiveRequest()) {
        toast.error(error?.response?.data?.error?.detail || '导入失败');
        trackImportEvent({ event: 'import_failed', error: error?.message || 'unknown' });
      }
    } finally {
      if (isActiveRequest()) {
        setImportingPaperId(null);
      }
    }
  }, [clearTracking, navigateToKnowledgeBase, pendingImportPaper, trackImportJob]);

  return {
    showKBSelectModal,
    setShowKBSelectModal,
    pendingImportPaper,
    knowledgeBases,
    loadingKBs,
    importingPaperId,
    runtimeStatus,
    startImportSelection,
    importToKnowledgeBase,
    cancelImport: () => {
      requestIdRef.current += 1;
      clearTracking();
      trackImportEvent({ event: 'import_cancelled' });
      if (isMountedRef.current) {
        setImportingPaperId(null);
      }
    },
    clearPendingImport: () => setPendingImportPaper(null),
  };
}
