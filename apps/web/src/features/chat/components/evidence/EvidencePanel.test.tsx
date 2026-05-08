import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EvidencePanel } from '@/features/chat/components/evidence/EvidencePanel';

describe('EvidencePanel', () => {
  it('shows fallback warning and localized error state', () => {
    render(
      <EvidencePanel
        contract={{
          response_type: 'rag',
          answer_mode: 'partial',
          answer: 'answer',
          claims: [],
          citations: [],
          evidence_blocks: [],
          quality: {
            fallback_used: true,
            fallback_reason: 'unsupported_field_type',
          },
          trace_id: 'trace-1',
          run_id: 'run-1',
          retrieval_trace_id: 'trace-1',
          error_state: 'fallback_used',
        }}
        onJumpCitation={vi.fn()}
        onOpenSource={vi.fn()}
        onSaveEvidence={vi.fn()}
      />,
    );

    expect(screen.getByText(/fallback active/i)).toBeInTheDocument();
    expect(screen.getByText('已启用回退检索路径，请结合证据面板审阅回答。')).toBeInTheDocument();
    expect(screen.queryByText(/fallback_used/i)).not.toBeInTheDocument();
  });

  it('suppresses unknown internal error state labels', () => {
    render(
      <EvidencePanel
        contract={{
          response_type: 'rag',
          answer_mode: 'abstain',
          answer: 'answer',
          claims: [],
          citations: [],
          evidence_blocks: [],
          quality: {
            fallback_used: false,
          },
          trace_id: 'trace-2',
          run_id: 'run-2',
          retrieval_trace_id: 'trace-2',
          error_state: 'debug_only_internal_state',
        }}
        onJumpCitation={vi.fn()}
        onOpenSource={vi.fn()}
        onSaveEvidence={vi.fn()}
      />,
    );

    expect(screen.queryByText(/debug_only_internal_state/i)).not.toBeInTheDocument();
  });

  it('normalizes abstain boilerplate inside claim support copy', () => {
    render(
      <EvidencePanel
        contract={{
          response_type: 'rag',
          answer_mode: 'abstain',
          answer: 'Insufficient evidence to answer confidently.',
          claims: [
            {
              claim: 'Insufficient evidence to answer confidently.',
              support_status: 'unsupported',
              supporting_source_chunk_ids: [],
            },
          ],
          citations: [],
          evidence_blocks: [],
          quality: {
            fallback_used: false,
            unsupported_claim_rate: 1,
          },
          trace_id: 'trace-3',
          run_id: 'run-3',
          retrieval_trace_id: 'trace-3',
          error_state: 'abstain',
        }}
        onJumpCitation={vi.fn()}
        onOpenSource={vi.fn()}
        onSaveEvidence={vi.fn()}
      />,
    );

    expect(screen.getByText('当前证据不足以给出可靠回答。')).toBeInTheDocument();
    expect(screen.queryByText('Insufficient evidence to answer confidently.')).not.toBeInTheDocument();
  });
});
