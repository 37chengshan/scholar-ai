/**
 * Tests for StreamStatusToast / useStreamStatusToast
 *
 * Coverage:
 * - Shows error toast on error status
 * - Shows cancelled toast on cancelled status
 * - Does not show toast on other statuses
 * - Error messages are user-friendly (no backend internals)
 * - Retry button calls onRetry
 */
import { renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useStreamStatusToast } from './StreamStatusToast';
import { toast } from 'sonner';

vi.mock('sonner', () => ({
  toast: Object.assign(vi.fn(), {
    error: vi.fn(),
    success: vi.fn(),
  }),
}));

describe('useStreamStatusToast', () => {
  it('shows error toast on error status', () => {
    renderHook(() =>
      useStreamStatusToast({
        streamStatus: 'error',
        isZh: false,
      }),
    );

    expect(toast.error).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        icon: expect.anything(),
      }),
    );
  });

  it('shows cancelled toast on cancelled status', () => {
    renderHook(() =>
      useStreamStatusToast({
        streamStatus: 'cancelled',
        isZh: false,
      }),
    );

    expect(toast).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        icon: expect.anything(),
      }),
    );
  });

  it('does not show toast on streaming status', () => {
    vi.mocked(toast).mockClear();
    vi.mocked(toast.error).mockClear();

    renderHook(() =>
      useStreamStatusToast({
        streamStatus: 'streaming',
        isZh: false,
      }),
    );

    expect(toast.error).not.toHaveBeenCalled();
    expect(toast).not.toHaveBeenCalled();
  });

  it('includes retry action when onRetry is provided', () => {
    const onRetry = vi.fn();

    renderHook(() =>
      useStreamStatusToast({
        streamStatus: 'error',
        isZh: false,
        onRetry,
      }),
    );

    expect(toast.error).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        action: expect.objectContaining({
          label: 'Retry',
        }),
      }),
    );
  });

  it('uses user-friendly message for NETWORK_ERROR', () => {
    renderHook(() =>
      useStreamStatusToast({
        streamStatus: 'error',
        errorCode: 'NETWORK_ERROR',
        isZh: false,
      }),
    );

    expect(toast.error).toHaveBeenCalledWith(
      'Connection lost. Retrying...',
      expect.any(Object),
    );
  });

  it('uses Chinese messages when isZh is true', () => {
    renderHook(() =>
      useStreamStatusToast({
        streamStatus: 'error',
        errorCode: 'TIMEOUT',
        isZh: true,
      }),
    );

    expect(toast.error).toHaveBeenCalledWith(
      '请求超时，请重试',
      expect.any(Object),
    );
  });
});
