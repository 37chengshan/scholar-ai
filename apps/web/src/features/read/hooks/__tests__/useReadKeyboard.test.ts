import { describe, expect, it, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useReadKeyboard } from '@/features/read/hooks/useReadKeyboard';

function createOpts(overrides: Record<string, unknown> = {}) {
  return {
    goToPage: vi.fn(),
    currentPage: 1,
    totalPages: 10,
    setScale: vi.fn((updater: (prev: number) => number) => updater(1.0)),
    scale: 1.0,
    setRightTab: vi.fn(),
    setIsPanelOpen: vi.fn(),
    toggleFullscreen: vi.fn(),
    isFullscreen: false,
    dismissFloating: vi.fn(),
    ...overrides,
  };
}

describe('useReadKeyboard', () => {
  it('j key goes to next page', () => {
    const opts = createOpts({ currentPage: 3, totalPages: 10 });
    renderHook(() => useReadKeyboard(opts as any));

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'j' }));
    expect(opts.goToPage).toHaveBeenCalledWith(4);
  });

  it('k key goes to previous page', () => {
    const opts = createOpts({ currentPage: 3, totalPages: 10 });
    renderHook(() => useReadKeyboard(opts as any));

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k' }));
    expect(opts.goToPage).toHaveBeenCalledWith(2);
  });

  it('j key does not exceed total pages', () => {
    const opts = createOpts({ currentPage: 10, totalPages: 10 });
    renderHook(() => useReadKeyboard(opts as any));

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'j' }));
    expect(opts.goToPage).toHaveBeenCalledWith(10);
  });

  it('k key does not go below page 1', () => {
    const opts = createOpts({ currentPage: 1, totalPages: 10 });
    renderHook(() => useReadKeyboard(opts as any));

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k' }));
    expect(opts.goToPage).toHaveBeenCalledWith(1);
  });

  it('] key zooms in', () => {
    const opts = createOpts();
    renderHook(() => useReadKeyboard(opts as any));

    document.dispatchEvent(new KeyboardEvent('keydown', { key: ']' }));
    expect(opts.setScale).toHaveBeenCalled();
  });

  it('[ key zooms out', () => {
    const opts = createOpts();
    renderHook(() => useReadKeyboard(opts as any));

    document.dispatchEvent(new KeyboardEvent('keydown', { key: '[' }));
    expect(opts.setScale).toHaveBeenCalled();
  });

  it('n key opens notes tab', () => {
    const opts = createOpts();
    renderHook(() => useReadKeyboard(opts as any));

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'n' }));
    expect(opts.setRightTab).toHaveBeenCalledWith('notes');
    expect(opts.setIsPanelOpen).toHaveBeenCalledWith(true);
  });

  it('Escape exits fullscreen when in fullscreen', () => {
    const opts = createOpts({ isFullscreen: true });
    renderHook(() => useReadKeyboard(opts as any));

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(opts.toggleFullscreen).toHaveBeenCalled();
  });

  it('Escape dismisses floating toolbar when not fullscreen', () => {
    const opts = createOpts({ isFullscreen: false });
    renderHook(() => useReadKeyboard(opts as any));

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(opts.dismissFloating).toHaveBeenCalled();
  });

  it('does not fire shortcuts when focus is on textarea', () => {
    const opts = createOpts();
    renderHook(() => useReadKeyboard(opts as any));

    const textarea = document.createElement('textarea');
    document.body.appendChild(textarea);
    textarea.focus();

    const event = new KeyboardEvent('keydown', { key: 'j', bubbles: true });
    textarea.dispatchEvent(event);

    expect(opts.goToPage).not.toHaveBeenCalled();
    document.body.removeChild(textarea);
  });

  it('does not fire shortcuts when focus is on input', () => {
    const opts = createOpts();
    renderHook(() => useReadKeyboard(opts as any));

    const input = document.createElement('input');
    document.body.appendChild(input);
    input.focus();

    const event = new KeyboardEvent('keydown', { key: 'j', bubbles: true });
    input.dispatchEvent(event);

    expect(opts.goToPage).not.toHaveBeenCalled();
    document.body.removeChild(input);
  });
});
