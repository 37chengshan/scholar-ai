/**
 * Tests for Phase 4 Compare components and contract types.
 *
 * Coverage:
 * - CompareCard renders matrix rows + dimensions
 * - Cell evidence jump uses citation_jump_url
 * - not_enough_evidence cells render as "–"
 * - Compare page default dimensions are all rendered
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import type { CompareMatrixDto } from '@scholar-ai/types';
import { CompareCard } from '@/features/chat/components/CompareCard';
import type { AnswerContractPayload } from '@/features/chat/components/workspaceTypes';
import { ALLOWED_COMPARE_DIMENSIONS, DIMENSION_LABELS } from '@/services/compareApi';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockJumpToSource = vi.fn();
const mockNavigate = vi.fn();

vi.mock('@/features/chat/hooks/useEvidenceNavigation', () => ({
  useEvidenceNavigation: () => ({ jumpToSource: mockJumpToSource }),
}));

vi.mock('react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router')>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeMatrix(overrides: Partial<CompareMatrixDto> = {}): CompareMatrixDto {
  return {
    paper_ids: ['p-001', 'p-002'],
    dimensions: [
      { id: 'method', label: 'Method' },
      { id: 'results', label: 'Results' },
    ],
    rows: [
      {
        paper_id: 'p-001',
        title: 'Paper Alpha',
        year: 2021,
        cells: [
          {
            dimension_id: 'method',
            content: 'Transformer-based approach',
            support_status: 'supported',
            evidence_blocks: [
              {
                evidence_id: 'eb-001',
                source_type: 'paper',
                paper_id: 'p-001',
                source_chunk_id: 'chunk-001',
                page_num: 3,
                content_type: 'text',
                text: 'We use a transformer encoder',
                citation_jump_url: '/read/p-001?chunk=chunk-001',
              },
            ],
          },
          {
            dimension_id: 'results',
            content: '',
            support_status: 'not_enough_evidence',
            evidence_blocks: [],
          },
        ],
      },
      {
        paper_id: 'p-002',
        title: 'Paper Beta',
        year: 2022,
        cells: [
          {
            dimension_id: 'method',
            content: 'CNN architecture',
            support_status: 'partially_supported',
            evidence_blocks: [
              {
                evidence_id: 'eb-002',
                source_type: 'paper',
                paper_id: 'p-002',
                source_chunk_id: 'chunk-002',
                page_num: 5,
                content_type: 'text',
                text: 'A CNN was used',
                citation_jump_url: '/read/p-002?chunk=chunk-002',
              },
            ],
          },
          {
            dimension_id: 'results',
            content: '95% accuracy',
            support_status: 'supported',
            evidence_blocks: [
              {
                evidence_id: 'eb-003',
                source_type: 'paper',
                paper_id: 'p-002',
                source_chunk_id: 'chunk-003',
                page_num: 8,
                content_type: 'text',
                text: 'We achieved 95% accuracy',
                citation_jump_url: '/read/p-002?chunk=chunk-003',
              },
            ],
          },
        ],
      },
    ],
    summary: 'Two papers compared.',
    cross_paper_insights: [
      {
        claim: 'Both papers address image classification',
        supporting_paper_ids: ['p-001', 'p-002'],
        evidence_blocks: [],
      },
    ],
    ...overrides,
  };
}

function makeContract(matrix: CompareMatrixDto): AnswerContractPayload {
  return {
    response_type: 'compare',
    answer_mode: 'full',
    answer: '',
    claims: [],
    citations: [],
    evidence_blocks: [],
    quality: {},
    trace_id: 'trace-1',
    run_id: 'run-1',
    compare_matrix: matrix,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('CompareCard', () => {
  beforeEach(() => {
    mockJumpToSource.mockReset();
    mockNavigate.mockReset();
  });

  it('renders paper titles as rows', () => {
    render(
      <MemoryRouter>
        <CompareCard contract={makeContract(makeMatrix())} isZh={false} />
      </MemoryRouter>,
    );
    expect(screen.getByText('Paper Alpha')).toBeTruthy();
    expect(screen.getByText('Paper Beta')).toBeTruthy();
  });

  it('renders dimension headers', () => {
    render(
      <MemoryRouter>
        <CompareCard contract={makeContract(makeMatrix())} isZh={false} />
      </MemoryRouter>,
    );
    expect(screen.getByText('Method')).toBeTruthy();
    expect(screen.getByText('Results')).toBeTruthy();
  });

  it('renders not_enough_evidence cells as "–"', () => {
    render(
      <MemoryRouter>
        <CompareCard contract={makeContract(makeMatrix())} isZh={false} />
      </MemoryRouter>,
    );
    // Paper Alpha's Results cell is not_enough_evidence → should show "–"
    const dashes = screen.getAllByText('–');
    expect(dashes.length).toBeGreaterThan(0);
  });

  it('calls jumpToSource with canonical evidence identifiers when page jump is clicked', () => {
    render(
      <MemoryRouter>
        <CompareCard contract={makeContract(makeMatrix())} isZh={false} />
      </MemoryRouter>,
    );
    // "p.3" is the jump button for Paper Alpha / Method cell
    const jumpBtn = screen.getByText('p.3');
    fireEvent.click(jumpBtn);
    expect(mockJumpToSource).toHaveBeenCalledWith(
      'chunk-001',
      'p-001',
      3,
    );
  });

  it('renders cross-paper insight claim', () => {
    render(
      <MemoryRouter>
        <CompareCard contract={makeContract(makeMatrix())} isZh={false} />
      </MemoryRouter>,
    );
    expect(screen.getByText('Both papers address image classification')).toBeTruthy();
  });

  it('"View full table" button navigates to /compare with paper_ids param', () => {
    render(
      <MemoryRouter>
        <CompareCard contract={makeContract(makeMatrix())} isZh={false} />
      </MemoryRouter>,
    );
    const btn = screen.getByText(/View full table/i);
    fireEvent.click(btn);
    expect(mockNavigate).toHaveBeenCalledWith('/compare?paper_ids=p-001,p-002');
  });
});

describe('compareApi dimension catalogue', () => {
  it('has 7 default allowed dimensions', () => {
    expect(ALLOWED_COMPARE_DIMENSIONS.length).toBe(7);
  });

  it('all dimension IDs have labels', () => {
    for (const dimId of ALLOWED_COMPARE_DIMENSIONS) {
      expect(DIMENSION_LABELS[dimId]).toBeTruthy();
    }
  });
});
