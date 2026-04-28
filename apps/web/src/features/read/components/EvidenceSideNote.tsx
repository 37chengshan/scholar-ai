import { useEffect, useState } from 'react';
import type { EvidenceBlockDto } from '@scholar-ai/types';
import { getEvidenceSource } from '@/services/evidenceApi';

interface EvidenceSideNoteProps {
  source: string;
  sourceId: string;
  page: number;
  paperId: string;
  targetNoteId: string | null;
  onSaveEvidence: (claim: string, block: EvidenceBlockDto) => void;
}

export function EvidenceSideNote({
  source,
  sourceId,
  page,
  paperId,
  targetNoteId,
  onSaveEvidence,
}: EvidenceSideNoteProps) {
  const [evidence, setEvidence] = useState<EvidenceBlockDto | null>(null);

  useEffect(() => {
    let cancelled = false;

    if (!sourceId) {
      setEvidence(null);
      return;
    }

    void getEvidenceSource(sourceId)
      .then((payload) => {
        if (cancelled) {
          return;
        }
        setEvidence({
          evidence_id: payload.evidence_id,
          source_type: payload.source_type,
          paper_id: payload.paper_id || paperId,
          source_chunk_id: payload.source_chunk_id,
          page_num: payload.page_num || page,
          section_path: payload.section_path || null,
          content_type: payload.content_type || 'text',
          text: payload.content || payload.anchor_text || '',
          citation_jump_url: payload.citation_jump_url,
        });
      })
      .catch(() => {
        if (!cancelled) {
          setEvidence(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [page, paperId, sourceId]);

  if (!sourceId) {
    return null;
  }

  return (
    <div className="rounded-md border border-border/70 bg-muted/20 px-3 py-2 text-xs">
      <div className="font-semibold text-foreground/90">Evidence Side Note</div>
      <div className="mt-1 text-muted-foreground">source: {source}</div>
      <div className="text-muted-foreground">chunk: {sourceId}</div>
      <div className="text-muted-foreground">page: {page}</div>
      {evidence?.text ? (
        <p className="mt-2 line-clamp-4 text-foreground/90">{evidence.text}</p>
      ) : null}
      {evidence ? (
        <button
          type="button"
          className="mt-2 rounded-md border border-border/70 px-2 py-1 text-[11px] text-foreground hover:border-primary/50 hover:text-primary"
          onClick={() => onSaveEvidence(`Evidence from ${evidence.paper_id}`, evidence)}
        >
          {targetNoteId ? 'Append to note' : 'Save to notes'}
        </button>
      ) : null}
    </div>
  );
}
