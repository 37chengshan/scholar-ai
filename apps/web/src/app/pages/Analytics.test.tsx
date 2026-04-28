import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { Analytics } from '@/app/pages/Analytics';
import type { EvaluationOverview, BenchmarkRunDetail } from '@scholar-ai/types';

// ─── Mock heavy external deps ─────────────────────────────────────────────────

vi.mock('recharts', () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('motion/react', () => ({
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
  },
}));

vi.mock('@/app/contexts/LanguageContext', () => ({
  useLanguage: () => ({ language: 'en' }),
}));

vi.mock('@/app/components/ui/button', () => ({
  Button: ({ children, onClick, disabled }: { children: React.ReactNode; onClick?: () => void; disabled?: boolean }) => (
    <button onClick={onClick} disabled={disabled}>{children}</button>
  ),
}));

// ─── Mock evalApi ─────────────────────────────────────────────────────────────

vi.mock('@/services/evalApi', () => ({
  evalApi: {
    getOverview: vi.fn(),
    getRunDetail: vi.fn(),
    getDiff: vi.fn(),
  },
}));

import { evalApi } from '@/services/evalApi';

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const MOCK_METRICS = {
  retrieval_hit_rate: 0.891,
  top_k_recall: { recall_at_5: 0.874, recall_at_10: 0.923 },
  rerank_gain: 0.042,
  citation_jump_valid_rate: 0.943,
  answer_supported_rate: 0.871,
  groundedness: 0.834,
  abstain_precision: 0.917,
  fallback_used_count: 5,
  latency_p50: 1.23,
  latency_p95: 4.56,
  cost_per_answer: 0.0012,
  overall_verdict: 'PASS' as const,
  gate_failures: [] as string[],
};

const MOCK_OVERVIEW: EvaluationOverview = {
  latest_offline_gate: {
    run_id: 'run_phase6_baseline_001',
    verdict: 'PASS',
    gate_failures: [],
    metrics: MOCK_METRICS,
  },
  run_count: 1,
  offline_count: 1,
  online_count: 0,
  recent_runs: [
    {
      run_id: 'run_phase6_baseline_001',
      git_sha: 'abc1234',
      dataset_version: 'phase6-v1',
      mode: 'offline',
      reranker: 'on',
      baseline_for: 'phase6',
      overall_verdict: 'PASS',
      created_at: '2026-04-28T00:00:00Z',
    },
  ],
};

const MOCK_DETAIL: BenchmarkRunDetail = {
  run_id: 'run_phase6_baseline_001',
  meta: {
    run_id: 'run_phase6_baseline_001',
    git_sha: 'abc1234',
    dataset_version: 'phase6-v1',
    query_count: 128,
    mode: 'offline',
    reranker: 'on',
    overall_verdict: 'PASS',
    created_at: '2026-04-28T00:00:00Z',
    family_counts: {},
  },
  metrics: MOCK_METRICS,
  by_family: {
    retrieval: {
      rag_basics: { recall_at_5: 0.90, recall_at_10: 0.94 },
    },
    answer_quality: {
      rag_basics: { answer_supported_rate: 0.88, groundedness: 0.80 },
    },
  },
  citation_jump_detail: {
    total_checked: 312,
    valid: 294,
    invalid: 18,
    invalid_reasons: {},
  },
};

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('Analytics page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading spinner on mount', () => {
    vi.mocked(evalApi.getOverview).mockReturnValue(new Promise(() => {}));
    render(<Analytics />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('shows empty state when no latest_offline_gate', async () => {
    vi.mocked(evalApi.getOverview).mockResolvedValue({
      ...MOCK_OVERVIEW,
      latest_offline_gate: null,
    } as EvaluationOverview);

    render(<Analytics />);

    await waitFor(() => {
      expect(
        screen.getByText(/No eval data yet/i),
      ).toBeInTheDocument();
    });
  });

  it('shows error state on fetch failure', async () => {
    vi.mocked(evalApi.getOverview).mockRejectedValue(new Error('network fail'));

    render(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Load failed. Please retry.')).toBeInTheDocument();
    });
  });

  it('renders gate verdict and metric cards when data is loaded', async () => {
    vi.mocked(evalApi.getOverview).mockResolvedValue(MOCK_OVERVIEW);
    vi.mocked(evalApi.getRunDetail).mockResolvedValue(MOCK_DETAIL);

    render(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Evaluation Dashboard')).toBeInTheDocument();
    });

    // Gate status card
    expect(screen.getByText('Gate Status')).toBeInTheDocument();
    expect(screen.getAllByText('PASS').length).toBeGreaterThan(0);

    // Hit Rate card
    expect(screen.getByText('Hit Rate')).toBeInTheDocument();

    // Latency card
    expect(screen.getAllByText('Latency P95').length).toBeGreaterThan(0);
  });

  it('renders run list with correct mode badge', async () => {
    vi.mocked(evalApi.getOverview).mockResolvedValue(MOCK_OVERVIEW);
    vi.mocked(evalApi.getRunDetail).mockResolvedValue(MOCK_DETAIL);

    render(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Recent Runs (1)')).toBeInTheDocument();
    });

    // mode badge
    expect(screen.getAllByText('offline').length).toBeGreaterThan(0);
  });

  it('calls getRunDetail when run row is clicked', async () => {
    vi.mocked(evalApi.getOverview).mockResolvedValue(MOCK_OVERVIEW);
    vi.mocked(evalApi.getRunDetail).mockResolvedValue(MOCK_DETAIL);
    const user = userEvent.setup();

    render(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Recent Runs (1)')).toBeInTheDocument();
    });

    // find the run row by its truncated ID (last 12 chars)
    const runIdSlice = 'run_phase6_baseline_001'.slice(-12);
    const row = screen.getByText(runIdSlice);
    await user.click(row);

    // getRunDetail should have been called (initial load + row click)
    expect(vi.mocked(evalApi.getRunDetail)).toHaveBeenCalledWith('run_phase6_baseline_001');
  });

  it('mode filter buttons toggle visibility', async () => {
    vi.mocked(evalApi.getOverview).mockResolvedValue(MOCK_OVERVIEW);
    vi.mocked(evalApi.getRunDetail).mockResolvedValue(MOCK_DETAIL);
    const user = userEvent.setup();

    render(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Recent Runs (1)')).toBeInTheDocument();
    });

    // Switch to 'online' filter — no online runs, should show 'No data'
    const onlineBtn = screen.getByRole('button', { name: /^online$/i });
    await user.click(onlineBtn);

    expect(screen.getByText('No data')).toBeInTheDocument();
  });

  it('render detail section shows metric rows', async () => {
    vi.mocked(evalApi.getOverview).mockResolvedValue(MOCK_OVERVIEW);
    vi.mocked(evalApi.getRunDetail).mockResolvedValue(MOCK_DETAIL);

    render(<Analytics />);

    await waitFor(() => {
      expect(screen.getByText('Run Detail')).toBeInTheDocument();
    });

    // Detail table should show metric labels
    expect(screen.getByText('Retrieval Hit Rate')).toBeInTheDocument();
    expect(screen.getByText('Groundedness')).toBeInTheDocument();
  });
});
