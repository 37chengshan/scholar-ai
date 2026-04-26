import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EvidencePanel } from '@/features/chat/components/evidence/EvidencePanel';

describe('EvidencePanel', () => {
  it('shows fallback warning and error state', () => {
    render(
      <EvidencePanel
        contract={{
          answer_mode: 'partial',
          answer: 'answer',
          claims: [],
          citations: [],
          evidence_blocks: [],
          quality: {
            fallback_used: true,
            fallback_reason: 'unsupported_field_type',
          },
          retrieval_trace_id: 'trace-1',
          error_state: 'fallback_used',
        }}
        onJumpCitation={vi.fn()}
        onOpenSource={vi.fn()}
        onSaveEvidence={vi.fn()}
      />,
    );

    expect(screen.getByText(/fallback active/i)).toBeInTheDocument();
    expect(screen.getByText(/trace-1/i)).toBeInTheDocument();
    expect(screen.getByText(/fallback_used/i)).toBeInTheDocument();
  });
});
