/**
 * ThinkingDetailModal Test Suite
 *
 * Tests for modal rendering, keyboard close, and content display.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThinkingDetailModal } from '../ThinkingDetailModal';
import type { Step } from '../StepTimeline';
import type { ToolCall } from '../../../types/chat';

// Mock useLanguage - path relative to this test file
vi.mock('../../contexts/LanguageContext', () => ({
  useLanguage: () => ({ language: 'zh' }),
}));

// Sample test data
const mockSteps: Step[] = [
  { name: '分析请求', status: 'success', duration: 150 },
  { name: '检索论文', status: 'success', duration: 320 },
  { name: '生成回答', status: 'running', duration: 0 },
];

const mockToolCalls: ToolCall[] = [
  {
    id: 'tool-1',
    tool: 'rag_search',
    parameters: { query: 'test query' },
    status: 'success',
    result: { matches: [] },
    duration: 320,
    startedAt: Date.now() - 500,
    completedAt: Date.now() - 180,
  },
  {
    id: 'tool-2',
    tool: 'read_paper',
    parameters: { paper_id: '123' },
    status: 'running',
    startedAt: Date.now(),
  },
];

const mockTokenUsage = {
  used: 2500,
  cost: 0.0025,
};

describe('ThinkingDetailModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Visibility', () => {
    it('should not render when isOpen is false', () => {
      render(
        <ThinkingDetailModal
          isOpen={false}
          onClose={vi.fn()}
          steps={[]}
          toolCalls={[]}
        />
      );

      expect(screen.queryByText('思考详情')).not.toBeInTheDocument();
    });

    it('should render when isOpen is true', () => {
      render(
        <ThinkingDetailModal
          isOpen={true}
          onClose={vi.fn()}
          steps={mockSteps}
          toolCalls={mockToolCalls}
        />
      );

      expect(screen.getByText('思考详情')).toBeInTheDocument();
    });
  });

  describe('Close behavior', () => {
    it('should call onClose when ESC key is pressed', async () => {
      const onClose = vi.fn();
      render(
        <ThinkingDetailModal
          isOpen={true}
          onClose={onClose}
          steps={[]}
          toolCalls={[]}
        />
      );

      await userEvent.type(document.body, '{Escape}');

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('should call onClose when backdrop is clicked', async () => {
      const onClose = vi.fn();
      render(
        <ThinkingDetailModal
          isOpen={true}
          onClose={onClose}
          steps={[]}
          toolCalls={[]}
        />
      );

      // Click backdrop (first element with bg-black/50 class)
      const backdrop = document.querySelector('.bg-black\\/50');
      if (backdrop) {
        fireEvent.click(backdrop);
      }

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('should call onClose when close button is clicked', async () => {
      const onClose = vi.fn();
      render(
        <ThinkingDetailModal
          isOpen={true}
          onClose={onClose}
          steps={[]}
          toolCalls={[]}
        />
      );

      const closeButton = screen.getByRole('button', { name: '关闭' });
      await userEvent.click(closeButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('Content display', () => {
    it('should display step timeline section', () => {
      render(
        <ThinkingDetailModal
          isOpen={true}
          onClose={vi.fn()}
          steps={mockSteps}
          toolCalls={[]}
        />
      );

      expect(screen.getByText('执行步骤')).toBeInTheDocument();
      expect(screen.getByText('分析请求')).toBeInTheDocument();
      expect(screen.getByText('检索论文')).toBeInTheDocument();
      expect(screen.getByText('生成回答')).toBeInTheDocument();
    });

    it('should display tool calls section', () => {
      render(
        <ThinkingDetailModal
          isOpen={true}
          onClose={vi.fn()}
          steps={[]}
          toolCalls={mockToolCalls}
        />
      );

      expect(screen.getByText('工具调用')).toBeInTheDocument();
      expect(screen.getByText('RAG搜索')).toBeInTheDocument();
      expect(screen.getByText('阅读论文')).toBeInTheDocument();
    });

    it('should display token usage in footer', () => {
      render(
        <ThinkingDetailModal
          isOpen={true}
          onClose={vi.fn()}
          steps={[]}
          toolCalls={[]}
          tokenUsage={mockTokenUsage}
        />
      );

      // Footer shows Tokens and Cost labels directly (no header)
      expect(screen.getByText('2,500')).toBeInTheDocument();
      expect(screen.getByText('$0.0025')).toBeInTheDocument();
    });

    it('should show empty state when no steps', () => {
      render(
        <ThinkingDetailModal
          isOpen={true}
          onClose={vi.fn()}
          steps={[]}
          toolCalls={[]}
        />
      );

      expect(screen.getByText('暂无执行步骤')).toBeInTheDocument();
      expect(screen.getByText('暂无工具调用')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have accessible close button', () => {
      render(
        <ThinkingDetailModal
          isOpen={true}
          onClose={vi.fn()}
          steps={[]}
          toolCalls={[]}
        />
      );

      const closeButton = screen.getByRole('button', { name: '关闭' });
      expect(closeButton).toBeInTheDocument();
    });

    it('should have proper heading structure', () => {
      render(
        <ThinkingDetailModal
          isOpen={true}
          onClose={vi.fn()}
          steps={mockSteps}
          toolCalls={mockToolCalls}
        />
      );

      // Main title
      expect(screen.getByRole('heading', { level: 2, name: '思考详情' })).toBeInTheDocument();

      // Section headings
      expect(screen.getByText('执行步骤')).toBeInTheDocument();
      expect(screen.getByText('工具调用')).toBeInTheDocument();
    });
  });
});