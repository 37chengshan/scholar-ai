import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { KnowledgeReviewPanel } from './KnowledgeReviewPanel';

const mockSearchParams = new URLSearchParams('runId=run-1');

vi.mock('react-router', async () => {
  const actual = await vi.importActual<any>('react-router');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useSearchParams: () => [mockSearchParams, vi.fn()],
  };
});

vi.mock('@/app/contexts/LanguageContext', () => ({
  useLanguage: () => ({ language: 'zh' }),
}));

vi.mock('@/services/kbReviewApi', () => ({
  kbReviewApi: {
    listDrafts: vi.fn(),
    getRunDetail: vi.fn(),
    createDraft: vi.fn(),
    retryDraft: vi.fn(),
    repairClaim: vi.fn(),
  },
}));

import { kbReviewApi } from '@/services/kbReviewApi';

describe('KnowledgeReviewPanel', () => {
  it('renders run trace from runId query even when the draft list is empty', async () => {
    vi.mocked(kbReviewApi.listDrafts).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    vi.mocked(kbReviewApi.getRunDetail).mockResolvedValue({
      id: 'run-1',
      knowledgeBaseId: 'kb-1',
      reviewDraftId: 'draft-missing',
      status: 'completed',
      scope: 'full_kb',
      traceId: 'trace-1',
      errorState: null,
      createdAt: '2026-04-29T00:00:00Z',
      updatedAt: '2026-04-29T00:00:00Z',
      inputPayload: {},
      steps: [
        {
          step_name: 'draft_finalizer',
          status: 'completed',
          metadata: {
            input_schema_name: 'DraftFinalizerInput',
            output_schema_name: 'DraftDoc',
          },
        },
      ],
      toolEvents: [],
      artifacts: [],
      evidence: [],
      recoveryActions: [],
    });

    render(<KnowledgeReviewPanel kbId="kb-1" papers={[]} />);

    await waitFor(() => {
      expect(kbReviewApi.getRunDetail).toHaveBeenCalledWith('run-1');
    });

    expect(screen.getByText('Run Trace')).toBeInTheDocument();
    expect(screen.getByText(/run_id: run-1/i)).toBeInTheDocument();
    expect(screen.getByText(/draft_finalizer/i)).toBeInTheDocument();
    expect(screen.getByText(/对应 draft 不在当前列表中/i)).toBeInTheDocument();
  });
});
