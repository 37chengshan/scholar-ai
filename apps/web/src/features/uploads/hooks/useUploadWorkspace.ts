import { useMemo, useState } from 'react';
import { useChunkUpload } from './useChunkUpload';
import { useUploadRecovery } from './useUploadRecovery';
import { useUploadWorkspaceStore } from '@/features/uploads/state/uploadWorkspaceStore';

interface UploadQueueSummary {
  succeeded: number;
  failed: number;
}

function isCancelledUploadError(error: unknown): boolean {
  return error instanceof Error && error.message.includes('上传会话已取消');
}

export function useUploadWorkspace(knowledgeBaseId: string) {
  const [isUploading, setIsUploading] = useState(false);
  const { uploadFile } = useChunkUpload(knowledgeBaseId);
  const { recoverUploadItem } = useUploadRecovery();

  const items = useUploadWorkspaceStore((state) => state.items);
  const addFiles = useUploadWorkspaceStore((state) => state.addFiles);
  const updateItem = useUploadWorkspaceStore((state) => state.updateItem);
  const removeItem = useUploadWorkspaceStore((state) => state.removeItem);
  const clear = useUploadWorkspaceStore((state) => state.clear);

  const pendingCount = useMemo(
    () =>
      items.filter(
        (item) => (item.status === 'pending' || item.status === 'failed') && item.file !== undefined
      ).length,
    [items]
  );

  const startUploadQueue = async (): Promise<UploadQueueSummary> => {
    if (isUploading) {
      return { succeeded: 0, failed: 0 };
    }

    let succeeded = 0;
    let failed = 0;
    setIsUploading(true);
    try {
      for (const item of items) {
        if (item.status !== 'pending' && item.status !== 'failed') {
          continue;
        }

        if (!item.file) {
          updateItem(item.id, (prev) => ({
            ...prev,
            status: 'needs_file_reselect',
            error: '请重新选择原始文件后继续上传',
          }));
          failed += 1;
          continue;
        }

        updateItem(item.id, (prev) => ({ ...prev, status: 'preparing', error: undefined }));

        try {
          const result = await uploadFile(
            item.file,
            (progress) => {
              updateItem(item.id, (prev) => ({
                ...prev,
                status: progress.status,
                progress: progress.progress,
                importJobId: progress.importJobId,
                uploadSessionId: progress.uploadSessionId,
              }));
            },
            {
              existingImportJobId: item.importJobId,
              existingUploadSessionId: item.uploadSessionId,
            }
          );

          updateItem(item.id, (prev) => ({
            ...prev,
            status: result.status,
            progress: result.progress,
            importJobId: result.importJobId,
            uploadSessionId: result.uploadSessionId,
          }));
          succeeded += 1;
        } catch (error) {
          const message = error instanceof Error ? error.message : '上传失败';
          updateItem(item.id, (prev) => ({
            ...prev,
            status: isCancelledUploadError(error) ? 'cancelled' : 'failed',
            error: message,
          }));
          failed += 1;
        }
      }

      return { succeeded, failed };
    } finally {
      setIsUploading(false);
    }
  };

  const recoverItem = async (itemId: string, sessionId: string) => {
    const item = items.find((entry) => entry.id === itemId);
    if (!item || item.uploadSessionId !== sessionId) {
      return;
    }

    const recovery = await recoverUploadItem(item);
    updateItem(itemId, (prev) => ({
      ...prev,
      status: recovery.nextStatus,
      progress: recovery.progress,
      uploadSessionId: recovery.session.uploadSessionId,
      error: recovery.error,
    }));
  };

  return {
    items,
    isUploading,
    pendingCount,
    addFiles,
    updateItem,
    removeItem,
    clear,
    startUploadQueue,
    recoverItem,
  };
}
