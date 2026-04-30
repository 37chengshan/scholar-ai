import type { AnswerClaim } from '@/features/chat/components/workspaceTypes';

interface ClaimSupportListProps {
  claims: AnswerClaim[];
}

export function ClaimSupportList({ claims }: ClaimSupportListProps) {
  if (claims.length === 0) {
    return null;
  }

  return (
    <ul className="mt-2 space-y-1">
      {claims.map((claim, index) => (
        <li key={`${claim.claim}-${index}`} className="rounded-md border border-border/60 bg-muted/20 px-2 py-1.5 text-xs">
          <div className="mb-1 font-medium text-foreground/90">{claim.claim}</div>
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <span>support:</span>
            <span
              className={
                claim.support_status === 'supported'
                  ? 'rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-emerald-700'
                  : claim.support_status === 'weakly_supported' || claim.support_status === 'partially_supported'
                    ? 'rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-amber-700'
                    : 'rounded-full border border-rose-500/40 bg-rose-500/10 px-2 py-0.5 text-rose-700'
              }
            >
              {claim.support_status === 'supported'
                ? 'Supported'
                : claim.support_status === 'weakly_supported' || claim.support_status === 'partially_supported'
                  ? 'Weakly Supported'
                  : 'Unsupported'}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}
