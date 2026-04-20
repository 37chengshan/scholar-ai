import { renderHook } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import { useChunkUpload } from './useChunkUpload';
import { importApi } from '@/services/importApi';
import { uploadSessionApi } from '@/services/uploadSessionApi';

vi.mock('@/services/importApi', () => ({
  importApi: {
    create: vi.fn(),
  },
}));

vi.mock('@/services/uploadSessionApi', () => ({
  uploadSessionApi: {
    createSession: vi.fn(),
    getSession: vi.fn(),
    uploadPart: vi.fn(),
    completeSession: vi.fn(),
  },
}));

describe('useChunkUpload', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('crypto', {
      subtle: {
        digest: vi.fn().mockResolvedValue(new Uint8Array(32).buffer),
      },
    });
  });

  it('uploads chunks and completes session', async () => {
    vi.mocked(importApi.create).mockResolvedValue({
      success: true,
      data: { importJobId: 'imp_1' },
    } as any);

    vi.mocked(uploadSessionApi.createSession).mockResolvedValue({
      instantImport: false,
      session: {
        uploadSessionId: 'us_1',
        importJobId: 'imp_1',
        status: 'created',
        chunkSize: 2,
        totalParts: 2,
        uploadedParts: [],
        missingParts: [1, 2],
        uploadedBytes: 0,
        sizeBytes: 4,
        progress: 0,
        expiresAt: new Date().toISOString(),
      },
    });

    vi.mocked(uploadSessionApi.uploadPart)
      .mockResolvedValueOnce({
        uploadSessionId: 'us_1',
        importJobId: 'imp_1',
        status: 'uploading',
        chunkSize: 2,
        totalParts: 2,
        uploadedParts: [1],
        missingParts: [2],
        uploadedBytes: 2,
        sizeBytes: 4,
        progress: 50,
        expiresAt: new Date().toISOString(),
      })
      .mockResolvedValueOnce({
        uploadSessionId: 'us_1',
        importJobId: 'imp_1',
        status: 'uploading',
        chunkSize: 2,
        totalParts: 2,
        uploadedParts: [1, 2],
        missingParts: [],
        uploadedBytes: 4,
        sizeBytes: 4,
        progress: 100,
        expiresAt: new Date().toISOString(),
      });

    vi.mocked(uploadSessionApi.completeSession).mockResolvedValue({
      uploadSessionId: 'us_1',
      importJobId: 'imp_1',
      status: 'completed',
      chunkSize: 2,
      totalParts: 2,
      uploadedParts: [1, 2],
      missingParts: [],
      uploadedBytes: 4,
      sizeBytes: 4,
      progress: 100,
      expiresAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
    });

    const { result } = renderHook(() => useChunkUpload('kb_1'));
    const file = new File([new Uint8Array([1, 2, 3, 4])], 'paper.pdf', {
      type: 'application/pdf',
    });

    const output = await result.current.uploadFile(file);

    expect(output.status).toBe('queued');
    expect(uploadSessionApi.uploadPart).toHaveBeenCalledTimes(2);
    expect(uploadSessionApi.completeSession).toHaveBeenCalledWith('us_1');
  });

  it('handles instant import response', async () => {
    vi.mocked(importApi.create).mockResolvedValue({
      success: true,
      data: { importJobId: 'imp_2' },
    } as any);
    vi.mocked(uploadSessionApi.createSession).mockResolvedValue({
      instantImport: true,
      importJobId: 'imp_2',
      status: 'completed',
    });

    const { result } = renderHook(() => useChunkUpload('kb_1'));
    const file = new File([new Uint8Array([1, 2])], 'paper.pdf', {
      type: 'application/pdf',
    });

    const output = await result.current.uploadFile(file);

    expect(output.status).toBe('completed');
    expect(uploadSessionApi.uploadPart).not.toHaveBeenCalled();
  });

  it('retries transient part upload failures', async () => {
    vi.mocked(importApi.create).mockResolvedValue({
      success: true,
      data: { importJobId: 'imp_3' },
    } as any);

    vi.mocked(uploadSessionApi.createSession).mockResolvedValue({
      instantImport: false,
      session: {
        uploadSessionId: 'us_retry',
        importJobId: 'imp_3',
        status: 'created',
        chunkSize: 4,
        totalParts: 1,
        uploadedParts: [],
        missingParts: [1],
        uploadedBytes: 0,
        sizeBytes: 4,
        progress: 0,
        expiresAt: new Date().toISOString(),
      },
    });

    vi.mocked(uploadSessionApi.uploadPart)
      .mockRejectedValueOnce(new Error('temporary network error'))
      .mockResolvedValueOnce({
        uploadSessionId: 'us_retry',
        importJobId: 'imp_3',
        status: 'uploading',
        chunkSize: 4,
        totalParts: 1,
        uploadedParts: [1],
        missingParts: [],
        uploadedBytes: 4,
        sizeBytes: 4,
        progress: 100,
        expiresAt: new Date().toISOString(),
      });

    vi.mocked(uploadSessionApi.completeSession).mockResolvedValue({
      uploadSessionId: 'us_retry',
      importJobId: 'imp_3',
      status: 'completed',
      chunkSize: 4,
      totalParts: 1,
      uploadedParts: [1],
      missingParts: [],
      uploadedBytes: 4,
      sizeBytes: 4,
      progress: 100,
      expiresAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
    });

    const { result } = renderHook(() => useChunkUpload('kb_1'));
    const file = new File([new Uint8Array([1, 2, 3, 4])], 'retry.pdf', {
      type: 'application/pdf',
    });

    const output = await result.current.uploadFile(file);

    expect(output.status).toBe('queued');
    expect(uploadSessionApi.uploadPart).toHaveBeenCalledTimes(2);
    expect(uploadSessionApi.completeSession).toHaveBeenCalledWith('us_retry');
  });

  it('resumes an existing upload session with missing parts only', async () => {
    vi.mocked(uploadSessionApi.getSession).mockResolvedValue({
      uploadSessionId: 'us_resume',
      importJobId: 'imp_resume',
      status: 'uploading',
      chunkSize: 2,
      totalParts: 3,
      uploadedParts: [1],
      missingParts: [2, 3],
      uploadedBytes: 2,
      sizeBytes: 6,
      progress: 34,
      expiresAt: new Date().toISOString(),
    });

    vi.mocked(uploadSessionApi.uploadPart)
      .mockResolvedValueOnce({
        uploadSessionId: 'us_resume',
        importJobId: 'imp_resume',
        status: 'uploading',
        chunkSize: 2,
        totalParts: 3,
        uploadedParts: [1, 2],
        missingParts: [3],
        uploadedBytes: 4,
        sizeBytes: 6,
        progress: 67,
        expiresAt: new Date().toISOString(),
      })
      .mockResolvedValueOnce({
        uploadSessionId: 'us_resume',
        importJobId: 'imp_resume',
        status: 'uploading',
        chunkSize: 2,
        totalParts: 3,
        uploadedParts: [1, 2, 3],
        missingParts: [],
        uploadedBytes: 6,
        sizeBytes: 6,
        progress: 100,
        expiresAt: new Date().toISOString(),
      });

    vi.mocked(uploadSessionApi.completeSession).mockResolvedValue({
      uploadSessionId: 'us_resume',
      importJobId: 'imp_resume',
      status: 'completed',
      chunkSize: 2,
      totalParts: 3,
      uploadedParts: [1, 2, 3],
      missingParts: [],
      uploadedBytes: 6,
      sizeBytes: 6,
      progress: 100,
      expiresAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
    });

    const { result } = renderHook(() => useChunkUpload('kb_1'));
    const file = new File([new Uint8Array([1, 2, 3, 4, 5, 6])], 'resume.pdf', {
      type: 'application/pdf',
    });

    const output = await result.current.uploadFile(file, undefined, {
      existingImportJobId: 'imp_resume',
      existingUploadSessionId: 'us_resume',
    });

    expect(output.status).toBe('queued');
    expect(importApi.create).not.toHaveBeenCalled();
    expect(uploadSessionApi.createSession).not.toHaveBeenCalled();
    expect(uploadSessionApi.getSession).toHaveBeenCalledWith('us_resume');
    expect(uploadSessionApi.uploadPart).toHaveBeenCalledTimes(2);
    expect(uploadSessionApi.completeSession).toHaveBeenCalledWith('us_resume');
  });

  it('short-circuits already completed sessions without reuploading parts', async () => {
    vi.mocked(uploadSessionApi.getSession).mockResolvedValue({
      uploadSessionId: 'us_done',
      importJobId: 'imp_done',
      status: 'completed',
      chunkSize: 2,
      totalParts: 2,
      uploadedParts: [1, 2],
      missingParts: [],
      uploadedBytes: 4,
      sizeBytes: 4,
      progress: 100,
      expiresAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
    });

    const { result } = renderHook(() => useChunkUpload('kb_1'));
    const file = new File([new Uint8Array([1, 2, 3, 4])], 'done.pdf', {
      type: 'application/pdf',
    });

    const output = await result.current.uploadFile(file, undefined, {
      existingImportJobId: 'imp_done',
      existingUploadSessionId: 'us_done',
    });

    expect(output.status).toBe('queued');
    expect(uploadSessionApi.uploadPart).not.toHaveBeenCalled();
    expect(uploadSessionApi.completeSession).not.toHaveBeenCalled();
  });

  it('rejects aborted sessions instead of retrying cancelled uploads', async () => {
    vi.mocked(uploadSessionApi.getSession).mockResolvedValue({
      uploadSessionId: 'us_aborted',
      importJobId: 'imp_aborted',
      status: 'aborted',
      chunkSize: 2,
      totalParts: 2,
      uploadedParts: [1],
      missingParts: [2],
      uploadedBytes: 2,
      sizeBytes: 4,
      progress: 50,
      expiresAt: new Date().toISOString(),
    });

    const { result } = renderHook(() => useChunkUpload('kb_1'));
    const file = new File([new Uint8Array([1, 2, 3, 4])], 'aborted.pdf', {
      type: 'application/pdf',
    });

    await expect(
      result.current.uploadFile(file, undefined, {
        existingImportJobId: 'imp_aborted',
        existingUploadSessionId: 'us_aborted',
      })
    ).rejects.toThrow('上传会话已取消，请重新创建上传任务');

    expect(uploadSessionApi.uploadPart).not.toHaveBeenCalled();
    expect(uploadSessionApi.completeSession).not.toHaveBeenCalled();
  });
});
