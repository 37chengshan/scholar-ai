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
    search: vi.fn(),
  },
}));

vi.mock('@/services/importApi', () => ({
  importApi: {
    list: vi.fn(),
  },
}));

import { kbApi } from '@/services/kbApi';
import { importApi } from '@/services/importApi';

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
    vi.mocked(kbApi.get).mockResolvedValue(mockKb as any);
    vi.mocked(kbApi.listPapers).mockResolvedValue({
      papers: mockPapers,
      total: 1,
      limit: 20,
      offset: 0,
    } as any);
    vi.mocked(importApi.list).mockResolvedValue({
      success: true,
      data: {
        jobs: [],
      },
    } as any);
    vi.mocked(kbApi.search).mockResolvedValue({ results: [], total: 0 } as any);
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

    await user.click(screen.getByRole('tab', { name: /导入状态/i }));
    expect(screen.getByText(/论文导入与处理记录/i)).toBeInTheDocument();
  });

  it('renders KB retrieval results from the API', async () => {
    const user = userEvent.setup();
    vi.mocked(kbApi.search).mockResolvedValue({
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

  it('renders unified chat entry in chat tab', async () => {
    const user = userEvent.setup();

    render(<KnowledgeBaseDetail />);

    await waitFor(() => {
      expect(screen.getByText('Paper One')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: /问答/i }));
    expect(screen.getByText(/当前知识库问答已统一到 Chat 页面/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /进入 Chat（全知识库作用域）/i })).toBeInTheDocument();
  });

  it('navigates to chat page from unified chat entry', async () => {
    const user = userEvent.setup();

    render(<KnowledgeBaseDetail />);

    await waitFor(() => {
      expect(screen.getByText('Paper One')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: /问答/i }));
    await user.click(screen.getByRole('button', { name: /进入 Chat（全知识库作用域）/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/chat?kbId=kb-1');
  });
});
