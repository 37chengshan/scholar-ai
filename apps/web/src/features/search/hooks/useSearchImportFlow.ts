import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { importApi } from '@/services/importApi';
import { kbApi } from '@/services/kbApi';
import { toast } from 'sonner';
import { trackImportEvent, trackSearchEvent } from '@/lib/observability/telemetry';

export function useSearchImportFlow() {
  const navigate = useNavigate();
  const requestIdRef = useRef(0);
  const isMountedRef = useRef(true);
  const [showKBSelectModal, setShowKBSelectModal] = useState(false);
  const [pendingImportPaper, setPendingImportPaper] = useState<any>(null);
  const [knowledgeBases, setKnowledgeBases] = useState<any[]>([]);
  const [loadingKBs, setLoadingKBs] = useState(false);
  const [importingPaperId, setImportingPaperId] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      requestIdRef.current += 1;
    };
  }, []);

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
      setImportingPaperId(pendingImportPaper.id);

      let sourceType: 'arxiv' | 'pdf_url';
      let payload: Record<string, unknown>;

      if (pendingImportPaper.source === 'arxiv' && pendingImportPaper.externalId) {
        sourceType = 'arxiv';
        payload = { arxivId: pendingImportPaper.externalId.replace('arXiv:', '') };
      } else if (pendingImportPaper.pdfUrl) {
        sourceType = 'pdf_url';
        payload = { url: pendingImportPaper.pdfUrl };
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
        navigate(`/read/${createResponse.data.paper.paperId}`);
        return;
      }

      for (let i = 0; i < 30; i += 1) {
        if (!isActiveRequest()) {
          return;
        }
        const jobResponse = await importApi.get(jobId);
        if (!isActiveRequest()) {
          return;
        }
        if (jobResponse.data.status === 'completed' && jobResponse.data.paper?.paperId) {
          trackImportEvent({
            event: 'import_completed',
            jobId,
            paperId: jobResponse.data.paper.paperId,
          });
          navigate(`/read/${jobResponse.data.paper.paperId}`);
          return;
        }
        if (jobResponse.data.status === 'failed') {
          trackImportEvent({ event: 'import_failed', jobId });
          break;
        }
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }
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
  }, [navigate, pendingImportPaper]);

  return {
    showKBSelectModal,
    setShowKBSelectModal,
    pendingImportPaper,
    knowledgeBases,
    loadingKBs,
    importingPaperId,
    startImportSelection,
    importToKnowledgeBase,
    cancelImport: () => {
      requestIdRef.current += 1;
      trackImportEvent({ event: 'import_cancelled' });
      if (isMountedRef.current) {
        setImportingPaperId(null);
      }
    },
    clearPendingImport: () => setPendingImportPaper(null),
  };
}
