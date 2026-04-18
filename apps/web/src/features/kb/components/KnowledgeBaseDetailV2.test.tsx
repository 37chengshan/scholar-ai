import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { KnowledgeBaseDetailV2 } from './KnowledgeBaseDetailV2';

vi.mock('@/features/kb/components/KnowledgeWorkspaceShell', () => ({
  KnowledgeWorkspaceShell: () => <div data-testid="kb-workspace-shell">KB Shell</div>,
}));

describe('KnowledgeBaseDetailV2', () => {
  it('renders workspace shell', () => {
    render(<KnowledgeBaseDetailV2 />);
    expect(screen.getByTestId('kb-workspace-shell')).toBeInTheDocument();
  });
});
