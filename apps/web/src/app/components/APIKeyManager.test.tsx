import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { APIKeyManager } from './APIKeyManager';

vi.mock('@/services/usersApi', () => ({
  getApiKeys: vi.fn(),
  createApiKey: vi.fn(),
  deleteApiKey: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

describe('APIKeyManager', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
  });

  it('shows localized fallback copy instead of raw transport errors', async () => {
    const usersApi = await import('@/services/usersApi');
    vi.mocked(usersApi.getApiKeys).mockRejectedValueOnce(new Error('Network Error'));

    render(<APIKeyManager isZh />);

    await waitFor(() => {
      expect(screen.getByText('暂时无法读取 API 密钥。可能是后端能力未启用，或服务当前返回异常。')).toBeInTheDocument();
    });

    expect(screen.queryByText('Network Error')).not.toBeInTheDocument();
  });
});