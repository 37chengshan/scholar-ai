import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { KnowledgeWorkspaceShell } from './KnowledgeWorkspaceShell';

const mockNavigate = vi.fn();
const mockSetSearchParams = vi.fn();

vi.mock('react-router', async () => {
  const actual = await vi.importActual<any>('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ pathname: '/knowledge-bases/kb-1', search: '', state: null }),
    useParams: () => ({ id: 'kb-1' }),
    useSearchParams: () => [new URLSearchParams(), mockSetSearchParams],
    Link: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

vi.mock('@/services/kbApi', () => ({
  kbApi: {
    get: vi.fn(),
    listPapers: vi.fn(),
    search: vi.fn(),
  },
}));

vi.mock('@/services/importApi', () => ({
  importApi: {
    list: vi.fn(),
  },
}));

vi.mock('@/utils/apiClient', () => ({
  default: {
    get: vi.fn(),
  },
}));

vi.mock('@/services/kbReviewApi', () => ({
  kbReviewApi: {
    listRuns: vi.fn(),
  },
}));

vi.mock('@/features/kb/components/KnowledgeImportPanel', () => ({
  KnowledgeImportPanel: ({ onJobComplete }: { onJobComplete: () => void }) => (
    <button type="button" onClick={onJobComplete}>
      mock-job-complete
    </button>
  ),
}));

vi.mock('@/features/uploads/components/UploadWorkspace', () => ({
  UploadWorkspace: ({ onQueueComplete }: { onQueueComplete?: () => void | Promise<void> }) => (
    <button type="button" onClick={() => void onQueueComplete?.()}>
      mock-upload-complete
    </button>
  ),
}));

vi.mock('@/app/components/ImportDialog', () => ({
  ImportDialog: ({ onImportComplete }: { onImportComplete: () => void | Promise<void> }) => (
    <button type="button" onClick={() => void onImportComplete()}>
      mock-import-complete
    </button>
  ),
}));

import { kbApi } from '@/services/kbApi';
import { importApi } from '@/services/importApi';
import apiClient from '@/utils/apiClient';
import { kbReviewApi } from '@/services/kbReviewApi';

describe('KnowledgeWorkspaceShell', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(kbApi.get).mockResolvedValue({
      id: 'kb-1',
      userId: 'u-1',
      name: 'Test KB',
      description: 'desc',
      category: '其他',
      paperCount: 1,
      chunkCount: 12,
      entityCount: 0,
      embeddingModel: 'bge-m3',
      parseEngine: 'docling',
      chunkStrategy: 'by-paragraph',
      enableGraph: false,
      enableImrad: true,
      enableChartUnderstanding: false,
      enableMultimodalSearch: false,
      enableComparison: false,
      createdAt: '2026-01-01T00:00:00Z',
      updatedAt: '2026-01-01T00:00:00Z',
    } as any);

    vi.mocked(kbApi.listPapers).mockResolvedValue({
      papers: [
        {
          id: 'paper-1',
          title: 'Paper One',
          authors: ['A'],
          year: 2024,
          venue: 'NeurIPS',
          status: 'completed',
          chunkCount: 3,
          entityCount: 0,
          createdAt: '2026-01-01T00:00:00Z',
          updatedAt: '2026-01-01T00:00:00Z',
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    } as any);

    vi.mocked(kbApi.search).mockResolvedValue({
      results: [
        {
          id: 'hit-1',
          paperId: 'paper-1',
          paperTitle: 'Paper One',
          content: 'Snippet',
          page: 2,
          score: 0.9,
        },
      ],
      total: 1,
    } as any);

    vi.mocked(importApi.list).mockResolvedValue({ success: true, data: { jobs: [] } } as any);
    vi.mocked(kbReviewApi.listRuns).mockResolvedValue({
      items: [{ id: 'run-1', status: 'completed', updatedAt: '2026-01-01T00:00:00Z' }],
      total: 1,
      limit: 50,
      offset: 0,
    } as any);
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] } as any);
  });

  it('renders papers panel by default', async () => {
    render(<KnowledgeWorkspaceShell />);

    await waitFor(() => {
      expect(screen.getByText('Paper One')).toBeInTheDocument();
    });

    expect(screen.getByText('Readiness')).toBeInTheDocument();
    expect(screen.getByText('Evidence is ready to inspect')).toBeInTheDocument();
    expect(screen.getByText('Review and chat are ready to continue')).toBeInTheDocument();
  });

  it('switches to runs panel and shows run history', async () => {
    const user = userEvent.setup();
    render(<KnowledgeWorkspaceShell />);

    await waitFor(() => {
      expect(screen.getByText('Paper One')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: /Run 历史/i }));
    expect(screen.getAllByText(/run-1/i).length).toBeGreaterThan(0);
  });

  it('opens review tab with runId when a KB run is clicked', async () => {
    const user = userEvent.setup();
    render(<KnowledgeWorkspaceShell />);

    await waitFor(() => {
      expect(screen.getByText('Paper One')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: /Run 历史/i }));
    await user.click(screen.getByRole('button', { name: /Run run-1/i }));

    expect(mockNavigate).toHaveBeenCalledWith('/knowledge-bases/kb-1?tab=review&runId=run-1');
  });

  it('only refreshes import jobs when upload queue submission completes', async () => {
    const user = userEvent.setup();
    vi.mocked(importApi.list).mockResolvedValueOnce({
      success: true,
      data: {
        jobs: [],
        total: 0,
        limit: 50,
        offset: 0,
      },
    } as any);
    vi.mocked(importApi.list).mockResolvedValueOnce({
      success: true,
      data: {
        jobs: [
          {
            importJobId: 'job-1',
            knowledgeBaseId: 'kb-1',
            sourceType: 'pdf_url',
            status: 'completed',
            stage: 'completed',
            progress: 100,
            createdAt: '2026-01-01T00:00:00Z',
            updatedAt: '2026-01-01T00:00:00Z',
            completedAt: '2026-01-01T00:00:00Z',
            cancelledAt: null,
            source: {
              rawInput: 'https://example.com/paper.pdf',
              normalizedRef: 'https://example.com/paper.pdf',
              externalIds: {},
            },
            preview: {
              title: 'Imported Paper',
              authors: ['A'],
              year: 2024,
              venue: 'NeurIPS',
            },
            dedupe: {
              status: 'resolved',
              matchedPaperId: null,
              matchType: null,
              decision: null,
            },
            file: {
              storageKey: null,
              sha256: null,
              sizeBytes: null,
            },
            paper: {
              paperId: 'paper-1',
              title: 'Imported Paper',
            },
            task: null,
            error: null,
          },
        ],
        total: 1,
        limit: 50,
        offset: 0,
      },
    } as any);
    render(<KnowledgeWorkspaceShell />);

    await waitFor(() => {
      expect(screen.getByText('Paper One')).toBeInTheDocument();
    });

    expect(vi.mocked(importApi.list)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(kbApi.listPapers)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(kbApi.get)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(kbReviewApi.listRuns)).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('tab', { name: /上传工作台/i }));
    await user.click(screen.getByRole('button', { name: 'mock-upload-complete' }));

    await waitFor(() => {
      expect(vi.mocked(importApi.list)).toHaveBeenCalledTimes(2);
    });

    await waitFor(() => {
      expect(vi.mocked(kbApi.listPapers).mock.calls.length).toBeGreaterThan(1);
      expect(vi.mocked(kbApi.get).mock.calls.length).toBeGreaterThan(1);
      expect(vi.mocked(kbReviewApi.listRuns).mock.calls.length).toBeGreaterThan(1);
    });
  });

  it('only refreshes import jobs when import dialog submission completes', async () => {
    const user = userEvent.setup();
    render(<KnowledgeWorkspaceShell />);

    await waitFor(() => {
      expect(screen.getByText('Paper One')).toBeInTheDocument();
    });

    expect(vi.mocked(importApi.list)).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: 'mock-import-complete' }));

    await waitFor(() => {
      expect(vi.mocked(importApi.list)).toHaveBeenCalledTimes(2);
    });

    expect(vi.mocked(kbApi.listPapers)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(kbApi.get)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(kbReviewApi.listRuns)).toHaveBeenCalledTimes(1);
  });

  it('only refreshes import jobs when import panel reports job completion', async () => {
    const user = userEvent.setup();
    render(<KnowledgeWorkspaceShell />);

    await waitFor(() => {
      expect(screen.getByText('Paper One')).toBeInTheDocument();
    });

    expect(vi.mocked(importApi.list)).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('tab', { name: /导入状态/i }));
    await user.click(screen.getByRole('button', { name: 'mock-job-complete' }));

    await waitFor(() => {
      expect(vi.mocked(importApi.list)).toHaveBeenCalledTimes(2);
    });

    expect(vi.mocked(kbApi.listPapers)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(kbApi.get)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(kbReviewApi.listRuns)).toHaveBeenCalledTimes(1);
  });
});
