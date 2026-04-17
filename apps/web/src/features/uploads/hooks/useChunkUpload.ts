import { importApi } from '@/services/importApi';
import { uploadSessionApi } from '@/services/uploadSessionApi';
import { useInstantUpload } from './useInstantUpload';

const DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024;

export interface UploadProgressUpdate {
  importJobId: string;
  uploadSessionId?: string;
  progress: number;
  status: 'uploading' | 'queued' | 'completed';
}

export function useChunkUpload(knowledgeBaseId: string) {
  const { isInstantImport } = useInstantUpload();

  const uploadFile = async (
    file: File,
    onProgress?: (update: UploadProgressUpdate) => void
  ): Promise<UploadProgressUpdate> => {
    const sha256 = await computeSha256(file);

    const createJobResp = await importApi.create(knowledgeBaseId, {
      sourceType: 'local_file',
      payload: {
        filename: file.name,
        sizeBytes: file.size,
        mimeType: file.type || 'application/pdf',
      },
      options: {
        dedupePolicy: 'prompt',
        autoAttachToKb: true,
      },
    });

    if (!createJobResp.success || !createJobResp.data) {
      throw new Error('创建导入任务失败');
    }

    const importJobId = createJobResp.data.importJobId;

    const sessionResp = await uploadSessionApi.createSession(importJobId, {
      filename: file.name,
      sizeBytes: file.size,
      chunkSize: DEFAULT_CHUNK_SIZE,
      sha256,
      mimeType: file.type || 'application/pdf',
    });

    if (isInstantImport(sessionResp)) {
      const instant = {
        importJobId,
        progress: 100,
        status: 'completed' as const,
      };
      onProgress?.(instant);
      return instant;
    }

    if (!sessionResp.session) {
      throw new Error('创建上传会话失败');
    }

    const { uploadSessionId, chunkSize, missingParts, totalParts } = sessionResp.session;

    const partsToUpload =
      missingParts.length > 0
        ? missingParts
        : Array.from({ length: totalParts }, (_, index) => index + 1);

    for (const partNumber of partsToUpload) {
      const chunkStart = (partNumber - 1) * chunkSize;
      const chunkEnd = Math.min(chunkStart + chunkSize, file.size);
      const chunk = file.slice(chunkStart, chunkEnd);

      const partState = await uploadSessionApi.uploadPart(uploadSessionId, partNumber, chunk);

      onProgress?.({
        importJobId,
        uploadSessionId,
        progress: partState.progress,
        status: 'uploading',
      });
    }

    const completedState = await uploadSessionApi.completeSession(uploadSessionId);
    const queued = {
      importJobId,
      uploadSessionId,
      progress: completedState.progress,
      status: 'queued' as const,
    };
    onProgress?.(queued);

    return queued;
  };

  return {
    uploadFile,
  };
}

async function computeSha256(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashBytes = Array.from(new Uint8Array(hashBuffer));
  return hashBytes.map((b) => b.toString(16).padStart(2, '0')).join('');
}
