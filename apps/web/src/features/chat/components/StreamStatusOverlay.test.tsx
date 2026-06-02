/**
 * Tests for StreamStatusOverlay
 *
 * Coverage:
 * - Renders during streaming/connecting/retrying states
 * - Hides during idle/completed/error/cancelled states
 * - Shows phase-specific messages
 * - Shows retrying indicator
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StreamStatusOverlay } from './StreamStatusOverlay';

describe('StreamStatusOverlay', () => {
  it('renders during streaming state', () => {
    render(
      <StreamStatusOverlay
        streamStatus="streaming"
        currentPhase="retrieving"
        isZh={false}
      />,
    );

    expect(screen.getByText('Searching papers...')).toBeInTheDocument();
  });

  it('renders during connecting state', () => {
    render(
      <StreamStatusOverlay
        streamStatus="connecting"
        currentPhase="idle"
        isZh={false}
      />,
    );

    expect(screen.getByText('Processing...')).toBeInTheDocument();
  });

  it('renders during retrying state with indicator', () => {
    render(
      <StreamStatusOverlay
        streamStatus="retrying"
        currentPhase="retrieving"
        isZh={false}
      />,
    );

    expect(screen.getByText('Searching papers...')).toBeInTheDocument();
    expect(screen.getByText('(retrying)')).toBeInTheDocument();
  });

  it('does not render during idle state', () => {
    const { container } = render(
      <StreamStatusOverlay
        streamStatus="idle"
        currentPhase="idle"
        isZh={false}
      />,
    );

    expect(container.innerHTML).toBe('');
  });

  it('does not render during completed state', () => {
    const { container } = render(
      <StreamStatusOverlay
        streamStatus="completed"
        currentPhase="done"
        isZh={false}
      />,
    );

    expect(container.innerHTML).toBe('');
  });

  it('does not render during error state', () => {
    const { container } = render(
      <StreamStatusOverlay
        streamStatus="error"
        currentPhase="error"
        isZh={false}
      />,
    );

    expect(container.innerHTML).toBe('');
  });

  it('shows Chinese messages when isZh is true', () => {
    render(
      <StreamStatusOverlay
        streamStatus="streaming"
        currentPhase="synthesizing"
        isZh={true}
      />,
    );

    expect(screen.getByText('正在生成回答...')).toBeInTheDocument();
  });

  it('shows custom phaseLabel when provided', () => {
    render(
      <StreamStatusOverlay
        streamStatus="streaming"
        currentPhase="retrieving"
        phaseLabel="Custom status message"
        isZh={false}
      />,
    );

    expect(screen.getByText('Custom status message')).toBeInTheDocument();
  });

  it('has role=status for accessibility', () => {
    render(
      <StreamStatusOverlay
        streamStatus="streaming"
        currentPhase="analyzing"
        isZh={false}
      />,
    );

    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
