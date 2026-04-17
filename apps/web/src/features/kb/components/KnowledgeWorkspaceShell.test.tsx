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

import { kbApi } from '@/services/kbApi';
import { importApi } from '@/services/importApi';
import apiClient from '@/utils/apiClient';

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
    vi.mocked(apiClient.get).mockResolvedValue({
      data: [{ id: 'session-1', title: 'Run A', updatedAt: '2026-01-01T00:00:00Z' }],
    } as any);
  });

  it('renders papers panel by default', async () => {
    render(<KnowledgeWorkspaceShell />);

    await waitFor(() => {
      expect(screen.getByText('Paper One')).toBeInTheDocument();
    });
  });

  it('switches to runs panel and shows run history', async () => {
    const user = userEvent.setup();
    render(<KnowledgeWorkspaceShell />);

    await waitFor(() => {
      expect(screen.getByText('Paper One')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: /Run 历史/i }));
    expect(screen.getByText('Run A')).toBeInTheDocument();
  });
});
