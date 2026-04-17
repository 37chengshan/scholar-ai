import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useImportJobsPolling } from './useImportJobsPolling';

describe('useImportJobsPolling', () => {
  it('triggers an immediate tick and interval ticks when enabled', () => {
    vi.useFakeTimers();
    const onTick = vi.fn();

    renderHook(() => useImportJobsPolling({ enabled: true, intervalMs: 5000, pauseWhenHidden: false, onTick }));

    expect(onTick).toHaveBeenCalledTimes(1);

    act(() => {
      vi.advanceTimersByTime(10000);
    });

    expect(onTick).toHaveBeenCalledTimes(3);
    vi.useRealTimers();
  });

  it('does not tick when disabled', () => {
    vi.useFakeTimers();
    const onTick = vi.fn();

    renderHook(() => useImportJobsPolling({ enabled: false, intervalMs: 5000, pauseWhenHidden: false, onTick }));

    act(() => {
      vi.advanceTimersByTime(10000);
    });

    expect(onTick).not.toHaveBeenCalled();
    vi.useRealTimers();
  });
});
