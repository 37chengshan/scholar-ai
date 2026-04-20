import { renderHook, act } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { usePinnedBottom } from './usePinnedBottom';

function createScrollableContainer(scrollTop: number) {
  const container = document.createElement('div');

  Object.defineProperty(container, 'scrollHeight', {
    value: 1000,
    writable: true,
    configurable: true,
  });
  Object.defineProperty(container, 'clientHeight', {
    value: 400,
    writable: true,
    configurable: true,
  });

  container.scrollTop = scrollTop;
  return container;
}

describe('usePinnedBottom', () => {
  it('auto follows when pinned to bottom', () => {
    const container = createScrollableContainer(600); // distance to bottom: 0
    const anchor = document.createElement('div');
    anchor.scrollIntoView = vi.fn();

    const containerRef = { current: container };
    const anchorRef = { current: anchor };

    const { result } = renderHook(() =>
      usePinnedBottom({
        containerRef,
        anchorRef,
        threshold: 100,
        streamFollowIntervalMs: 0,
      })
    );

    expect(result.current.isPinnedToBottom).toBe(true);

    act(() => {
      result.current.maybeFollowBottom('stream');
    });

    expect(anchor.scrollIntoView).toHaveBeenCalledTimes(1);
  });

  it('stops following when user scrolls up and aligns on done', () => {
    const container = createScrollableContainer(600);
    const anchor = document.createElement('div');
    anchor.scrollIntoView = vi.fn();

    const containerRef = { current: container };
    const anchorRef = { current: anchor };

    const { result } = renderHook(() =>
      usePinnedBottom({
        containerRef,
        anchorRef,
        threshold: 100,
        streamFollowIntervalMs: 0,
      })
    );

    act(() => {
      container.scrollTop = 200; // distance to bottom: 400
      container.dispatchEvent(new Event('scroll'));
    });

    expect(result.current.isPinnedToBottom).toBe(false);

    act(() => {
      result.current.maybeFollowBottom('stream');
    });

    expect(anchor.scrollIntoView).not.toHaveBeenCalled();

    act(() => {
      result.current.maybeFollowBottom('done');
    });

    expect(anchor.scrollIntoView).toHaveBeenCalledTimes(1);
  });
});
