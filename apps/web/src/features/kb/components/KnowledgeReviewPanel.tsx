import { useEffect, useMemo, useState } from 'react';
import { Loader2, RefreshCw, Sparkles } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router';
import type { ReviewDraftDto, ReviewRunDetailDto } from '@scholar-ai/types';
import type { KBPaperListItem } from '@/services/kbApi';
import { kbReviewApi } from '@/services/kbReviewApi';
import { useElementWidth, useTextMeasure } from '@/lib/text-layout/react';

interface KnowledgeReviewPanelProps {
  kbId: string;
  papers: KBPaperListItem[];
  onRunChanged?: () => void;
}

function ReviewParagraphCard({
  text,
  citations,
}: {
  text: string;
  citations: Array<Record<string, unknown>>;
}) {
  const navigate = useNavigate();
  const { width, setElement } = useElementWidth<HTMLDivElement>(720);
  const measure = useTextMeasure(text, width);

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
    </div>
  );
}

export function KnowledgeReviewPanel({ kbId, papers, onRunChanged }: KnowledgeReviewPanelProps) {
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [question, setQuestion] = useState('');
  const [selectedPaperIds, setSelectedPaperIds] = useState<string[]>([]);
  const [drafts, setDrafts] = useState<ReviewDraftDto[]>([]);
  const [selectedDraftId, setSelectedDraftId] = useState<string | null>(null);
  const [runDetail, setRunDetail] = useState<ReviewRunDetailDto | null>(null);

  const selectedDraft = useMemo(
    () => drafts.find((d) => d.id === selectedDraftId) || drafts[0] || null,
    [drafts, selectedDraftId],
  );
  const selectedRunId = searchParams.get('runId');

  const loadDrafts = async () => {
    setLoading(true);
    try {
      const response = await kbReviewApi.listDrafts(kbId, { limit: 50, offset: 0 });
      setDrafts(response.items);
      if (!selectedDraftId && response.items.length > 0) {
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
      setRunDetail(null);
      return;
    }
    try {
      const detail = await kbReviewApi.getRunDetail(runId);
      setRunDetail(detail);
      if (detail.reviewDraftId) {
        setSelectedDraftId(detail.reviewDraftId);
      }
    } catch {
      setRunDetail(null);
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
    if (!selectedDraft) {
      return;
    }
    setRetrying(true);
    try {
      const refreshed = await kbReviewApi.retryDraft(kbId, selectedDraft.id);
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
        {!selectedDraft ? (
          <div className="rounded-xl border border-border/70 bg-paper-1 p-6 text-sm text-muted-foreground">
            还没有 Review Draft，先发起一次生成。
          </div>
        ) : (
          <>
            <div className="rounded-xl border border-border/70 bg-paper-1 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="text-lg font-semibold">{selectedDraft.title}</h3>
                  <div className="text-xs text-muted-foreground">status: {selectedDraft.status}</div>
                </div>
                {(selectedDraft.status === 'failed' || selectedDraft.status === 'partial') ? (
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

              <div className="mt-3 text-sm">
                <div className="font-medium">Research Question</div>
                <div className="mt-1 text-muted-foreground">{selectedDraft.outlineDoc.research_question}</div>
              </div>

              <div className="mt-3">
                <div className="font-medium text-sm">Outline Themes</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {selectedDraft.outlineDoc.themes.map((theme) => (
                    <span key={theme} className="rounded-full border border-border/70 px-2 py-0.5 text-xs">
                      {theme}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-3">
              {selectedDraft.draftDoc.sections.map((section) => (
                <div key={section.heading} className="rounded-xl border border-border/70 bg-paper-1 p-4">
                  <h4 className="text-sm font-semibold">{section.heading}</h4>
                  {section.omitted_reason ? (
                    <div className="mt-2 text-xs text-amber-600">omitted: {section.omitted_reason}</div>
                  ) : null}
                  <div className="mt-3 space-y-3">
                    {section.paragraphs.map((paragraph) => (
                      <ReviewParagraphCard
                        key={paragraph.paragraph_id}
                        text={paragraph.text}
                        citations={paragraph.citations}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="rounded-xl border border-border/70 bg-paper-1 p-4">
              <div className="mb-2 text-sm font-semibold">Run Trace</div>
              {!runDetail ? (
                <div className="text-xs text-muted-foreground">当前 Draft 尚无可读 run trace。</div>
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
          </>
        )}
      </section>
    </div>
  );
}
