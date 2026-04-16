/**
 * ChatMessageWithThinking Component Tests
 *
 * Tests the integration of ThinkingStatusLine with message content,
 * citations, and expandable thinking details.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ChatMessageWithThinking } from '../ChatMessageWithThinking';

// Types from design
interface Citation {
  source: string;
  excerpt: string;
  page?: number;
}

describe('ChatMessageWithThinking', () => {
  const defaultProps = {
    message: 'This is the AI response content.',
    isStreaming: false,
  };

  it('renders message content', () => {
    render(<ChatMessageWithThinking {...defaultProps} />);
    expect(screen.getByText('This is the AI response content.')).toBeInTheDocument();
  });

  it('renders citations when provided', () => {
    const citations: Citation[] = [
      { source: 'Paper A', excerpt: 'Key finding from paper', page: 5 },
      { source: 'Paper B', excerpt: 'Another important quote' },
    ];
    render(<ChatMessageWithThinking {...defaultProps} citations={citations} />);
    expect(screen.getByText('Paper A')).toBeInTheDocument();
    expect(screen.getByText('Paper B')).toBeInTheDocument();
  });

  it('does not show ThinkingStatusLine when not streaming', () => {
    render(<ChatMessageWithThinking {...defaultProps} />);
    // ThinkingStatusLine should not appear when not streaming
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('shows ThinkingStatusLine when streaming', () => {
    render(
      <ChatMessageWithThinking
        {...defaultProps}
        isStreaming={true}
        thinkingStatus="analyzing"
        thinkingSummary="Analyzing your query..."
      />
    );
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Analyzing your query...')).toBeInTheDocument();
  });

  it('passes step progress to ThinkingStatusLine', () => {
    render(
      <ChatMessageWithThinking
        {...defaultProps}
        isStreaming={true}
        thinkingStatus="executing"
        thinkingSummary="Processing step 2"
        stepProgress={{ current: 2, total: 5 }}
      />
    );
    expect(screen.getByText('2/5')).toBeInTheDocument();
  });

  it('passes duration to ThinkingStatusLine', () => {
    render(
      <ChatMessageWithThinking
        {...defaultProps}
        isStreaming={true}
        thinkingStatus="synthesizing"
        thinkingSummary="Finalizing response"
        duration_ms={12345}
      />
    );
    expect(screen.getByText(/12\.3s/)).toBeInTheDocument();
  });

  it('shows expand button when hasDetails is true (via steps/toolCalls)', () => {
    const steps = [
      { name: 'Step 1', description: 'First step' },
      { name: 'Step 2', description: 'Second step' },
    ];
    render(
      <ChatMessageWithThinking
        {...defaultProps}
        isStreaming={true}
        thinkingStatus="executing"
        thinkingSummary="Processing"
        steps={steps}
      />
    );
    expect(screen.getByRole('button', { name: /expand|details/i })).toBeInTheDocument();
  });

  it('opens details view when expand button is clicked', () => {
    const steps = [
      { name: 'Step 1', description: 'First step' },
      { name: 'Step 2', description: 'Second step' },
    ];
    render(
      <ChatMessageWithThinking
        {...defaultProps}
        isStreaming={true}
        thinkingStatus="executing"
        thinkingSummary="Processing"
        steps={steps}
      />
    );
    const expandBtn = screen.getByRole('button', { name: /expand|details/i });
    fireEvent.click(expandBtn);
    // Details should appear (could be modal or inline expanded view)
    expect(screen.getByText('Step 1')).toBeInTheDocument();
  });

  it('closes details view when close button is clicked', () => {
    const steps = [
      { name: 'Step 1', description: 'First step' },
    ];
    render(
      <ChatMessageWithThinking
        {...defaultProps}
        isStreaming={true}
        thinkingStatus="executing"
        thinkingSummary="Processing"
        steps={steps}
      />
    );
    const expandBtn = screen.getByRole('button', { name: /expand|details/i });
    fireEvent.click(expandBtn);
    expect(screen.getByText('Step 1')).toBeInTheDocument();

    const closeBtn = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeBtn);
    // Details should be hidden
    expect(screen.queryByText('Step 1')).not.toBeInTheDocument();
  });

  it('shows tool calls in details view', () => {
    const toolCalls = [
      { name: 'search', input: { query: 'test' }, output: 'result' },
    ];
    render(
      <ChatMessageWithThinking
        {...defaultProps}
        isStreaming={true}
        thinkingStatus="executing"
        thinkingSummary="Processing"
        toolCalls={toolCalls}
      />
    );
    const expandBtn = screen.getByRole('button', { name: /expand|details/i });
    fireEvent.click(expandBtn);
    expect(screen.getByText('search')).toBeInTheDocument();
  });

  it('shows token usage in details view', () => {
    const tokenUsage = { input: 100, output: 200, total: 300 };
    render(
      <ChatMessageWithThinking
        {...defaultProps}
        isStreaming={true}
        thinkingStatus="synthesizing"
        thinkingSummary="Complete"
        tokenUsage={tokenUsage}
      />
    );
    const expandBtn = screen.getByRole('button', { name: /expand|details/i });
    fireEvent.click(expandBtn);
    expect(screen.getByText(/300/)).toBeInTheDocument();
  });

  it('applies correct message styling', () => {
    render(<ChatMessageWithThinking {...defaultProps} />);
    const messageContainer = screen.getByText('This is the AI response content.').closest('div');
    expect(messageContainer?.className).toMatch(/message|content|prose/);
  });

  it('displays citation page number when available', () => {
    const citations: Citation[] = [
      { source: 'Paper A', excerpt: 'Quote', page: 42 },
    ];
    render(<ChatMessageWithThinking {...defaultProps} citations={citations} />);
    expect(screen.getByText(/42/)).toBeInTheDocument();
  });

  it('handles empty message gracefully', () => {
    render(<ChatMessageWithThinking message="" isStreaming={false} />);
    // Should still render the container
    expect(screen.getByTestId('chat-message-container')).toBeInTheDocument();
  });

  it('does not show expand button when no details available', () => {
    render(
      <ChatMessageWithThinking
        {...defaultProps}
        isStreaming={true}
        thinkingStatus="idle"
        thinkingSummary="Ready"
      />
    );
    expect(screen.queryByRole('button', { name: /expand|details/i })).not.toBeInTheDocument();
  });
});