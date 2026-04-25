/**
 * EvidencePanel — Displays collected evidence and citations for the run.
 *
 * Per 战役 B WP4: Evidence panel replaces the old citations panel.
 */

import { motion, AnimatePresence } from 'motion/react';
import type { RunEvidence } from '@/features/chat/types/run';

interface EvidencePanelProps {
  evidence: RunEvidence[];
  maxVisible?: number;
}

type EvidenceKind = 'text' | 'table' | 'figure' | 'summary' | 'relation';

function detectEvidenceKind(item: RunEvidence): EvidenceKind {
  const sourceText = `${item.sectionPath || ''} ${item.anchorText || ''} ${item.textPreview || ''}`.toLowerCase();
  if (sourceText.includes('table')) return 'table';
  if (sourceText.includes('figure') || sourceText.includes('fig.')) return 'figure';
  if (sourceText.includes('summary') || sourceText.includes('conclusion')) return 'summary';
  if (sourceText.includes('relation') || sourceText.includes('citation chain') || sourceText.includes('follow-up')) return 'relation';
  return 'text';
}

function kindLabel(kind: EvidenceKind): string {
  switch (kind) {
    case 'table':
      return 'table';
    case 'figure':
      return 'figure';
    case 'summary':
      return 'summary';
    case 'relation':
      return 'relation';
    default:
      return 'text';
  }
}

function ConsistencyDot({ value }: { value?: number }) {
  if (value == null) return null;
  const color = value >= 0.8 ? 'bg-primary/70' : value >= 0.5 ? 'bg-secondary/80' : 'bg-destructive/75';
  return (
    <span className={`inline-block h-2 w-2 rounded-full ${color}`} title={`Consistency ${(value * 100).toFixed(0)}%`} />
  );
}

export function EvidencePanel({ evidence, maxVisible = 10 }: EvidencePanelProps) {
  if (evidence.length === 0) return null;

  const visible = evidence.slice(0, maxVisible);

  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold text-foreground/85">
        Evidence ({evidence.length})
      </div>
      <AnimatePresence mode="popLayout">
        {visible.map((item, idx) => {
          const kind = detectEvidenceKind(item);
          return (
            <motion.div
              key={item.sourceId || `${item.title}-${idx}`}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-md border border-border/60 bg-muted/20 px-3 py-2"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full border border-border/70 bg-background px-2 py-0.5 text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                      {kindLabel(kind)}
                    </span>
                    <ConsistencyDot value={item.consistency} />
                  </div>
                  <div className="mt-1 truncate text-xs font-medium text-foreground/90">{item.title}</div>
                  <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{item.textPreview}</div>
                  <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
                    {item.pageNum != null ? <span>p.{item.pageNum}</span> : null}
                    {item.sectionPath ? <span className="truncate">{item.sectionPath}</span> : null}
                  </div>
                </div>
                {item.relevance != null ? (
                  <span className="text-[10px] text-foreground/70 whitespace-nowrap">
                    {(item.relevance * 100).toFixed(0)}%
                  </span>
                ) : null}
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
      {evidence.length > maxVisible ? (
        <div className="text-xs text-muted-foreground">+{evidence.length - maxVisible} more</div>
      ) : null}
    </div>
  );
}
