import { importApi } from '@/services/importApi';
import { uploadSessionApi } from '@/services/uploadSessionApi';
import { useInstantUpload } from './useInstantUpload';

const DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024;
const MAX_PART_UPLOAD_ATTEMPTS = 3;

interface UploadFileOptions {
  existingImportJobId?: string;
  existingUploadSessionId?: string;
}

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
    onProgress?: (update: UploadProgressUpdate) => void,
    options: UploadFileOptions = {}
  ): Promise<UploadProgressUpdate> => {
    const sessionContext = await initializeUploadSession({
      file,
      knowledgeBaseId,
      isInstantImport,
      options,
    });

    if (sessionContext.kind === 'instant') {
      const instant = {
        importJobId: sessionContext.importJobId,
        progress: 100,
        status: 'completed' as const,
      };
      onProgress?.(instant);
      return instant;
    }

    const { importJobId, uploadSessionId, chunkSize, missingParts, totalParts, currentState } = sessionContext;

    if (currentState.status === 'completed') {
      const queued = {
        importJobId,
        uploadSessionId,
        progress: currentState.progress,
        status: 'queued' as const,
      };
      onProgress?.(queued);
      return queued;
    }

    if (missingParts.length === 0) {
      const completedState = await uploadSessionApi.completeSession(uploadSessionId);
      const queued = {
        importJobId,
        uploadSessionId,
        progress: completedState.progress,
        status: 'queued' as const,
      };
      onProgress?.(queued);
      return queued;
    }

    const partsToUpload = Array.from({ length: missingParts.length }, (_, index) => missingParts[index]);

    for (const partNumber of partsToUpload) {
      const chunkStart = (partNumber - 1) * chunkSize;
      const chunkEnd = Math.min(chunkStart + chunkSize, file.size);
      const chunk = file.slice(chunkStart, chunkEnd);

      const partState = await uploadPartWithRetry(uploadSessionId, partNumber, chunk);

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

async function initializeUploadSession({
  file,
  knowledgeBaseId,
  isInstantImport,
  options,
}: {
  file: File;
  knowledgeBaseId: string;
  isInstantImport: (response: Awaited<ReturnType<typeof uploadSessionApi.createSession>>) => boolean;
  options: UploadFileOptions;
}): Promise<
  | { kind: 'instant'; importJobId: string }
  | {
      kind: 'session';
      importJobId: string;
      uploadSessionId: string;
      chunkSize: number;
      missingParts: number[];
      totalParts: number;
      currentState: Awaited<ReturnType<typeof uploadSessionApi.getSession>>;
    }
> {
  if (options.existingImportJobId && options.existingUploadSessionId) {
    const sessionState = await uploadSessionApi.getSession(options.existingUploadSessionId);

    if (sessionState.status === 'aborted') {
      throw new Error('上传会话已取消，请重新创建上传任务');
    }

    return {
      kind: 'session',
      importJobId: options.existingImportJobId,
      uploadSessionId: sessionState.uploadSessionId,
      chunkSize: sessionState.chunkSize,
      missingParts: sessionState.missingParts,
      totalParts: sessionState.totalParts,
      currentState: sessionState,
    };
  }

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
    return {
      kind: 'instant',
      importJobId,
    };
  }

  if (!sessionResp.session) {
    throw new Error('创建上传会话失败');
  }

  return {
    kind: 'session',
    importJobId,
    uploadSessionId: sessionResp.session.uploadSessionId,
    chunkSize: sessionResp.session.chunkSize,
    missingParts: sessionResp.session.missingParts,
    totalParts: sessionResp.session.totalParts,
    currentState: sessionResp.session,
  };
}

async function uploadPartWithRetry(sessionId: string, partNumber: number, chunk: Blob) {
  let lastError: unknown = null;

  for (let attempt = 1; attempt <= MAX_PART_UPLOAD_ATTEMPTS; attempt += 1) {
    try {
      return await uploadSessionApi.uploadPart(sessionId, partNumber, chunk);
    } catch (error) {
      lastError = error;

      if (attempt === MAX_PART_UPLOAD_ATTEMPTS) {
        break;
      }
    }
  }

  throw lastError instanceof Error ? lastError : new Error(`分片 ${partNumber} 上传失败`);
}

async function computeSha256(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashBytes = Array.from(new Uint8Array(hashBuffer));
  return hashBytes.map((b) => b.toString(16).padStart(2, '0')).join('');
}
