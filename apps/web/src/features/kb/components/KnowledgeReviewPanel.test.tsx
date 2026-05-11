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

    expect(screen.getByText('运行轨迹')).toBeInTheDocument();
    expect(screen.getByText(/运行 ID\s*:\s*run-1/i)).toBeInTheDocument();
    expect(screen.getByText(/草稿生成/i)).toBeInTheDocument();
    expect(screen.getByText(/对应草稿不在当前列表中/i)).toBeInTheDocument();
  });

  it('renders known limitations from the selected draft', async () => {
    vi.mocked(kbReviewApi.listDrafts).mockResolvedValue({
      items: [
        {
          id: 'draft-1',
          knowledgeBaseId: 'kb-1',
          title: 'Related Work Draft',
          status: 'partial',
          sourcePaperIds: ['paper-1'],
          outlineDoc: {
            research_question: 'q',
            themes: [],
            sections: [],
          },
          draftDoc: { sections: [] },
          quality: {
            citation_coverage: 0.6,
            unsupported_paragraph_rate: 0.4,
            graph_assist_used: false,
            fallback_used: false,
          },
          knownLimitations: ['部分段落仍需要更强证据支撑'],
          traceId: 'trace-1',
          runId: 'run-1',
          errorState: 'partial_draft',
          createdAt: '2026-04-29T00:00:00Z',
          updatedAt: '2026-04-29T00:00:00Z',
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });
    vi.mocked(kbReviewApi.getRunDetail).mockResolvedValue({
      id: 'run-1',
      knowledgeBaseId: 'kb-1',
      reviewDraftId: 'draft-1',
      status: 'completed',
      scope: 'full_kb',
      traceId: 'trace-1',
      errorState: null,
      createdAt: '2026-04-29T00:00:00Z',
      updatedAt: '2026-04-29T00:00:00Z',
      inputPayload: {},
      steps: [],
      toolEvents: [],
      artifacts: [],
      evidence: [],
      recoveryActions: [],
    });

    render(<KnowledgeReviewPanel kbId="kb-1" papers={[]} />);

    await waitFor(() => {
      expect(screen.getByText(/已知限制/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/部分段落仍需要更强证据支撑/i)).toBeInTheDocument();
  });

  it('renders artifact bundle links when run artifacts provide urls', async () => {
    vi.mocked(kbReviewApi.listDrafts).mockResolvedValue({
      items: [
        {
          id: 'draft-1',
          knowledgeBaseId: 'kb-1',
          title: 'Related Work Draft',
          status: 'completed',
          sourcePaperIds: ['paper-1', 'paper-2'],
          outlineDoc: {
            research_question: 'q',
            themes: [],
            sections: [],
          },
          draftDoc: { sections: [] },
          quality: {
            citation_coverage: 1,
            unsupported_paragraph_rate: 0,
            graph_assist_used: false,
            fallback_used: false,
          },
          knownLimitations: [],
          traceId: 'trace-1',
          runId: 'run-1',
          errorState: null,
          createdAt: '2026-04-29T00:00:00Z',
          updatedAt: '2026-04-29T00:00:00Z',
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });
    vi.mocked(kbReviewApi.getRunDetail).mockResolvedValue({
      id: 'run-1',
      knowledgeBaseId: 'kb-1',
      reviewDraftId: 'draft-1',
      status: 'completed',
      scope: 'full_kb',
      traceId: 'trace-1',
      errorState: null,
      createdAt: '2026-04-29T00:00:00Z',
      updatedAt: '2026-04-29T00:00:00Z',
      inputPayload: {},
      steps: [],
      toolEvents: [],
      artifacts: [
        {
          artifact_id: 'run-1:evidence_note',
          run_id: 'run-1',
          type: 'evidence_note',
          title: 'Evidence Note',
          url: '/notes?paperId=paper-1&sourceChunkId=chunk-1',
          metadata: {},
        },
        {
          artifact_id: 'run-1:compare_matrix',
          run_id: 'run-1',
          type: 'compare_matrix',
          title: 'Compare Matrix',
          url: '/compare?paper_ids=paper-1,paper-2',
          metadata: {},
        },
      ],
      evidence: [],
      recoveryActions: [],
    });

    render(<KnowledgeReviewPanel kbId="kb-1" papers={[]} />);

    await waitFor(() => {
      expect(screen.getByText(/产物包/i)).toBeInTheDocument();
    });

    expect(screen.getByText('Evidence Note')).toBeInTheDocument();
    expect(screen.getByText('Compare Matrix')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '打开' })).toHaveLength(2);
  });
});
