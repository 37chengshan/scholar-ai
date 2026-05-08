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
import { isSafeNavigationTarget, openSafeExternalLink } from '@/lib/navigation';

interface KnowledgeReviewPanelProps {
  kbId: string;
  papers: KBPaperListItem[];
  onRunChanged?: () => void;
}

function formatReviewStatus(status: string, isZh: boolean) {
  if (!isZh) return status;
  switch (status) {
    case 'failed':
      return '失败';
    case 'partial':
      return '部分完成';
    case 'running':
      return '进行中';
    case 'idle':
      return '等待中';
    case 'completed':
      return '已完成';
    default:
      return status;
  }
}

function formatSupportStatus(status: string, isZh: boolean) {
  if (!isZh) {
    if (status === 'supported') return 'Supported';
    if (status === 'weakly_supported' || status === 'partially_supported') return 'Weakly Supported';
    return 'Unsupported';
  }
  if (status === 'supported') return '证据充分';
  if (status === 'weakly_supported' || status === 'partially_supported') return '证据偏弱';
  return '证据不足';
}

function formatReviewStepName(stepName: string, isZh: boolean) {
  if (!isZh) return stepName;
  const normalized = stepName.toLowerCase();
  if (normalized.includes('outline')) return '提纲生成';
  if (normalized.includes('draft')) return '草稿生成';
  if (normalized.includes('claim')) return '论断核验';
  if (normalized.includes('evidence')) return '证据组装';
  if (normalized.includes('citation')) return '引文校验';
  if (normalized.includes('repair')) return '修复补强';
  return stepName;
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

  return (
    <div ref={setElement} className="rounded-xl border border-border/60 bg-paper-1 p-3">
      <p className="text-sm leading-6 text-foreground">{text}</p>
      <div className="mt-2 text-[11px] text-muted-foreground">
        {isZh ? `排版测量行数：${measure.lineCount}` : `Pretext lines: ${measure.lineCount}`}
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {citations.map((citation, index) => {
          const jump = (citation.citation_jump_url as string) || '';
          const label = isZh ? `引文 ${index + 1}` : `Citation ${index + 1}`;
          return (
            <button
              key={`${label}-${index}`}
              type="button"
              className="rounded-full border border-border/70 px-2 py-1 text-xs hover:border-primary hover:text-primary"
              onClick={() => {
                if (!jump) {
                  return;
                }
                if (!isSafeNavigationTarget(jump)) {
                  return;
                }
                if (jump.startsWith('/')) {
                  navigate(jump);
                } else {
                  openSafeExternalLink(jump);
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
                    {formatSupportStatus(supportStatus, isZh)}
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
                        {repairingClaimId === claimId
                          ? (isZh ? '修复中...' : 'Repairing...')
                          : (isZh ? '修复论断' : 'Repair Claim')}
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
  const navigate = useNavigate();
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
        label: isZh ? '需要修复' : 'Needs repair',
        reason: isZh
          ? '当前草稿链路失败，需要补证据或修复关键论断后再继续。'
          : 'The draft pipeline failed and needs evidence or claim follow-up.',
      };
    }

    if (displayDraft.status === 'partial') {
      return {
        label: isZh ? '部分完成' : 'Partial draft',
        reason: isZh
          ? '草稿已生成，但部分段落仍需要更强的证据支撑。'
          : 'The draft exists, but some paragraphs still need stronger support.',
      };
    }

    if (displayDraft.status === 'running' || displayDraft.status === 'idle') {
      return {
        label: isZh ? '生成中' : 'In progress',
        reason: isZh
          ? '可结合运行轨迹查看当前草稿是如何逐步生成的。'
          : 'Open the run trace to inspect how the current draft is being built.',
      };
    }

    return {
      label: isZh ? '可继续' : 'Ready to continue',
      reason: isZh
        ? '可以直接从草稿、证据和运行轨迹继续提问或完善结论。'
        : 'Use the draft, evidence, and run trace as a launch point for the next question.',
    };
  }, [displayDraft, isZh]);

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
          <h3 className="text-sm font-semibold uppercase tracking-wider font-serif tracking-tight">{isZh ? '综述草稿' : 'Review Draft'}</h3>
          <p className="mt-1 text-xs text-muted-foreground">{isZh ? '支持整库或论文子集生成' : 'Generate from the whole KB or a paper subset.'}</p>
        </div>

        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={isZh ? '可选：指定研究问题' : 'Optional: specify a research question'}
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
          {isZh ? '生成提纲与草稿' : 'Generate Outline + Draft'}
        </button>

        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{isZh ? '历史草稿' : 'Draft History'}</div>
          {loading ? (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> {isZh ? '加载中' : 'Loading'}
            </div>
          ) : drafts.length === 0 ? (
            <div className="text-xs text-muted-foreground">{isZh ? '还没有草稿' : 'No drafts yet'}</div>
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
                <div className="mt-1 text-muted-foreground">{formatReviewStatus(draft.status, isZh)}</div>
              </button>
            ))
          )}
        </div>
      </aside>

      <section className="space-y-4">
        {!displayDraft ? (
          <div className="rounded-xl border border-border/70 bg-paper-1 p-6 text-sm text-muted-foreground">
            {runDetail
              ? (isZh ? '当前运行轨迹已加载，但对应草稿不在当前列表中。' : 'Run trace loaded, but its draft is not in the current list.')
              : (isZh ? '还没有综述草稿，先发起一次生成。' : 'No review draft yet. Generate one first.')}
          </div>
        ) : (
          <>
            <div className="rounded-xl border border-border/70 bg-paper-1 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="text-lg font-semibold font-serif tracking-tight">{displayDraft.title}</h3>
                  <div className="text-xs text-muted-foreground">
                    {isZh ? '状态' : 'Status'}: {formatReviewStatus(displayDraft.status, isZh)}
                  </div>
                </div>
                {(displayDraft.status === 'failed' || displayDraft.status === 'partial') ? (
                  <button
                    type="button"
                    disabled={retrying}
                    onClick={() => void handleRetry()}
                    className="inline-flex items-center gap-2 rounded-md border border-border/70 px-3 py-1.5 text-xs hover:border-primary"
                  >
                    {retrying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                    {isZh ? '重试生成' : 'Retry'}
                  </button>
                ) : null}
              </div>

              {draftStatusSummary ? (
                <div className="mt-4 grid gap-3 md:grid-cols-4">
                  <div className="rounded-lg border border-border/60 bg-background/70 p-3">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{isZh ? '下一步' : 'Next Step'}</div>
                    <div className="mt-2 text-sm font-medium text-foreground">{draftStatusSummary.label}</div>
                    <div className="mt-1 text-xs leading-relaxed text-muted-foreground">{draftStatusSummary.reason}</div>
                  </div>
                  <div className="rounded-lg border border-border/60 bg-background/70 p-3">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{isZh ? '引文覆盖率' : 'Citation Coverage'}</div>
                    <div className="mt-2 text-sm font-medium text-foreground">{Math.round(displayDraft.quality.citation_coverage * 100)}%</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {isZh ? '衡量草稿中有多少内容已经被明确引文支撑。' : 'How much of the draft is backed by citations.'}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border/60 bg-background/70 p-3">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{isZh ? '证据不足占比' : 'Unsupported Rate'}</div>
                    <div className="mt-2 text-sm font-medium text-foreground">{Math.round(displayDraft.quality.unsupported_paragraph_rate * 100)}%</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {isZh ? '这些段落仍需要更强的证据支撑。' : 'Paragraphs that still need stronger support.'}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border/60 bg-background/70 p-3">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{isZh ? '回退状态' : 'Fallback'}</div>
                    <div className="mt-2 text-sm font-medium text-foreground">{displayDraft.quality.fallback_used ? (isZh ? '已触发' : 'Used') : (isZh ? '未触发' : 'Clean')}</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {displayDraft.errorState
                        ? (isZh ? `最近一次生成触发了回退：${displayDraft.errorState}` : `Fallback triggered on the latest draft: ${displayDraft.errorState}`)
                        : (isZh ? '最近一次生成没有触发回退警告。' : 'No fallback warning on the latest draft.')}
                    </div>
                  </div>
                </div>
              ) : null}

              {displayDraft.knownLimitations.length > 0 ? (
                <div className="mt-4 rounded-lg border border-border/60 bg-background/70 p-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                    {isZh ? '已知限制' : 'Known Limitations'}
                  </div>
                  <ul className="mt-2 space-y-1 text-sm text-foreground">
                    {displayDraft.knownLimitations.map((item) => (
                      <li key={item}>- {item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div className="mt-3 text-sm">
                <div className="font-medium">{isZh ? '研究问题' : 'Research Question'}</div>
                <div className="mt-1 text-muted-foreground">{displayDraft.outlineDoc.research_question}</div>
              </div>

              <div className="mt-3">
                <div className="font-medium text-sm">{isZh ? '提纲主题' : 'Outline Themes'}</div>
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
                    <div className="mt-2 text-xs text-amber-600">
                      {isZh ? `本节暂未展开：${section.omitted_reason}` : `Omitted: ${section.omitted_reason}`}
                    </div>
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
          <div className="mb-2 text-sm font-semibold">{isZh ? '运行轨迹' : 'Run Trace'}</div>
          {!runDetail ? (
            <div className="text-xs text-muted-foreground">
              {runDetailLoading
                ? (isZh ? '正在加载运行轨迹...' : 'Loading run trace...')
                : selectedRunId
                  ? (isZh ? '指定运行的轨迹暂不可读。' : 'The selected run trace is not readable right now.')
                  : (isZh ? '当前草稿还没有可读的运行轨迹。' : 'The current draft has no readable run trace yet.')}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="text-xs text-muted-foreground">{isZh ? '运行 ID' : 'Run ID'}: {runDetail.id}</div>
              <div className="space-y-2">
                {runDetail.steps.map((step, index) => (
                  <div key={`${String(step.step_name)}-${index}`} className="rounded-md border border-border/50 px-2 py-2 text-xs">
                    <div className="font-medium">
                      {formatReviewStepName(String(step.step_name || `step-${index + 1}`), isZh)}
                    </div>
                    <div className="mt-1 text-muted-foreground">
                      {isZh ? '状态' : 'Status'}: {formatReviewStatus(String(step.status || 'unknown'), isZh)}
                    </div>
                    <div className="mt-1 text-muted-foreground">
                      {isZh ? '输入/输出' : 'Input/Output'}: {String((step.metadata as any)?.input_schema_name || '-')}
                      {' -> '}
                      {String((step.metadata as any)?.output_schema_name || '-')}
                    </div>
                  </div>
                ))}
              </div>
              {runDetail.artifacts.length > 0 ? (
                <div className="space-y-2">
                  <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {isZh ? '产物包' : 'Artifact Bundle'}
                  </div>
                  {runDetail.artifacts.map((artifact) => (
                    <div key={artifact.artifact_id} className="rounded-md border border-border/50 px-2 py-2 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <div className="font-medium">{artifact.title}</div>
                        {artifact.url ? (
                          <button
                            type="button"
                            className="rounded-md border border-border/70 px-2 py-1 text-[11px] hover:border-primary hover:text-primary"
                            onClick={() => {
                              if (!isSafeNavigationTarget(artifact.url!)) {
                                return;
                              }
                              if (artifact.url!.startsWith('/')) {
                                navigate(artifact.url!);
                              } else {
                                openSafeExternalLink(artifact.url!);
                              }
                            }}
                          >
                            {isZh ? '打开' : 'Open'}
                          </button>
                        ) : null}
                      </div>
                      <div className="mt-1 text-muted-foreground">{artifact.type}</div>
                      {artifact.content ? (
                        <div className="mt-1 whitespace-pre-line text-foreground/80">{artifact.content}</div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
