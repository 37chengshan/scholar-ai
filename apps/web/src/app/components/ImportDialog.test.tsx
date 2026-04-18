import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ImportDialog } from './ImportDialog';

vi.mock('react-router', async () => {
  const actual = await vi.importActual<any>('react-router');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

vi.mock('@/features/uploads/components/UploadWorkspace', () => ({
  UploadWorkspace: () => <div data-testid="upload-workspace">upload workspace</div>,
}));

vi.mock('@/services/importApi', () => ({
  importApi: {
    resolve: vi.fn(),
    create: vi.fn(),
  },
}));

describe('ImportDialog', () => {
  it('renders upload workspace for local tab', () => {
    render(
      <ImportDialog
        open={true}
        onOpenChange={vi.fn()}
        knowledgeBaseId="kb_1"
        knowledgeBaseName="KB"
      />
    );

    expect(screen.getByTestId('upload-workspace')).toBeInTheDocument();
  });
});
