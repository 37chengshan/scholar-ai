import { describe, expect, it, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePageNavigation } from '@/features/read/hooks/usePageNavigation';

// Mock react-router
const mockSearchParams = new URLSearchParams();
const mockSetSearchParams = vi.fn();
vi.mock('react-router', () => ({
  useSearchParams: () => [mockSearchParams, mockSetSearchParams],
}));

// Mock papersApi
vi.mock('@/services/papersApi', () => ({
  saveReadingProgress: vi.fn().mockResolvedValue(undefined),
}));

describe('usePageNavigation', () => {
  it('initializes with page 1', () => {
    const { result } = renderHook(() => usePageNavigation('paper-1', true));
    expect(result.current.currentPage).toBe(1);
  });

  it('clampPage returns 1 for values below 1', () => {
    const { result } = renderHook(() => usePageNavigation('paper-1', true));
    expect(result.current.clampPage(0)).toBe(1);
    expect(result.current.clampPage(-5)).toBe(1);
  });

  it('clampPage returns totalPages for values above total', () => {
    const { result } = renderHook(() => usePageNavigation('paper-1', true));

    act(() => {
      result.current.handleNumPagesChange(20);
    });

    expect(result.current.clampPage(25)).toBe(20);
    expect(result.current.clampPage(15)).toBe(15);
  });

  it('clampPage returns the value when within bounds', () => {
    const { result } = renderHook(() => usePageNavigation('paper-1', true));

    act(() => {
      result.current.handleNumPagesChange(20);
    });

    expect(result.current.clampPage(10)).toBe(10);
    expect(result.current.clampPage(1)).toBe(1);
    expect(result.current.clampPage(20)).toBe(20);
  });

  it('handleNumPagesChange updates totalPages', () => {
    const { result } = renderHook(() => usePageNavigation('paper-1', true));

    act(() => {
      result.current.handleNumPagesChange(50);
    });

    expect(result.current.totalPages).toBe(50);
  });

  it('handleNumPagesChange clamps currentPage to numPages', () => {
    const { result } = renderHook(() => usePageNavigation('paper-1', true));

    // First set current page high
    act(() => {
      result.current.goToPage(100);
    });

    // Then set totalPages lower
    act(() => {
      result.current.handleNumPagesChange(5);
    });

    expect(result.current.currentPage).toBeLessThanOrEqual(5);
  });

  it('setScale updates scale', () => {
    const { result } = renderHook(() => usePageNavigation('paper-1', true));

    act(() => {
      result.current.setScale((s) => s + 0.1);
    });

    expect(result.current.scale).toBeCloseTo(1.1);
  });
});
