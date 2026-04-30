import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { importApi } from '@/services/importApi';
import { kbApi } from '@/services/kbApi';
import { toast } from 'sonner';
import { trackImportEvent, trackSearchEvent } from '@/lib/observability/telemetry';

const IMPORT_JOB_STORAGE_KEY = 'search_import_active_job';
const IMPORT_STAGE_LABELS: Record<string, string> = {
  queued: '排队中',
  resolving: '解析来源',
  downloading: '下载 PDF',
  parsing: '解析文档',
  indexing: '建立索引',
  completed_fulltext_ready: '导入完成',
  completed_metadata_only: '元数据已入库',
  failed: '导入失败',
  cancelled: '已取消',
};


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
  const [selectedKnowledgeBaseId, setSelectedKnowledgeBaseId] = useState<string | null>(null);
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

  const clearTracking = useCallback(() => {
    streamUnsubscribeRef.current?.();
    streamUnsubscribeRef.current = null;
    if (fallbackPollingRef.current) {
      clearTimeout(fallbackPollingRef.current);
      fallbackPollingRef.current = null;
    }
  }, []);

  const finalizeCompletedImport = useCallback(
    async (jobId: string, kbId: string, fallbackPaperId?: string) => {
      let paperId = fallbackPaperId;

      if (!paperId) {
        try {
          const latest = await importApi.get(jobId);
          paperId = latest.data.paper?.paperId ?? undefined;
        } catch {
          paperId = undefined;
        }
      }

      navigateToKnowledgeBase(kbId, {
        importJobId: jobId,
        justImported: true,
        paperId,
      });
      window.sessionStorage.removeItem(IMPORT_JOB_STORAGE_KEY);
      clearTracking();
    },
    [clearTracking, navigateToKnowledgeBase]
  );

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
        if (job.status === 'completed') {
          void finalizeCompletedImport(
            persisted.jobId as string,
            persisted.kbId as string,
            job.paper?.paperId ?? persisted.paperId,
          );
        }
      }).catch(() => {
        window.sessionStorage.removeItem(IMPORT_JOB_STORAGE_KEY);
      });
    } catch {
      window.sessionStorage.removeItem(IMPORT_JOB_STORAGE_KEY);
    }
  }, [finalizeCompletedImport]);

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
            await finalizeCompletedImport(jobId, kbId, job.paper.paperId);
            return;
          }

          if (job.status === 'completed') {
            trackImportEvent({ event: 'import_completed', jobId, paperId: 'unknown' });
            await finalizeCompletedImport(jobId, kbId);
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
    [finalizeCompletedImport]
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

        if (snapshot.status === 'completed') {
          await finalizeCompletedImport(jobId, kbId, snapshot.paper?.paperId ?? undefined);
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
          if (payload.status === 'completed') {
            void finalizeCompletedImport(jobId, kbId);
          }
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
          void finalizeCompletedImport(jobId, kbId, paperId);
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
      void pollUntilTerminal(jobId, kbId, isActiveRequest);
    },
    [clearTracking, finalizeCompletedImport, pollUntilTerminal]
  );

  const loadKnowledgeBases = useCallback(async () => {
    setLoadingKBs(true);
    trackSearchEvent({ event: 'import_kb_list_loading_started' });
    try {
      const response = await kbApi.list({ limit: 100 });
      const bases = response.knowledgeBases || [];
      setKnowledgeBases(bases);
      setSelectedKnowledgeBaseId((current) => current ?? bases[0]?.id ?? null);
      trackSearchEvent({
        event: 'import_kb_list_loaded',
        count: bases.length,
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
    setSelectedKnowledgeBaseId(null);
    setShowKBSelectModal(true);
    await loadKnowledgeBases();
  }, [loadKnowledgeBases]);

  const importToKnowledgeBase = useCallback(async (kbId?: string) => {
    if (!pendingImportPaper) {
      return;
    }
    const targetKbId = kbId ?? selectedKnowledgeBaseId;
    if (!targetKbId) {
      toast.error('请选择目标知识库');
      return;
    }

    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;

    const isActiveRequest = () => isMountedRef.current && requestIdRef.current === requestId;

    try {
      clearTracking();
      setImportingPaperId(pendingImportPaper.id);

      let sourceType: 'arxiv' | 'pdf_url' | 'semantic_scholar';
      let payload: Record<string, unknown>;

      if (pendingImportPaper.source === 'arxiv' && pendingImportPaper.externalId) {
        const arxivId = pendingImportPaper.externalId.replace('arXiv:', '');
        sourceType = 'arxiv';
        payload = {
          arxivId,
          input: arxivId,
        };
      } else if (
        (pendingImportPaper.source === 'semantic_scholar' || pendingImportPaper.source === 's2') &&
        pendingImportPaper.s2PaperId
      ) {
        sourceType = 'semantic_scholar';
        payload = {
          s2PaperId: pendingImportPaper.s2PaperId,
          input: pendingImportPaper.s2PaperId,
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

      const createResponse = await importApi.create(targetKbId, { sourceType, payload });
      if (!isActiveRequest()) {
        return;
      }
      const jobId = createResponse.data.importJobId;
      trackImportEvent({ event: 'import_job_created', jobId, kbId: targetKbId });

      toast.success('论文导入任务已创建');
      setShowKBSelectModal(false);
      setPendingImportPaper(null);
      setSelectedKnowledgeBaseId(null);

      if (createResponse.data.paper?.paperId) {
        await finalizeCompletedImport(jobId, targetKbId, createResponse.data.paper.paperId);
        return;
      }

      await trackImportJob(jobId, targetKbId, isActiveRequest);
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
  }, [
    clearTracking,
    finalizeCompletedImport,
    pendingImportPaper,
    selectedKnowledgeBaseId,
    trackImportJob,
  ]);

  return {
    showKBSelectModal,
    setShowKBSelectModal,
    pendingImportPaper,
    knowledgeBases,
    selectedKnowledgeBaseId,
    setSelectedKnowledgeBaseId,
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
    stageLabel: runtimeStatus?.stage ? (IMPORT_STAGE_LABELS[runtimeStatus.stage] ?? runtimeStatus.stage) : null,
  };
}
