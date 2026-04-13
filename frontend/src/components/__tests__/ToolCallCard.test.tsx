import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ToolCallCard } from '../ToolCallCard';

describe('ToolCallCard', () => {
  const defaultProps = {
    tool: 'rag_search',
    parameters: { query: 'machine learning', limit: 5 },
    status: 'success' as const,
  };

  it('renders tool name with icon', () => {
    render(<ToolCallCard {...defaultProps} />);
    // Should display tool name from TOOL_DISPLAY config
    expect(screen.getByText(/RAG搜索/)).toBeInTheDocument();
    // Icon should be present
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('displays parameters when provided', () => {
    render(<ToolCallCard {...defaultProps} />);
    // Parameters should be shown
    expect(screen.getByText(/query/)).toBeInTheDocument();
    expect(screen.getByText(/machine learning/)).toBeInTheDocument();
  });

  it('shows status indicator for each status type', () => {
    // Pending status
    const { rerender } = render(
      <ToolCallCard {...defaultProps} status="pending" />
    );
    const statusEl = screen.getByRole('status');
    expect(statusEl.className).toMatch(/pending|gray/);

    // Running status
    rerender(<ToolCallCard {...defaultProps} status="running" />);
    expect(screen.getByRole('status').className).toMatch(/running|animate/);

    // Success status
    rerender(<ToolCallCard {...defaultProps} status="success" />);
    expect(screen.getByRole('status').className).toMatch(/success|green/);

    // Error status
    rerender(<ToolCallCard {...defaultProps} status="error" />);
    expect(screen.getByRole('status').className).toMatch(/error|red/);
  });

  it('displays duration when provided', () => {
    render(<ToolCallCard {...defaultProps} duration={1234} />);
    // Duration should be formatted as seconds
    expect(screen.getByText(/1\.23s/)).toBeInTheDocument();
  });

  it('shows fallback indicator when tool used fallback', () => {
    render(
      <ToolCallCard
        {...defaultProps}
        status="success"
        usedFallback={true}
        fallbackTool="external_search"
      />
    );
    // Should show fallback indicator
    expect(screen.getByText(/fallback|备用|外部搜索/)).toBeInTheDocument();
  });

  it('displays error message when status is error', () => {
    render(
      <ToolCallCard
        {...defaultProps}
        status="error"
        error="API timeout occurred"
      />
    );
    expect(screen.getByText(/API timeout occurred/)).toBeInTheDocument();
  });

  it('shows result preview when status is success', () => {
    render(
      <ToolCallCard
        {...defaultProps}
        status="success"
        result={{ papers: ['Paper 1', 'Paper 2'], total: 2 }}
      />
    );
    // Result preview should be shown
    expect(screen.getByText(/total.*2|2.*papers/i)).toBeInTheDocument();
  });

  it('handles unknown tool gracefully', () => {
    render(<ToolCallCard {...defaultProps} tool="unknown_tool" />);
    // Should display the tool name as-is (fallback behavior)
    expect(screen.getByText(/unknown_tool/)).toBeInTheDocument();
  });

  it('applies correct styling for compact mode', () => {
    render(<ToolCallCard {...defaultProps} />);
    // Should have compact styling
    const card = screen.getByTestId('tool-call-card');
    expect(card.className).toMatch(/flex|compact|gap/);
  });

  it('formats duration correctly for different values', () => {
    // Short duration (less than 1 second)
    const { rerender } = render(
      <ToolCallCard {...defaultProps} status="success" duration={500} />
    );
    expect(screen.getByText(/0\.50s/)).toBeInTheDocument();

    // Long duration (over a minute)
    rerender(<ToolCallCard {...defaultProps} status="success" duration={65000} />);
    expect(screen.getByText(/1m.*5s|65\.00s/)).toBeInTheDocument();
  });

  it('does not show parameters section when empty', () => {
    render(<ToolCallCard {...defaultProps} parameters={{}} />);
    // Should not have parameters display
    expect(screen.queryByText(/query/)).not.toBeInTheDocument();
  });
});