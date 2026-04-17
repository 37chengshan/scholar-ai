import { describe, expect, it, vi } from 'vitest';

import { useUploadRecovery } from './useUploadRecovery';
import { uploadSessionApi } from '@/services/uploadSessionApi';

vi.mock('@/services/uploadSessionApi', () => ({
  uploadSessionApi: {
    getSession: vi.fn(),
  },
}));

describe('useUploadRecovery', () => {
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
});
