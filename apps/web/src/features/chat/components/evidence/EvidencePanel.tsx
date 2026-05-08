import type { AnswerContractPayload, CitationItem, EvidenceBlock } from '@/features/chat/components/workspaceTypes';
import { AnswerModeBadge } from './AnswerModeBadge';
import { ClaimSupportList } from './ClaimSupportList';
import { CitationInline } from './CitationInline';
import { EvidenceBlockCard } from './EvidenceBlockCard';
import { RetrievalQualityBar } from './RetrievalQualityBar';
import { FallbackWarning } from './FallbackWarning';
import { useLanguage } from '@/app/contexts/LanguageContext';
import { resolveAnswerErrorStateLabel } from '@/features/chat/lib/answerCopy';

interface EvidencePanelProps {
  contract: AnswerContractPayload;
  onJumpCitation: (citation: CitationItem) => void;
  onOpenSource: (sourceChunkId: string, paperId?: string, pageNum?: number | null) => void;
  onSaveEvidence: (claim: string, block: EvidenceBlock) => void;
}

export function EvidencePanel({ contract, onJumpCitation, onOpenSource, onSaveEvidence }: EvidencePanelProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const leadClaim = contract.claims[0]?.claim || contract.answer || 'evidence';
  const errorStateLabel = resolveAnswerErrorStateLabel(contract.error_state, isZh);

  return (
    <section className="mt-3 rounded-xl border border-border/70 bg-muted/10 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="text-xs font-semibold tracking-[0.08em] text-muted-foreground">
          {isZh ? '证据依据' : 'Evidence basis'}
        </div>
        <AnswerModeBadge mode={contract.answer_mode} />
      </div>

      <FallbackWarning visible={Boolean(contract.quality.fallback_used)} reason={contract.quality.fallback_reason} />
      <RetrievalQualityBar quality={contract.quality} />
      <ClaimSupportList claims={contract.claims} answerMode={contract.answer_mode} />
      <CitationInline citations={contract.citations} onJump={onJumpCitation} />

      <div className="mt-2 space-y-2">
        {contract.evidence_blocks.slice(0, 4).map((block) => (
          <EvidenceBlockCard
            key={block.evidence_id || `${block.paper_id}-${block.source_chunk_id}`}
            block={block}
            onOpenSource={onOpenSource}
            onSave={(payload) => onSaveEvidence(leadClaim, payload)}
          />
        ))}
      </div>

      {errorStateLabel ? <div className="mt-1 text-[11px] text-rose-700">{errorStateLabel}</div> : null}
    </section>
  );
}
