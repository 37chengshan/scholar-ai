import { useMemo, useState } from 'react';
import { useChunkUpload } from './useChunkUpload';
import { useUploadRecovery } from './useUploadRecovery';
import { useUploadWorkspaceStore } from '@/features/uploads/state/uploadWorkspaceStore';

interface UploadQueueSummary {
  succeeded: number;
  failed: number;
}

export function useUploadWorkspace(knowledgeBaseId: string) {
  const [isUploading, setIsUploading] = useState(false);
  const { uploadFile } = useChunkUpload(knowledgeBaseId);
  const { recoverSession } = useUploadRecovery();

  const items = useUploadWorkspaceStore((state) => state.items);
  const addFiles = useUploadWorkspaceStore((state) => state.addFiles);
  const updateItem = useUploadWorkspaceStore((state) => state.updateItem);
  const removeItem = useUploadWorkspaceStore((state) => state.removeItem);
  const clear = useUploadWorkspaceStore((state) => state.clear);

  const pendingCount = useMemo(
    () => items.filter((item) => item.status === 'pending' || item.status === 'failed').length,
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

        updateItem(item.id, (prev) => ({ ...prev, status: 'preparing', error: undefined }));

        try {
          const result = await uploadFile(item.file, (progress) => {
            updateItem(item.id, (prev) => ({
              ...prev,
              status: progress.status,
              progress: progress.progress,
              importJobId: progress.importJobId,
              uploadSessionId: progress.uploadSessionId,
            }));
          });

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
            status: 'failed',
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
    const state = await recoverSession(sessionId);
    updateItem(itemId, (prev) => ({
      ...prev,
      status: state.status === 'completed' ? 'queued' : 'uploading',
      progress: state.progress,
      uploadSessionId: state.uploadSessionId,
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
