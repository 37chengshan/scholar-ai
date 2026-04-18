import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { ToolCallCard } from '../ToolCallCard';
import type { ToolCall } from '@/types/chat';

vi.mock('../../contexts/LanguageContext', () => ({
  useLanguage: () => ({ language: 'zh' }),
}));

describe('ToolCallCard (app/components)', () => {
  const baseToolCall: ToolCall = {
    id: 'tool-1',
    tool: 'rag_search',
    parameters: { query: 'graph rag', limit: 5 },
    status: 'success',
    startedAt: Date.now() - 200,
    completedAt: Date.now(),
  };

  it('renders compact row with display name and status', () => {
    render(<ToolCallCard toolCall={baseToolCall} />);

    expect(screen.getByText('RAG搜索')).toBeInTheDocument();
    expect(screen.getByText('完成')).toBeInTheDocument();
  });

  it('expands to show parameters when clicked', () => {
    render(<ToolCallCard toolCall={baseToolCall} />);

    fireEvent.click(screen.getByText('RAG搜索'));

    expect(screen.getByText('参数')).toBeInTheDocument();
    expect(screen.getByText(/graph rag/)).toBeInTheDocument();
  });

  it('renders error status and error message in expanded result', () => {
    const errorCall: ToolCall = {
      ...baseToolCall,
      id: 'tool-2',
      status: 'error',
      result: { success: false, error: 'Request timeout' },
    };

    render(<ToolCallCard toolCall={errorCall} />);
    fireEvent.click(screen.getByText('RAG搜索'));

    expect(screen.getByText('失败')).toBeInTheDocument();
    expect(screen.getAllByText(/Request timeout/).length).toBeGreaterThan(0);
  });

  it('renders object result payload in expanded view', () => {
    const objectResultCall: ToolCall = {
      ...baseToolCall,
      id: 'tool-3',
      result: { total: 2, papers: ['A', 'B'] },
    };

    render(<ToolCallCard toolCall={objectResultCall} />);
    fireEvent.click(screen.getByText('RAG搜索'));

    expect(screen.getByText('结果')).toBeInTheDocument();
    expect(screen.getByText(/"total": 2/)).toBeInTheDocument();
  });
});
