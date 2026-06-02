/**
 * Upload Page
 *
 * Dedicated page for uploading PDFs to a knowledge base.
 * Route: /knowledge-bases/:kbId/upload
 *
 * Features:
 * - UploadWorkspace for drag-and-drop PDF upload
 * - Pipeline progress tracking via SSE (PipelineProgressCard)
 * - Batch upload mode for >= 3 files
 * - BatchUploadSummary for aggregate progress
 * - Navigation back to KB detail
 */

import { useMemo, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router';
import { ArrowLeft, Upload as UploadIcon, Layers } from 'lucide-react';

import { Button } from '@/app/components/ui/button';
import { UploadWorkspace } from '@/features/uploads/components/UploadWorkspace';
import { PipelineProgressCard } from '@/features/uploads/components/PipelineProgressCard';
import { BatchUploadSummary } from '@/features/uploads/components/BatchUploadSummary';
import { useUploadWorkspaceStore } from '@/features/uploads/state/uploadWorkspaceStore';
import { useBatchUpload } from '@/features/uploads/hooks/useBatchUpload';
import { importApi } from '@/services/importApi';
import { toast } from 'sonner';

const BATCH_THRESHOLD = 3;

function PipelineProgressSection() {
  const items = useUploadWorkspaceStore((state) => state.items);
  const navigate = useNavigate();

  const pipelineItems = useMemo(
    () =>
      items.filter(
        (item) =>
          item.status === 'queued' ||
          item.status === 'completed' ||
          item.status === 'failed' ||
          item.status === 'cancelled'
      ),
    [items]
  );

  if (pipelineItems.length === 0) {
    return null;
  }

  const handleCancel = async (importJobId: string) => {
    try {
      await importApi.cancel(importJobId);
      toast.success('已取消处理');
    } catch {
      // Error handled by apiClient interceptor
    }
  };

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-foreground">处理进度</h3>
      <div className="space-y-3">
        {pipelineItems.map((item) => (
          <PipelineProgressCard
            key={item.id}
            stage={item.pipelineStage ?? ''}
            progress={item.pipelineProgress ?? 0}
            status={
              item.status === 'completed'
                ? 'completed'
                : item.status === 'failed'
                  ? 'error'
                  : item.status === 'cancelled'
                    ? 'cancelled'
                    : 'running'
            }
            fileName={item.fileName}
            error={item.error}
            paperId={item.paperId}
            onCancel={
              item.importJobId ? () => void handleCancel(item.importJobId!) : undefined
            }
            onViewPaper={
              item.paperId ? (paperId) => navigate(`/read/${paperId}`) : undefined
            }
          />
        ))}
      </div>
    </div>
  );
}

function BatchUploadSection({ kbId }: { kbId: string }) {
  const { isBatchUploading, startBatch } = useBatchUpload();
  const items = useUploadWorkspaceStore((state) => state.items);
  const pendingCount = items.filter((i) => i.status === 'pending').length;

  const handleStartBatch = useCallback(() => {
    void startBatch(kbId);
  }, [startBatch, kbId]);

  const handleRetryFailed = useCallback(() => {
    // Reset failed items to pending
    const store = useUploadWorkspaceStore.getState();
    for (const item of store.items) {
      if (item.status === 'failed') {
        store.updateItem(item.id, (prev) => ({
          ...prev,
          status: 'pending',
          error: undefined,
          progress: 0,
        }));
      }
    }
    void startBatch(kbId);
  }, [startBatch, kbId]);

  const handleCancelRemaining = useCallback(() => {
    const store = useUploadWorkspaceStore.getState();
    for (const item of store.items) {
      if (
        item.status === 'uploading' ||
        item.status === 'preparing' ||
        item.status === 'queued'
      ) {
        store.updateItem(item.id, (prev) => ({
          ...prev,
          status: 'cancelled',
        }));
      }
    }
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">批量上传模式</span>
          <span className="text-xs text-muted-foreground">({pendingCount} 个文件)</span>
        </div>
        <Button
          onClick={handleStartBatch}
          disabled={isBatchUploading || pendingCount === 0}
          size="sm"
        >
          {isBatchUploading ? '上传中...' : `批量上传 (${pendingCount})`}
        </Button>
      </div>

      <BatchUploadSummary
        onRetryFailed={handleRetryFailed}
        onCancelRemaining={handleCancelRemaining}
      />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <UploadIcon className="h-12 w-12 text-muted-foreground/40 mb-4" />
      <p className="text-sm text-muted-foreground">
        拖拽 PDF 文件到上方区域或点击选择文件开始上传
      </p>
      <p className="text-xs text-muted-foreground mt-2">
        支持同时选择多个文件，3 个及以上自动启用批量模式
      </p>
    </div>
  );
}

export function Upload() {
  const { id: kbId } = useParams<{ id: string }>();
  const items = useUploadWorkspaceStore((state) => state.items);
  const hasItems = items.length > 0;
  const showBatchMode = items.filter((i) => i.status === 'pending').length >= BATCH_THRESHOLD;

  if (!kbId) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">缺少知识库 ID</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-border/50">
        <Link to={`/knowledge-bases/${kbId}`}>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex items-center gap-2">
          <UploadIcon className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-lg font-semibold font-serif">上传论文</h1>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-2xl mx-auto space-y-8">
          <UploadWorkspace knowledgeBaseId={kbId} />
          {!hasItems && <EmptyState />}
          {showBatchMode && <BatchUploadSection kbId={kbId} />}
          <PipelineProgressSection />
        </div>
      </div>
    </div>
  );
}

export default Upload;
