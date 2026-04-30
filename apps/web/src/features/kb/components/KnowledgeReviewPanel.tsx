import { useEffect, useMemo, useState } from 'react';
import { Loader2, RefreshCw, Sparkles } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router';
import type { EvidenceBlockDto, ReviewDraftDto, ReviewRunDetailDto } from '@scholar-ai/types';
import type { KBPaperListItem } from '@/services/kbApi';
import { kbReviewApi } from '@/services/kbReviewApi';
import { useElementWidth, useTextMeasure } from '@/lib/text-layout/react';
import { useEvidenceNavigation } from '@/features/chat/hooks/useEvidenceNavigation';
import { navigateToChatWithHandoff } from '@/features/chat/chatHandoff';
import { useLanguage } from '@/app/contexts/LanguageContext';

interface KnowledgeReviewPanelProps {
  kbId: string;
  papers: KBPaperListItem[];
  onRunChanged?: () => void;
}

function ReviewParagraphCard({
  kbId,
  draftId,
  runId,
  paragraphId,
  text,
  citations,
  evidenceBlocks,
  claimVerification,
  draftTitle,
  researchQuestion,
  isZh,
  onRepaired,
}: {
  kbId: string;
  draftId: string;
  runId?: string;
  paragraphId: string;
  text: string;
  citations: Array<Record<string, unknown>>;
  evidenceBlocks: EvidenceBlockDto[];
  claimVerification: Array<Record<string, unknown>>;
  draftTitle: string;
  researchQuestion?: string;
  isZh: boolean;
  onRepaired: (next: ReviewDraftDto) => void;
}) {
  const navigate = useNavigate();
  const { width, setElement } = useElementWidth<HTMLDivElement>(720);
  const measure = useTextMeasure(text, width);
  const [repairingClaimId, setRepairingClaimId] = useState<string | null>(null);
  const { jumpToSource, saveEvidence } = useEvidenceNavigation(isZh);

  const isSafeJump = (url: string) =>
    url.startsWith('/') || url.startsWith('http://') || url.startsWith('https://');

  return (
    <div ref={setElement} className="rounded-xl border border-border/60 bg-paper-1 p-3">
      <p className="text-sm leading-6 text-foreground">{text}</p>
      <div className="mt-2 text-[11px] text-muted-foreground">{`Pretext lines: ${measure.lineCount}`}</div>
      <div className="mt-2 flex flex-wrap gap-2">
        {citations.map((citation, index) => {
          const jump = (citation.citation_jump_url as string) || '';
          const label = `Citation ${index + 1}`;
          return (
            <button
              key={`${label}-${index}`}
              type="button"
              className="rounded-full border border-border/70 px-2 py-1 text-xs hover:border-primary hover:text-primary"
              onClick={() => {
                if (!jump) {
                  return;
                }
                if (!isSafeJump(jump)) {
                  return;
                }
                if (jump.startsWith('/')) {
                  navigate(jump);
                } else {
                  window.location.href = jump;
                }
              }}
            >
              {label}
            </button>
          );
        })}
      </div>

      {evidenceBlocks.length > 0 ? (
        <div className="mt-3 space-y-2">
          {evidenceBlocks.slice(0, 2).map((block, index) => (
            <div key={`${block.evidence_id}-${index}`} className="rounded-md border border-border/60 bg-background/70 px-2 py-2">
              <div className="text-[11px] text-muted-foreground">
                {block.section_path || `Evidence ${index + 1}`}
                {block.page_num ? ` · p.${block.page_num}` : ''}
              </div>
              <div className="mt-1 line-clamp-2 text-xs text-foreground/85">{block.text}</div>
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rounded-md border border-border/70 px-2 py-1 text-[11px] hover:border-primary hover:text-primary"
                  onClick={() => {
                    void jumpToSource(block.source_chunk_id, block.paper_id, block.page_num ?? undefined);
                  }}
                >
                  {isZh ? '打开证据' : 'Open source'}
                </button>
                <button
                  type="button"
                  className="rounded-md border border-border/70 px-2 py-1 text-[11px] hover:border-primary hover:text-primary"
                  onClick={() => {
                    void saveEvidence(text, {
                      ...block,
                      citation_jump_url: block.citation_jump_url || '',
                    }, { surface: 'review' });
                  }}
                >
                  {isZh ? '保存到笔记' : 'Save to Notes'}
                </button>
                <button
                  type="button"
                  className="rounded-md border border-border/70 px-2 py-1 text-[11px] hover:border-primary hover:text-primary"
                  onClick={() => {
                    navigateToChatWithHandoff(
                      navigate,
                      { kbId },
                      {
                        origin: 'review',
                        promptDraft: isZh
                          ? `围绕 Review Draft《${draftTitle}》中的这段证据，继续分析它是否足以支撑当前段落，并给出更稳妥的写法。${researchQuestion ? ` 研究问题：${researchQuestion}` : ''}`
                          : `Continue analyzing whether this evidence is enough to support the current paragraph in review draft "${draftTitle}", and suggest a safer revision.${researchQuestion ? ` Research question: ${researchQuestion}` : ''}`,
                        evidence: [
                          {
                            paperId: block.paper_id,
                            sourceChunkId: block.source_chunk_id,
                            pageNum: block.page_num ?? undefined,
                            claim: text,
                          },
                        ],
                        returnTo: `/knowledge-bases/${kbId}?tab=review&runId=${runId || draftId}`,
                      },
                    );
                  }}
                >
                  {isZh ? '继续问' : 'Continue in Chat'}
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {claimVerification.length > 0 ? (
        <div className="mt-3 space-y-2">
          {claimVerification.map((claim, index) => {
            const claimId = String(claim.claim_id || `claim-${index + 1}`);
            const supportStatus = String(claim.support_status || 'unsupported');
            const claimText = String(claim.claim_text || claim.claim || '');
            return (
              <div key={claimId} className="rounded-md border border-border/60 bg-background/70 px-2 py-2">
                <div className="text-xs font-medium text-foreground">{claimText}</div>
                <div className="mt-1 flex items-center justify-between gap-2">
                  <span
                    className={
                      supportStatus === 'supported'
                        ? 'rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[11px] text-emerald-700'
                        : supportStatus === 'weakly_supported' || supportStatus === 'partially_supported'
                          ? 'rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[11px] text-amber-700'
                          : 'rounded-full border border-rose-500/40 bg-rose-500/10 px-2 py-0.5 text-[11px] text-rose-700'
                    }
                  >
                    {supportStatus === 'supported'
                      ? 'Supported'
                      : supportStatus === 'weakly_supported' || supportStatus === 'partially_supported'
                        ? 'Weakly Supported'
                        : 'Unsupported'}
                  </span>

                  {supportStatus !== 'supported' ? (
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        className="rounded-md border border-border/70 px-2 py-1 text-[11px] hover:border-primary"
                        onClick={() => {
                          navigateToChatWithHandoff(
                            navigate,
                            { kbId },
                            {
                              origin: 'review',
                              promptDraft: isZh
                                ? `围绕这条 claim 继续补强证据并给出更稳妥的表述：${claimText}${researchQuestion ? `。研究问题：${researchQuestion}` : ''}`
                                : `Continue by strengthening the evidence and rewriting this claim more safely: ${claimText}${researchQuestion ? `. Research question: ${researchQuestion}` : ''}`,
                              evidence: evidenceBlocks.slice(0, 2).map((block) => ({
                                paperId: block.paper_id,
                                sourceChunkId: block.source_chunk_id,
                                pageNum: block.page_num ?? undefined,
                                claim: claimText,
                              })),
                              returnTo: `/knowledge-bases/${kbId}?tab=review&runId=${runId || draftId}`,
                            },
                          );
                        }}
                      >
                        {isZh ? '继续问' : 'Continue in Chat'}
                      </button>
                      <button
                        type="button"
                        className="rounded-md border border-border/70 px-2 py-1 text-[11px] hover:border-primary"
                        disabled={repairingClaimId === claimId}
                        onClick={async () => {
                          setRepairingClaimId(claimId);
                          try {
                            const next = await kbReviewApi.repairClaim(kbId, draftId, {
                              paragraph_id: paragraphId,
                              claim_id: claimId,
                            });
                            onRepaired(next);
                          } finally {
                            setRepairingClaimId(null);
                          }
                        }}
                      >
                        {repairingClaimId === claimId ? 'Repairing...' : 'Repair Claim'}
                      </button>
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

export function KnowledgeReviewPanel({ kbId, papers, onRunChanged }: KnowledgeReviewPanelProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [question, setQuestion] = useState('');
  const [selectedPaperIds, setSelectedPaperIds] = useState<string[]>([]);
  const [drafts, setDrafts] = useState<ReviewDraftDto[]>([]);
  const [selectedDraftId, setSelectedDraftId] = useState<string | null>(null);
  const [runDetail, setRunDetail] = useState<ReviewRunDetailDto | null>(null);
  const [runDetailLoading, setRunDetailLoading] = useState(false);

  const selectedDraft = useMemo(
    () => drafts.find((d) => d.id === selectedDraftId) || drafts[0] || null,
    [drafts, selectedDraftId],
  );
  const selectedRunId = searchParams.get('runId');
  const displayDraft = useMemo(() => {
    if (selectedRunId && runDetail?.reviewDraftId) {
      return drafts.find((draft) => draft.id === runDetail.reviewDraftId) || null;
    }
    return selectedDraft;
  }, [drafts, runDetail?.reviewDraftId, selectedDraft, selectedRunId]);
  const draftStatusSummary = useMemo(() => {
    if (!displayDraft) {
      return null;
    }

    if (displayDraft.status === 'failed') {
      return {
        label: 'Needs repair',
        reason: 'The draft pipeline failed and needs evidence or claim follow-up.',
      };
    }

    if (displayDraft.status === 'partial') {
      return {
        label: 'Partial draft',
        reason: 'The draft exists, but some paragraphs still need stronger support.',
      };
    }

    if (displayDraft.status === 'running' || displayDraft.status === 'idle') {
      return {
        label: 'In progress',
        reason: 'Open the run trace to inspect how the current draft is being built.',
      };
    }

    return {
      label: 'Ready to continue',
      reason: 'Use the draft, evidence, and run trace as a launch point for the next question.',
    };
  }, [displayDraft]);

  const loadDrafts = async () => {
    setLoading(true);
    try {
      const response = await kbReviewApi.listDrafts(kbId, { limit: 50, offset: 0 });
      setDrafts(response.items);
      if (!selectedRunId && !selectedDraftId && response.items.length > 0) {
        setSelectedDraftId(response.items[0].id);
      }
    } catch {
      setDrafts([]);
    } finally {
      setLoading(false);
    }
  };

  const loadRunDetail = async (runId?: string) => {
    if (!runId) {
      setRunDetailLoading(false);
      setRunDetail(null);
      return;
    }
    setRunDetailLoading(true);
    try {
      const detail = await kbReviewApi.getRunDetail(runId);
      setRunDetail(detail);
      if (detail.reviewDraftId) {
        setSelectedDraftId(detail.reviewDraftId);
      }
    } catch {
      setRunDetail(null);
    } finally {
      setRunDetailLoading(false);
    }
  };

  useEffect(() => {
    void loadDrafts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kbId]);

  useEffect(() => {
    if (selectedRunId) {
      void loadRunDetail(selectedRunId);
      return;
    }
    if (!selectedDraft?.runId) {
      setRunDetailLoading(false);
      setRunDetail(null);
      return;
    }
    void loadRunDetail(selectedDraft.runId);
  }, [selectedDraft?.runId, selectedRunId]);

  const togglePaper = (paperId: string) => {
    setSelectedPaperIds((prev) =>
      prev.includes(paperId) ? prev.filter((id) => id !== paperId) : [...prev, paperId],
    );
  };

  const handleGenerate = async () => {
    setCreating(true);
    try {
      const draft = await kbReviewApi.createDraft(kbId, {
        mode: 'outline_and_draft',
        paper_ids: selectedPaperIds.length > 0 ? selectedPaperIds : undefined,
        question: question.trim() || undefined,
      });
      await loadDrafts();
      setSelectedDraftId(draft.id);
      await loadRunDetail(draft.runId);
      onRunChanged?.();
    } finally {
      setCreating(false);
    }
  };

  const handleRetry = async () => {
    if (!displayDraft) {
      return;
    }
    setRetrying(true);
    try {
      const refreshed = await kbReviewApi.retryDraft(kbId, displayDraft.id);
      await loadDrafts();
      setSelectedDraftId(refreshed.id);
      await loadRunDetail(refreshed.runId);
      onRunChanged?.();
    } finally {
      setRetrying(false);
    }
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[320px,1fr]">
      <aside className="space-y-4 rounded-xl border border-border/70 bg-paper-1 p-4">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wider">Review Draft</h3>
          <p className="mt-1 text-xs text-muted-foreground">支持整库或论文子集生成</p>
        </div>

        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="可选：指定研究问题"
          className="min-h-20 w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm"
        />

        <div className="max-h-40 space-y-2 overflow-auto rounded-md border border-border/50 p-2">
          {papers.map((paper) => (
            <label key={paper.id} className="flex items-start gap-2 text-xs">
              <input
                type="checkbox"
                checked={selectedPaperIds.includes(paper.id)}
                onChange={() => togglePaper(paper.id)}
              />
              <span className="line-clamp-2">{paper.title}</span>
            </label>
          ))}
        </div>

        <button
          type="button"
          disabled={creating}
          className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
          onClick={() => void handleGenerate()}
        >
          {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          生成 Outline + Draft
        </button>

        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">历史 Drafts</div>
          {loading ? (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> 加载中
            </div>
          ) : drafts.length === 0 ? (
            <div className="text-xs text-muted-foreground">暂无 Draft</div>
          ) : (
            drafts.map((draft) => (
              <button
                key={draft.id}
                type="button"
                onClick={() => setSelectedDraftId(draft.id)}
                className={`w-full rounded-md border px-2 py-2 text-left text-xs ${
                  selectedDraft?.id === draft.id
                    ? 'border-primary bg-primary/5'
                    : 'border-border/60 hover:border-primary/50'
                }`}
              >
                <div className="font-medium">{draft.title}</div>
                <div className="mt-1 text-muted-foreground">{draft.status}</div>
              </button>
            ))
          )}
        </div>
      </aside>

      <section className="space-y-4">
        {!displayDraft ? (
          <div className="rounded-xl border border-border/70 bg-paper-1 p-6 text-sm text-muted-foreground">
            {runDetail
              ? '当前 run trace 已加载，但对应 draft 不在当前列表中。'
              : '还没有 Review Draft，先发起一次生成。'}
          </div>
        ) : (
          <>
            <div className="rounded-xl border border-border/70 bg-paper-1 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="text-lg font-semibold">{displayDraft.title}</h3>
                  <div className="text-xs text-muted-foreground">status: {displayDraft.status}</div>
                </div>
                {(displayDraft.status === 'failed' || displayDraft.status === 'partial') ? (
                  <button
                    type="button"
                    disabled={retrying}
                    onClick={() => void handleRetry()}
                    className="inline-flex items-center gap-2 rounded-md border border-border/70 px-3 py-1.5 text-xs hover:border-primary"
                  >
                    {retrying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                    Retry
                  </button>
                ) : null}
              </div>

              {draftStatusSummary ? (
                <div className="mt-4 grid gap-3 md:grid-cols-4">
                  <div className="rounded-lg border border-border/60 bg-background/70 p-3">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Next Step</div>
                    <div className="mt-2 text-sm font-medium text-foreground">{draftStatusSummary.label}</div>
                    <div className="mt-1 text-xs leading-relaxed text-muted-foreground">{draftStatusSummary.reason}</div>
                  </div>
                  <div className="rounded-lg border border-border/60 bg-background/70 p-3">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Citation Coverage</div>
                    <div className="mt-2 text-sm font-medium text-foreground">{Math.round(displayDraft.quality.citation_coverage * 100)}%</div>
                    <div className="mt-1 text-xs text-muted-foreground">How much of the draft is backed by citations.</div>
                  </div>
                  <div className="rounded-lg border border-border/60 bg-background/70 p-3">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Unsupported Rate</div>
                    <div className="mt-2 text-sm font-medium text-foreground">{Math.round(displayDraft.quality.unsupported_paragraph_rate * 100)}%</div>
                    <div className="mt-1 text-xs text-muted-foreground">Paragraphs that still need stronger support.</div>
                  </div>
                  <div className="rounded-lg border border-border/60 bg-background/70 p-3">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Fallback</div>
                    <div className="mt-2 text-sm font-medium text-foreground">{displayDraft.quality.fallback_used ? 'Used' : 'Clean'}</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {displayDraft.errorState ? `error_state: ${displayDraft.errorState}` : 'No fallback warning on the latest draft.'}
                    </div>
                  </div>
                </div>
              ) : null}

              <div className="mt-3 text-sm">
                <div className="font-medium">Research Question</div>
                <div className="mt-1 text-muted-foreground">{displayDraft.outlineDoc.research_question}</div>
              </div>

              <div className="mt-3">
                <div className="font-medium text-sm">Outline Themes</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {displayDraft.outlineDoc.themes.map((theme) => (
                    <span key={theme} className="rounded-full border border-border/70 px-2 py-0.5 text-xs">
                      {theme}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-3">
              {displayDraft.draftDoc.sections.map((section) => (
                <div key={section.heading} className="rounded-xl border border-border/70 bg-paper-1 p-4">
                  <h4 className="text-sm font-semibold">{section.heading}</h4>
                  {section.omitted_reason ? (
                    <div className="mt-2 text-xs text-amber-600">omitted: {section.omitted_reason}</div>
                  ) : null}
                  <div className="mt-3 space-y-3">
                    {section.paragraphs.map((paragraph) => (
                      <ReviewParagraphCard
                        kbId={kbId}
                        draftId={displayDraft.id}
                        runId={displayDraft.runId}
                        paragraphId={paragraph.paragraph_id}
                        key={paragraph.paragraph_id}
                        text={paragraph.text}
                        citations={paragraph.citations}
                        evidenceBlocks={paragraph.evidence_blocks || []}
                        claimVerification={Array.isArray((paragraph as any).claim_verification) ? (paragraph as any).claim_verification : []}
                        draftTitle={displayDraft.title}
                        researchQuestion={displayDraft.outlineDoc.research_question}
                        isZh={isZh}
                        onRepaired={(nextDraft) => {
                          setDrafts((prev) => prev.map((item) => (item.id === nextDraft.id ? nextDraft : item)));
                          setSelectedDraftId(nextDraft.id);
                        }}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>

          </>
        )}

        <div className="rounded-xl border border-border/70 bg-paper-1 p-4">
          <div className="mb-2 text-sm font-semibold">Run Trace</div>
          {!runDetail ? (
            <div className="text-xs text-muted-foreground">
              {runDetailLoading
                ? '正在加载 run trace...'
                : selectedRunId
                  ? '指定 run 的 trace 暂不可读。'
                  : '当前 Draft 尚无可读 run trace。'}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="text-xs text-muted-foreground">run_id: {runDetail.id}</div>
              <div className="space-y-2">
                {runDetail.steps.map((step, index) => (
                  <div key={`${String(step.step_name)}-${index}`} className="rounded-md border border-border/50 px-2 py-2 text-xs">
                    <div className="font-medium">{String(step.step_name || `step-${index + 1}`)}</div>
                    <div className="mt-1 text-muted-foreground">status: {String(step.status || 'unknown')}</div>
                    <div className="mt-1 text-muted-foreground">
                      in/out: {String((step.metadata as any)?.input_schema_name || '-')}
                      {' -> '}
                      {String((step.metadata as any)?.output_schema_name || '-')}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
