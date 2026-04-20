import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TypingText } from '../TypingText';

describe('TypingText', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it('reveals text progressively while streaming', () => {
    render(<TypingText text="Hi" speed={1000} enableMarkdown={false} />);

    expect(screen.queryByText('Hi')).not.toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(20);
    });
    expect(screen.getByText('H')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(20);
    });
    expect(screen.getByText('Hi')).toBeInTheDocument();
  });

  it('renders markdown once typing completes', () => {
    render(<TypingText text="# A" speed={1000} />);

    act(() => {
      vi.advanceTimersByTime(100);
    });

    const heading = document.querySelector('h1');
    expect(heading).toHaveTextContent('A');
  });
});
