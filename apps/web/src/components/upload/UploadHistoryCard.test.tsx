import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { UploadHistoryCard } from './UploadHistoryCard';

const baseRecord = {
  id: 'upload-1',
  userId: 'user-1',
  filename: 'paper.pdf',
  status: 'COMPLETED',
  chunksCount: 10,
  llmTokens: 100,
  pageCount: 5,
  imageCount: 0,
  tableCount: 0,
  errorMessage: null,
  processingTime: 1200,
  progress: 100,
  processingStatus: 'completed',
  completedAt: '2026-04-12T00:00:00Z',
  paperId: 'paper-1',
  createdAt: '2026-04-12T00:00:00Z',
  updatedAt: '2026-04-12T00:00:00Z',
  paper: {
    id: 'paper-1',
    title: 'Paper One',
    filename: 'paper.pdf',
  },
};

describe('UploadHistoryCard', () => {
  it('renders progress information when provided', () => {
    render(<UploadHistoryCard record={baseRecord} onDelete={() => {}} />);
    expect(screen.getByText(/paper.pdf/i)).toBeInTheDocument();
  });

  it('renders failed status styling for failed uploads', () => {
    render(
      <UploadHistoryCard
        record={{ ...baseRecord, status: 'FAILED', progress: 0, errorMessage: 'boom' }}
        onDelete={() => {}}
      />
    );
    expect(screen.getByText(/失败|FAILED/i)).toBeInTheDocument();
  });
});
