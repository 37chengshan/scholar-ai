import { useCallback, type ChangeEvent, type DragEvent } from 'react';
import { Upload, PlayCircle } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/app/components/ui/button';
import { useUploadWorkspace } from '@/features/uploads/hooks/useUploadWorkspace';
import { usePipelineTracker } from '@/features/uploads/hooks/usePipelineTracker';
import { uploadSessionApi } from '@/services/uploadSessionApi';
import { importApi } from '@/services/importApi';
import { UploadQueue } from './UploadQueue';
import type { UploadQueueItem } from '@/features/uploads/state/uploadWorkspaceStore';

interface UploadWorkspaceProps {
  knowledgeBaseId: string;
  onQueueComplete?: () => void | Promise<void>;
}

export function UploadWorkspace({ knowledgeBaseId, onQueueComplete }: UploadWorkspaceProps) {
  usePipelineTracker();

  const {
    items,
    isUploading,
    pendingCount,
    addFiles,
    removeItem,
    updateItem,
    startUploadQueue,
  } = useUploadWorkspace(knowledgeBaseId);

  const handleFileInput = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const selectedFiles = event.target.files ? Array.from(event.target.files) : [];
      const pdfFiles = selectedFiles.filter((file) => file.type === 'application/pdf' || file.name.endsWith('.pdf'));
      if (pdfFiles.length === 0) {
        return;
      }
      addFiles(pdfFiles);
    },
    [addFiles]
  );

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      const droppedFiles = Array.from(event.dataTransfer.files).filter(
        (file) => file.type === 'application/pdf' || file.name.endsWith('.pdf')
      );
      if (droppedFiles.length === 0) {
        return;
      }
      addFiles(droppedFiles);
    },
    [addFiles]
  );

  const runUpload = async () => {
    const summary = await startUploadQueue();

    if (summary.succeeded > 0 && summary.failed === 0) {
      toast.success('上传任务已提交');
      await onQueueComplete?.();
      return;
    }

    if (summary.succeeded > 0 && summary.failed > 0) {
      toast.success(`部分文件已提交：成功 ${summary.succeeded}，失败 ${summary.failed}`);
      await onQueueComplete?.();
      return;
    }

    toast.error('上传失败，请检查文件后重试');
  };

  const handleCancel = useCallback(
    async (item: UploadQueueItem) => {
      try {
        if (item.uploadSessionId) {
          await uploadSessionApi.abortSession(item.uploadSessionId);
        } else if (item.importJobId) {
          await importApi.cancel(item.importJobId);
        }
        updateItem(item.id, (prev) => ({
          ...prev,
          status: 'cancelled',
          error: undefined,
        }));
        toast.success('已取消');
      } catch {
        toast.error('取消失败');
      }
    },
    [updateItem]
  );

  return (
    <div className="space-y-4">
      <div
        className="border-2 border-dashed rounded-lg p-8 text-center transition-colors border-border/50 hover:border-primary/50 hover:bg-primary/5"
        onDrop={handleDrop}
        onDragOver={(event) => event.preventDefault()}
      >
        <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
        <p className="text-sm font-medium text-foreground">拖拽 PDF 文件到此处</p>
        <p className="text-sm text-muted-foreground mt-1">
          或{' '}
          <label className="text-primary cursor-pointer hover:underline">
            点击选择文件
            <input type="file" accept=".pdf" multiple className="hidden" onChange={handleFileInput} />
          </label>
        </p>
        <p className="text-xs text-muted-foreground mt-3">支持 PDF 格式，默认 5MB 分片断点续传</p>
      </div>

      <UploadQueue items={items} onRemove={removeItem} onCancel={handleCancel} removable={!isUploading} />

      <div className="flex justify-end">
        <Button onClick={() => void runUpload()} disabled={isUploading || pendingCount === 0}>
          <PlayCircle className="h-4 w-4 mr-2" />
          {isUploading ? '上传中...' : `开始上传 (${pendingCount})`}
        </Button>
      </div>
    </div>
  );
}
