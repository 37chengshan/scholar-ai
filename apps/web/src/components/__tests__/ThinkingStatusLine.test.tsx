import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ThinkingStatusLine } from '../ThinkingStatusLine';

// ThinkingStatus type definition (inline for test)
type ThinkingStatus = 'idle' | 'analyzing' | 'planning' | 'executing' | 'synthesizing';

describe('ThinkingStatusLine', () => {
  const defaultProps = {
    status: 'idle' as ThinkingStatus,
    summary: 'Ready to process',
    isStreaming: false,
  };

  it('renders status icon and summary text', () => {
    render(<ThinkingStatusLine {...defaultProps} />);
    expect(screen.getByText('Ready to process')).toBeInTheDocument();
    // Icon should be present (idle state)
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('displays correct status icon for analyzing state', () => {
    render(
      <ThinkingStatusLine
        {...defaultProps}
        status="analyzing"
        summary="Analyzing your query..."
        isStreaming={true}
      />
    );
    expect(screen.getByText('Analyzing your query...')).toBeInTheDocument();
    // Analyzing icon should be present with animation class
    const statusEl = screen.getByRole('status');
    expect(statusEl).toBeInTheDocument();
  });

  it('displays step progress when provided', () => {
    render(
      <ThinkingStatusLine
        {...defaultProps}
        status="executing"
        summary="Processing step 2"
        stepProgress={{ current: 2, total: 5 }}
        isStreaming={true}
      />
    );
    expect(screen.getByText('2/5')).toBeInTheDocument();
  });

  it('displays duration when provided', () => {
    render(
      <ThinkingStatusLine
        {...defaultProps}
        status="synthesizing"
        summary="Finalizing response"
        duration_ms={12345}
        isStreaming={true}
      />
    );
    // Duration should be formatted as seconds
    expect(screen.getByText(/12\.3s/)).toBeInTheDocument();
  });

  it('renders expand button when hasDetails is true', () => {
    const onExpand = vi.fn();
    render(
      <ThinkingStatusLine
        {...defaultProps}
        status="planning"
        summary="Planning execution steps"
        hasDetails={true}
        onExpand={onExpand}
        isStreaming={true}
      />
    );
    const expandBtn = screen.getByRole('button', { name: /expand|details/i });
    expect(expandBtn).toBeInTheDocument();
  });

  it('calls onExpand when expand button is clicked', () => {
    const onExpand = vi.fn();
    render(
      <ThinkingStatusLine
        {...defaultProps}
        status="planning"
        summary="Planning execution steps"
        hasDetails={true}
        onExpand={onExpand}
        isStreaming={true}
      />
    );
    const expandBtn = screen.getByRole('button', { name: /expand|details/i });
    expandBtn.click();
    expect(onExpand).toHaveBeenCalledTimes(1);
  });

  it('applies streaming animation class when isStreaming is true', () => {
    render(
      <ThinkingStatusLine
        {...defaultProps}
        status="analyzing"
        summary="Analyzing..."
        isStreaming={true}
      />
    );
    // Streaming should have a pulsing/flowing effect
    const summaryEl = screen.getByText('Analyzing...');
    expect(summaryEl.className).toMatch(/animate|streaming|pulse/);
  });

  it('does not show expand button when hasDetails is false', () => {
    render(
      <ThinkingStatusLine
        {...defaultProps}
        status="idle"
        summary="Ready"
        hasDetails={false}
        isStreaming={false}
      />
    );
    expect(screen.queryByRole('button', { name: /expand|details/i })).not.toBeInTheDocument();
  });

  it('displays synthesizing status with success styling', () => {
    render(
      <ThinkingStatusLine
        {...defaultProps}
        status="synthesizing"
        summary="Response complete"
        isStreaming={false}
      />
    );
    const statusEl = screen.getByRole('status');
    expect(statusEl.className).toMatch(/green|success/);
  });

  it('formats duration correctly for different values', () => {
    // Short duration (less than 1 second)
    const { rerender } = render(
      <ThinkingStatusLine
        {...defaultProps}
        status="executing"
        summary="Quick step"
        duration_ms={500}
        isStreaming={true}
      />
    );
    expect(screen.getByText(/0\.5s/)).toBeInTheDocument();

    // Long duration (over a minute)
    rerender(
      <ThinkingStatusLine
        {...defaultProps}
        status="executing"
        summary="Long operation"
        duration_ms={90000}
        isStreaming={true}
      />
    );
    expect(screen.getByText(/1m 30s|90\.0s/)).toBeInTheDocument();
  });
});