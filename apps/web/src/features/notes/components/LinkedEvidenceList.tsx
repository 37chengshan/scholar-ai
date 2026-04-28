import { useMemo } from 'react';
import { useNavigate } from 'react-router';
import type { EvidenceBlockDto } from '@scholar-ai/types';
import { measureEvidenceBlock, tokenizeEvidenceInline } from '@/lib/text-layout';

interface LinkedEvidenceListProps {
  evidence: EvidenceBlockDto[];
}

export function LinkedEvidenceList({ evidence }: LinkedEvidenceListProps) {
  const navigate = useNavigate();

  const measured = useMemo(
    () =>
      evidence.map((item) => ({
        item,
        layout: measureEvidenceBlock(item, 560),
        tokens: tokenizeEvidenceInline({
          paperId: item.paper_id,
          pageNum: item.page_num,
          sectionPath: item.section_path,
        }),
      })),
    [evidence],
  );

  if (measured.length === 0) {
    return null;
  }

  return (
    <section className="mb-5 rounded-xl border border-border/60 bg-muted/10 p-4">
      <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        Linked Evidence
      </div>
      <div className="space-y-3">
        {measured.map(({ item, layout, tokens }) => (
          <article
            key={`${item.evidence_id}-${item.source_chunk_id}`}
            className="rounded-lg border border-border/60 bg-background p-3"
            style={{ minHeight: `${layout.height}px` }}
          >
            <div className="mb-2 flex flex-wrap items-center gap-1.5 text-[11px]">
              {tokens.map((token, index) => (
                <span
                  key={`${item.evidence_id}-${index}`}
                  className={token.kind === 'tag' || token.kind === 'evidence'
                    ? 'rounded-full border border-border/60 bg-muted/30 px-2 py-0.5 text-foreground/90'
                    : 'text-muted-foreground'}
                >
                  {token.text}
                </span>
              ))}
              <span className="ml-auto text-muted-foreground">{item.content_type}</span>
            </div>
            <p className="text-sm leading-6 text-foreground/90">{item.text}</p>
            {item.user_comment ? (
              <p className="mt-2 rounded-md bg-muted/40 px-2.5 py-2 text-xs text-muted-foreground">
                {item.user_comment}
              </p>
            ) : null}
            <div className="mt-3 flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
              <span>
                {item.support_status || 'supported'}
                {item.score !== undefined && item.score !== null ? ` · score ${item.score.toFixed(2)}` : ''}
              </span>
              <button
                type="button"
                className="rounded-md border border-border/70 px-2 py-1 text-foreground hover:border-primary/50 hover:text-primary"
                onClick={() => navigate(item.citation_jump_url)}
              >
                Open source
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
