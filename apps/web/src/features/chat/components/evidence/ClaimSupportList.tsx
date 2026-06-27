import type { AnswerClaim } from '@/features/chat/components/workspaceTypes';
import { useLanguage } from '@/app/contexts/LanguageContext';
import { normalizeAnswerClaimCopy } from '@/features/chat/lib/answerCopy';

interface ClaimSupportListProps {
  claims: AnswerClaim[];
  answerMode?: 'full' | 'partial' | 'abstain';
}

export function ClaimSupportList({ claims, answerMode }: ClaimSupportListProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  if (claims.length === 0) {
    return null;
  }

  return (
    <ul className="mt-2 space-y-1">
      {claims.map((claim, index) => (
        <li key={`${claim.claim}-${index}`} className="rounded-md border border-border/60 bg-muted/20 px-2 py-1.5 text-xs">
          <div className="mb-1 font-medium text-foreground/90">
            {normalizeAnswerClaimCopy(claim.claim, answerMode, isZh)}
          </div>
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <span>{isZh ? '证据支持：' : 'Support:'}</span>
            <span
              className={
                claim.support_status === 'supported'
                  ? 'rounded-full border border-[var(--color-success)]/40 bg-[var(--color-success)]/10 px-2 py-0.5 text-[var(--color-success)]'
                  : claim.support_status === 'weakly_supported' || claim.support_status === 'partially_supported'
                    ? 'rounded-full border border-[var(--color-warning)]/40 bg-[var(--color-warning)]/10 px-2 py-0.5 text-[var(--color-warning)]'
                    : 'rounded-full border border-destructive/40 bg-destructive/10 px-2 py-0.5 text-destructive'
              }
            >
              {claim.support_status === 'supported'
                ? (isZh ? '证据充分' : 'Supported')
                : claim.support_status === 'weakly_supported' || claim.support_status === 'partially_supported'
                  ? (isZh ? '证据偏弱' : 'Weakly Supported')
                  : (isZh ? '证据不足' : 'Unsupported')}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}
