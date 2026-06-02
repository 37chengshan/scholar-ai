import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router';
import { Upload } from './Upload';

vi.mock('@/features/uploads/components/UploadWorkspace', () => ({
  UploadWorkspace: ({ knowledgeBaseId }: { knowledgeBaseId: string }) => (
    <div data-testid="upload-workspace">UploadWorkspace: {knowledgeBaseId}</div>
  ),
}));

vi.mock('@/features/uploads/components/PipelineProgressCard', () => ({
  PipelineProgressCard: () => <div data-testid="pipeline-card" />,
}));

vi.mock('@/features/uploads/components/BatchUploadSummary', () => ({
  BatchUploadSummary: () => <div data-testid="batch-summary" />,
}));

vi.mock('@/features/uploads/state/uploadWorkspaceStore', () => ({
  useUploadWorkspaceStore: (selector: (state: { items: unknown[] }) => unknown) => {
    const state = { items: [] };
    return selector(state);
  },
}));

describe('Upload Page', () => {
  it('renders upload workspace with kbId', () => {
    render(
      <MemoryRouter initialEntries={['/knowledge-bases/kb_123/upload']}>
        <Routes>
          <Route path="/knowledge-bases/:id/upload" element={<Upload />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/上传论文/)).toBeInTheDocument();
    expect(screen.getByTestId('upload-workspace')).toBeInTheDocument();
    expect(screen.getByText(/kb_123/)).toBeInTheDocument();
  });

  it('renders back link to KB detail', () => {
    render(
      <MemoryRouter initialEntries={['/knowledge-bases/kb_123/upload']}>
        <Routes>
          <Route path="/knowledge-bases/:id/upload" element={<Upload />} />
        </Routes>
      </MemoryRouter>
    );

    const backLink = screen.getByRole('link');
    expect(backLink).toHaveAttribute('href', '/knowledge-bases/kb_123');
  });

  it('renders empty state when no items', () => {
    render(
      <MemoryRouter initialEntries={['/knowledge-bases/kb_123/upload']}>
        <Routes>
          <Route path="/knowledge-bases/:id/upload" element={<Upload />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/拖拽 PDF 文件/)).toBeInTheDocument();
  });
});
