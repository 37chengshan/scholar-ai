import type { AnswerContractPayload, CitationItem, EvidenceBlock } from '@/features/chat/components/workspaceTypes';
import { AnswerModeBadge } from './AnswerModeBadge';
import { ClaimSupportList } from './ClaimSupportList';
import { CitationInline } from './CitationInline';
import { EvidenceBlockCard } from './EvidenceBlockCard';
import { RetrievalQualityBar } from './RetrievalQualityBar';
import { FallbackWarning } from './FallbackWarning';

interface EvidencePanelProps {
  contract: AnswerContractPayload;
  onJumpCitation: (citation: CitationItem) => void;
  onOpenSource: (sourceChunkId: string, paperId?: string, pageNum?: number | null) => void;
  onSaveEvidence: (claim: string, block: EvidenceBlock) => void;
}

export function EvidencePanel({ contract, onJumpCitation, onOpenSource, onSaveEvidence }: EvidencePanelProps) {
  const leadClaim = contract.claims[0]?.claim || contract.answer || 'evidence';

  return (
    <section className="mt-3 rounded-xl border border-border/70 bg-muted/10 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="text-xs font-semibold tracking-[0.08em] text-muted-foreground">Evidence</div>
        <AnswerModeBadge mode={contract.answer_mode} />
      </div>

      <FallbackWarning visible={Boolean(contract.quality.fallback_used)} reason={contract.quality.fallback_reason} />
      <RetrievalQualityBar quality={contract.quality} />
      <ClaimSupportList claims={contract.claims} />
      <CitationInline citations={contract.citations} onJump={onJumpCitation} />

      <div className="mt-2 space-y-2">
        {contract.evidence_blocks.slice(0, 4).map((block) => (
          <EvidenceBlockCard
            key={`${block.paper_id}-${block.source_chunk_id}`}
            block={block}
            onOpenSource={onOpenSource}
            onSave={(payload) => onSaveEvidence(leadClaim, payload)}
          />
        ))}
      </div>

      {contract.trace_id || contract.retrieval_trace_id ? (
        <div className="mt-2 text-[11px] text-muted-foreground">
          trace: {contract.trace_id || contract.retrieval_trace_id}
          {contract.run_id ? ` · run: ${contract.run_id}` : ''}
        </div>
      ) : null}
      {contract.error_state ? (
        <div className="mt-1 text-[11px] text-rose-700">state: {contract.error_state}</div>
      ) : null}
    </section>
  );
}
