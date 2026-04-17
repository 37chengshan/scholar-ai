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
});
