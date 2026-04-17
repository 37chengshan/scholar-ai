import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { UploadWorkspace } from './UploadWorkspace';

const startUploadQueue = vi.fn().mockResolvedValue({ succeeded: 1, failed: 0 });

vi.mock('@/features/uploads/hooks/useUploadWorkspace', () => ({
  useUploadWorkspace: () => ({
    items: [
      {
        id: 'item_1',
        file: new File([new Uint8Array([1, 2])], 'paper.pdf', { type: 'application/pdf' }),
        fileName: 'paper.pdf',
        sizeBytes: 2,
        progress: 0,
        status: 'pending',
      },
    ],
    isUploading: false,
    pendingCount: 1,
    addFiles: vi.fn(),
    removeItem: vi.fn(),
    startUploadQueue,
  }),
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
  },
}));

describe('UploadWorkspace', () => {
  it('triggers upload queue action', async () => {
    const user = userEvent.setup();
    render(<UploadWorkspace knowledgeBaseId="kb_1" />);

    await user.click(screen.getByRole('button', { name: /开始上传/i }));
    expect(startUploadQueue).toHaveBeenCalledTimes(1);
  });
});
