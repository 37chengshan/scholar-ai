import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useUploadRecovery } from './useUploadRecovery';
import { uploadSessionApi } from '@/services/uploadSessionApi';

vi.mock('@/services/uploadSessionApi', () => ({
  uploadSessionApi: {
    getSession: vi.fn(),
    completeSession: vi.fn(),
  },
}));

describe('useUploadRecovery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads session state from API', async () => {
    const mockState = {
      uploadSessionId: 'us_1',
      importJobId: 'imp_1',
      status: 'uploading',
      chunkSize: 1024,
      totalParts: 4,
      uploadedParts: [1],
      missingParts: [2, 3, 4],
      uploadedBytes: 1024,
      sizeBytes: 4096,
      progress: 25,
      expiresAt: new Date().toISOString(),
    };
    vi.mocked(uploadSessionApi.getSession).mockResolvedValue(mockState as any);

    const { recoverSession } = useUploadRecovery();
    const state = await recoverSession('us_1');

    expect(uploadSessionApi.getSession).toHaveBeenCalledWith('us_1');
    expect(state.progress).toBe(25);
  });

  it('marks recovered uploads without local file for reselection', async () => {
    const mockState = {
      uploadSessionId: 'us_2',
      importJobId: 'imp_2',
      status: 'uploading',
      chunkSize: 1024,
      totalParts: 4,
      uploadedParts: [1, 2],
      missingParts: [3, 4],
      uploadedBytes: 2048,
      sizeBytes: 4096,
      progress: 50,
      expiresAt: new Date().toISOString(),
    };
    vi.mocked(uploadSessionApi.getSession).mockResolvedValue(mockState as any);

    const { recoverUploadItem } = useUploadRecovery();
    const result = await recoverUploadItem({
      uploadSessionId: 'us_2',
      file: undefined,
    });

    expect(result.nextStatus).toBe('needs_file_reselect');
    expect(result.error).toContain('重新选择原始文件');
  });

  it('completes a fully uploaded session before marking it queued', async () => {
    const session = {
      uploadSessionId: 'us_3',
      importJobId: 'imp_3',
      status: 'uploading',
      chunkSize: 1024,
      totalParts: 4,
      uploadedParts: [1, 2, 3, 4],
      missingParts: [],
      uploadedBytes: 4096,
      sizeBytes: 4096,
      progress: 100,
      expiresAt: new Date().toISOString(),
    };
    const completed = {
      ...session,
      status: 'completed',
      completedAt: new Date().toISOString(),
    };
    vi.mocked(uploadSessionApi.getSession).mockResolvedValue(session as any);
    vi.mocked(uploadSessionApi.completeSession).mockResolvedValue(completed as any);

    const { recoverUploadItem } = useUploadRecovery();
    const result = await recoverUploadItem({
      uploadSessionId: 'us_3',
      file: new File([new Uint8Array([1])], 'paper.pdf', { type: 'application/pdf' }),
    });

    expect(uploadSessionApi.completeSession).toHaveBeenCalledWith('us_3');
    expect(result.nextStatus).toBe('queued');
    expect(result.session.status).toBe('completed');
  });

  it('marks aborted sessions as cancelled instead of trying to resume them', async () => {
    const abortedSession = {
      uploadSessionId: 'us_4',
      importJobId: 'imp_4',
      status: 'aborted',
      chunkSize: 1024,
      totalParts: 4,
      uploadedParts: [1],
      missingParts: [2, 3, 4],
      uploadedBytes: 1024,
      sizeBytes: 4096,
      progress: 25,
      expiresAt: new Date().toISOString(),
    };
    vi.mocked(uploadSessionApi.getSession).mockResolvedValue(abortedSession as any);

    const { recoverUploadItem } = useUploadRecovery();
    const result = await recoverUploadItem({
      uploadSessionId: 'us_4',
      file: new File([new Uint8Array([1])], 'paper.pdf', { type: 'application/pdf' }),
    });

    expect(result.nextStatus).toBe('cancelled');
    expect(result.error).toContain('已取消');
    expect(uploadSessionApi.completeSession).not.toHaveBeenCalled();
  });
});
