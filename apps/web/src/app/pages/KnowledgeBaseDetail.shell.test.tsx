import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { KnowledgeBaseDetail } from './KnowledgeBaseDetail';

vi.mock('@/features/kb/components/KnowledgeBaseWorkspace', () => ({
  KnowledgeBaseWorkspace: () => <div data-testid="kb-workspace">kb-workspace</div>,
}));

describe('KnowledgeBaseDetail page shell', () => {
  it('renders knowledge base workspace container', () => {
    render(<KnowledgeBaseDetail />);
    expect(screen.getByTestId('kb-workspace')).toBeInTheDocument();
  });
});
