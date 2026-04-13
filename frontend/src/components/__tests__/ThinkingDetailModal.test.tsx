import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThinkingDetailModal, Step, ToolCall, TokenUsage } from '../ThinkingDetailModal';

describe('ThinkingDetailModal', () => {
  const mockSteps: Step[] = [
    { name: '分析意图', status: 'success' },
    { name: '执行检索', status: 'running' },
  ];

  const mockToolCalls: ToolCall[] = [
    { tool: 'rag_search', parameters: { query: 'test' }, status: 'running' },
  ];

  const mockTokenUsage: TokenUsage = {
    used: 100,
    cost: 0.01,
  };

  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    steps: mockSteps,
    toolCalls: mockToolCalls,
    tokenUsage: mockTokenUsage,
  };

  it('renders modal with title', () => {
    render(<ThinkingDetailModal {...defaultProps} />);

    expect(screen.getByText('思考详情')).toBeInTheDocument();
  });

  it('renders StepTimeline', () => {
    render(<ThinkingDetailModal {...defaultProps} />);

    expect(screen.getByText('分析意图')).toBeInTheDocument();
    expect(screen.getByText('执行检索')).toBeInTheDocument();
  });

  it('renders tool calls section', () => {
    render(<ThinkingDetailModal {...defaultProps} />);

    expect(screen.getByText('工具调用 (1)')).toBeInTheDocument();
    expect(screen.getByText('RAG搜索')).toBeInTheDocument();
  });

  it('renders token usage in footer', () => {
    render(<ThinkingDetailModal {...defaultProps} />);

    expect(screen.getByText(/100 tokens/)).toBeInTheDocument();
    expect(screen.getByText(/¥0.01/)).toBeInTheDocument();
  });

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn();
    render(<ThinkingDetailModal {...defaultProps} onClose={onClose} />);

    fireEvent.click(screen.getByText('✕'));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when background clicked', () => {
    const onClose = vi.fn();
    render(<ThinkingDetailModal {...defaultProps} onClose={onClose} />);

    // Click on the backdrop (the fixed inset overlay)
    const modalContent = screen.getByText('思考详情').closest('.bg-white');
    const backdrop = modalContent?.parentElement;
    if (backdrop) {
      fireEvent.click(backdrop);
      expect(onClose).toHaveBeenCalledTimes(1);
    }
  });

  it('does not render when isOpen is false', () => {
    render(<ThinkingDetailModal {...defaultProps} isOpen={false} />);

    expect(screen.queryByText('思考详情')).not.toBeInTheDocument();
  });

  it('hides tool calls section when empty', () => {
    render(
      <ThinkingDetailModal
        {...defaultProps}
        toolCalls={[]}
      />
    );

    expect(screen.queryByText('工具调用')).not.toBeInTheDocument();
  });

  it('hides token usage when not provided', () => {
    render(
      <ThinkingDetailModal
        {...defaultProps}
        tokenUsage={undefined}
      />
    );

    expect(screen.queryByText(/tokens/)).not.toBeInTheDocument();
  });

  it('shows step count in section header', () => {
    render(<ThinkingDetailModal {...defaultProps} />);

    expect(screen.getByText('执行步骤 (2)')).toBeInTheDocument();
  });
});