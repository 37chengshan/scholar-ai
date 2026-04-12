import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { KnowledgeBaseDetail } from './KnowledgeBaseDetail';

const mockNavigate = vi.fn();
const mockSetSearchParams = vi.fn();

vi.mock('react-router', async () => {
  const actual = await vi.importActual<any>('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: 'kb-1' }),
    useSearchParams: () => [new URLSearchParams(), mockSetSearchParams],
    Link: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

vi.mock('@/services/kbApi', () => ({
  kbApi: {
    get: vi.fn(),
    listPapers: vi.fn(),
    getUploadHistory: vi.fn(),
    search: vi.fn(),
    query: vi.fn(),
  },
}));

vi.mock('@/services/uploadHistoryApi', () => ({
  uploadHistoryApi: {
    delete: vi.fn(),
  },
}));

import { kbApi } from '@/services/kbApi';

const mockKb = {
  id: 'kb-1',
  userId: 'user-1',
  name: 'Test KB',
  description: 'desc',
  category: '其他',
  paperCount: 2,
  chunkCount: 10,
  entityCount: 0,
  embeddingModel: 'bge-m3',
  parseEngine: 'docling',
  chunkStrategy: 'by-paragraph',
  enableGraph: false,
  enableImrad: true,
  enableChartUnderstanding: false,
  enableMultimodalSearch: false,
  enableComparison: false,
  createdAt: '2026-04-12T00:00:00Z',
  updatedAt: '2026-04-12T00:00:00Z',
};

const mockPapers = [
  {
    id: 'paper-1',
    title: 'Paper One',
    authors: ['Author A'],
    year: 2024,
    venue: 'NeurIPS',
    status: 'completed',
    chunkCount: 4,
    entityCount: 0,
    createdAt: '2026-04-12T00:00:00Z',
    updatedAt: '2026-04-12T00:00:00Z',
  },
];

describe('KnowledgeBaseDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(kbApi.get).mockResolvedValue({ success: true, data: mockKb } as any);
    vi.mocked(kbApi.listPapers).mockResolvedValue({
      success: true,
      data: { papers: mockPapers, total: 1, limit: 20, offset: 0 },
    } as any);
    vi.mocked(kbApi.getUploadHistory).mockResolvedValue({
      success: true,
      data: { records: [], total: 0, limit: 20, offset: 0 },
    } as any);
    vi.mocked(kbApi.search).mockResolvedValue({ success: true, data: { results: [], total: 0 } } as any);
    vi.mocked(kbApi.query).mockResolvedValue({ success: true, data: { answer: 'ok', citations: [], confidence: 1 } } as any);
  });

  it('defaults to papers-first hierarchy and renders paper list', async () => {
    render(<KnowledgeBaseDetail />);

    await waitFor(() => {
      expect(screen.getByText('Paper One')).toBeInTheDocument();
    });

    expect(screen.getByRole('tab', { name: /论文列表/i })).toHaveAttribute('data-state', 'active');
    expect(screen.getByRole('button', { name: /阅读/i })).toBeInTheDocument();
  });

  it('shows upload history tab content when selected', async () => {
    const user = userEvent.setup();
    render(<KnowledgeBaseDetail />);

    await waitFor(() => {
      expect(screen.getByText('Paper One')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: /上传记录/i }));
    expect(screen.getByText(/知识库上传记录/i)).toBeInTheDocument();
  });

  it('renders KB retrieval results from the API', async () => {
    const user = userEvent.setup();
    vi.mocked(kbApi.search).mockResolvedValue({
      success: true,
      data: {
        results: [
          {
            id: 'chunk-1',
            paperId: 'paper-1',
            paperTitle: 'Paper One',
            content: 'Important result snippet',
            page: 3,
            score: 0.91,
          },
        ],
        total: 1,
      },
    } as any);

    render(<KnowledgeBaseDetail />);

    await waitFor(() => {
      expect(screen.getByText('Paper One')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: /知识库检索/i }));
    await user.type(screen.getByPlaceholderText(/输入您的问题/i), 'test query');
    await user.click(screen.getByRole('button', { name: /^检索$/i }));

    await waitFor(() => {
      expect(screen.getByText(/Important result snippet/i)).toBeInTheDocument();
      expect(screen.getByText(/Paper One/i)).toBeInTheDocument();
    });
  });

  it('renders KB QA answers from the API', async () => {
    const user = userEvent.setup();
    vi.mocked(kbApi.query).mockResolvedValue({
      success: true,
      data: {
        answer: 'Knowledge-base answer',
        citations: [],
        confidence: 0.9,
      },
    } as any);

    render(<KnowledgeBaseDetail />);

    await waitFor(() => {
      expect(screen.getByText('Paper One')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: /问答/i }));
    await user.type(
      screen.getByPlaceholderText(/Ask a question about your knowledge base/i),
      'what is this paper about?'
    );
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText(/Knowledge-base answer/i)).toBeInTheDocument();
    });
  });

  it('uses citation paper_id fallback for QA source navigation', async () => {
    const user = userEvent.setup();
    vi.mocked(kbApi.query).mockResolvedValue({
      success: true,
      data: {
        answer: 'Answer with citation',
        citations: [
          {
            paper_id: 'paper-1',
            paperTitle: 'Paper One',
            page: 2,
          },
        ],
        confidence: 0.9,
      },
    } as any);

    render(<KnowledgeBaseDetail />);

    await waitFor(() => {
      expect(screen.getByText('Paper One')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: /问答/i }));
    await user.type(
      screen.getByPlaceholderText(/Ask a question about your knowledge base/i),
      'show me citation'
    );
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText(/Answer with citation/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Paper One/i).length).toBeGreaterThan(0);
    });

    await user.click(screen.getByText('Paper One', { selector: 'span' }));
    expect(mockNavigate).toHaveBeenCalledWith('/read/paper-1?page=2');
  });
});
