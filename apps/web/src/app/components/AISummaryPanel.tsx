/**
 * AI Summary Panel Component
 *
 * Displays AI-generated summary in left sidebar:
 * - Five-paragraph format (Background, Methods, Results, Discussion, Key Contributions)
 * - Loading state while summary is generated
 * - Static display after summary available
 *
 * Requirements: D-06 (AI summary tab in left navigation)
 */

import { Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { EvidenceBlockDto } from '@scholar-ai/types';
import type { ReadingCardDoc, ReadingCardSlot } from '@/features/read/readingCard';
import { ScrollArea } from './ui/scroll-area';
import { useLanguage } from '../contexts/LanguageContext';

interface AISummaryPanelProps {
  paperId: string;
  summary?: string | null;
  readingCardDoc?: ReadingCardDoc | null;
  onJumpCitation?: (block: EvidenceBlockDto) => void;
  onSaveEvidence?: (claim: string, block: EvidenceBlockDto) => void;
}

const SLOT_ORDER: Array<keyof Omit<ReadingCardDoc, 'key_evidence'>> = [
  'research_question',
  'method',
  'experiment',
  'result',
  'conclusion',
  'limitation',
];

function ReadingCardSlotView({
  slot,
  onJumpCitation,
  onSaveEvidence,
}: {
  slot: ReadingCardSlot;
  onJumpCitation?: (block: EvidenceBlockDto) => void;
  onSaveEvidence?: (claim: string, block: EvidenceBlockDto) => void;
}) {
  if (!slot.content && slot.evidence_blocks.length === 0) {
    return null;
  }

  const claimText = slot.content || slot.title;

  return (
    <section className="rounded-2xl border border-border/60 bg-background/80 p-3">
      <h4 className="text-sm font-semibold text-foreground">{slot.title}</h4>
      {slot.content ? <p className="mt-2 text-sm leading-6 text-foreground/90">{slot.content}</p> : null}
      {slot.evidence_blocks.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {slot.evidence_blocks.map((block, index) => (
            <div key={`${block.source_chunk_id}-${index}`} className="flex items-center gap-2">
              <button
                type="button"
                className="rounded-full border border-border/70 px-2 py-1 text-[11px] text-foreground hover:border-primary/50 hover:text-primary"
                onClick={() => onJumpCitation?.(block)}
              >
                {`p.${block.page_num ?? 1}`}
              </button>
              <button
                type="button"
                className="rounded-full border border-border/70 px-2 py-1 text-[11px] text-muted-foreground hover:border-primary/50 hover:text-primary"
                onClick={() => onSaveEvidence?.(claimText, block)}
              >
                Save evidence
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

export function AISummaryPanel({
  paperId,
  summary,
  readingCardDoc,
  onJumpCitation,
  onSaveEvidence,
}: AISummaryPanelProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const hasReadingCard = Boolean(readingCardDoc);
  const hasLegacySummary = Boolean(summary && summary.trim().length > 0);

  return (
    <ScrollArea className="h-full" data-testid="ai-summary-panel" data-paper-id={paperId}>
      <div className="space-y-4 p-4">
        <h3 className="text-lg font-bold">
          {isZh ? 'AI 总结' : 'AI Summary'}
        </h3>

        {hasReadingCard ? (
          <>
            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-[11px] text-emerald-700">
              {isZh ? '优先展示结构化 Reading Card' : 'Showing structured reading card'}
            </div>
            <div className="space-y-3">
              {SLOT_ORDER.map((slotKey) => (
                <ReadingCardSlotView
                  key={slotKey}
                  slot={readingCardDoc![slotKey]}
                  onJumpCitation={onJumpCitation}
                  onSaveEvidence={onSaveEvidence}
                />
              ))}
            </div>
            {readingCardDoc!.key_evidence.length > 0 ? (
              <section className="rounded-2xl border border-border/60 bg-muted/20 p-3">
                <h4 className="text-sm font-semibold text-foreground">
                  {isZh ? '关键证据' : 'Key Evidence'}
                </h4>
                <div className="mt-3 space-y-3">
                  {readingCardDoc!.key_evidence.map((item, index) => (
                    <div key={`${item.label}-${index}`} className="rounded-xl border border-border/50 bg-background px-3 py-2">
                      <div className="text-xs font-medium text-foreground">{item.label}</div>
                      <p className="mt-1 text-sm leading-6 text-foreground/90">{item.content}</p>
                      {item.evidence_blocks[0] ? (
                        <div className="mt-2 flex gap-2">
                          <button
                            type="button"
                            className="rounded-full border border-border/70 px-2 py-1 text-[11px] text-foreground hover:border-primary/50 hover:text-primary"
                            onClick={() => onJumpCitation?.(item.evidence_blocks[0])}
                          >
                            {isZh ? '跳转原文' : 'Jump to source'}
                          </button>
                        <button
                          type="button"
                          className="rounded-full border border-border/70 px-2 py-1 text-[11px] text-muted-foreground hover:border-primary/50 hover:text-primary"
                          onClick={() => onSaveEvidence?.(item.content || item.label, item.evidence_blocks[0])}
                        >
                          Save evidence
                        </button>
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              </section>
            ) : null}
          </>
        ) : hasLegacySummary ? (
          <div className="space-y-3">
            <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-700">
              {isZh ? '缺少 readingCardDoc，回退展示 legacy reading_notes' : 'Missing readingCardDoc, falling back to legacy reading notes'}
            </div>
            <div className="prose prose-sm max-w-none text-[15px] leading-relaxed prose-headings:font-serif prose-headings:text-foreground prose-p:text-foreground/90 prose-strong:text-foreground prose-li:my-1 prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:text-[0.85em]">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {summary!}
              </ReactMarkdown>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">
              {isZh ? '正在生成 AI 总结...' : 'Generating AI summary...'}
            </span>
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
