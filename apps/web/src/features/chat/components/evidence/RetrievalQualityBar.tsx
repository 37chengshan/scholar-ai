import type { AnswerQuality } from '@/features/chat/components/workspaceTypes';

interface RetrievalQualityBarProps {
  quality: AnswerQuality;
}

function pct(value?: number): string {
  const safe = Math.max(0, Math.min(1, value || 0));
  return `${Math.round(safe * 100)}%`;
}

export function RetrievalQualityBar({ quality }: RetrievalQualityBarProps) {
  return (
    <div className="mt-2 grid grid-cols-3 gap-2 text-[11px]">
      <div className="rounded-md border border-border/60 bg-muted/20 px-2 py-1">
        <div className="text-muted-foreground">coverage</div>
        <div className="font-semibold">{pct(quality.citation_coverage)}</div>
      </div>
      <div className="rounded-md border border-border/60 bg-muted/20 px-2 py-1">
        <div className="text-muted-foreground">consistency</div>
        <div className="font-semibold">{pct(quality.answer_evidence_consistency)}</div>
      </div>
      <div className="rounded-md border border-border/60 bg-muted/20 px-2 py-1">
        <div className="text-muted-foreground">unsupported</div>
        <div className="font-semibold">{pct(quality.unsupported_claim_rate)}</div>
      </div>
    </div>
  );
}
