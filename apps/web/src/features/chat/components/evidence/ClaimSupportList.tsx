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
          <div className="text-[11px] text-muted-foreground">support: {claim.support_status}</div>
        </li>
      ))}
    </ul>
  );
}
