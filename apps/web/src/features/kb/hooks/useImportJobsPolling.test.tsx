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

  it('pauses when tab is hidden and resumes when visible', () => {
    vi.useFakeTimers();
    const onTick = vi.fn();

    const visibilityState = { value: 'visible' as 'visible' | 'hidden' };
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => visibilityState.value,
    });

    renderHook(() => useImportJobsPolling({ enabled: true, intervalMs: 1000, pauseWhenHidden: true, onTick }));

    expect(onTick).toHaveBeenCalledTimes(1);

    act(() => {
      visibilityState.value = 'hidden';
      document.dispatchEvent(new Event('visibilitychange'));
      vi.advanceTimersByTime(3000);
    });

    expect(onTick).toHaveBeenCalledTimes(1);

    act(() => {
      visibilityState.value = 'visible';
      document.dispatchEvent(new Event('visibilitychange'));
    });

    expect(onTick).toHaveBeenCalledTimes(2);

    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(onTick).toHaveBeenCalledTimes(4);
    vi.useRealTimers();
  });

  it('stops interval ticks after enabled is turned off', () => {
    vi.useFakeTimers();
    const onTick = vi.fn();

    const { rerender } = renderHook(
      ({ enabled }) => useImportJobsPolling({ enabled, intervalMs: 1000, pauseWhenHidden: false, onTick }),
      { initialProps: { enabled: true } }
    );

    expect(onTick).toHaveBeenCalledTimes(1);

    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(onTick).toHaveBeenCalledTimes(3);

    rerender({ enabled: false });

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(onTick).toHaveBeenCalledTimes(3);
    vi.useRealTimers();
  });
});
