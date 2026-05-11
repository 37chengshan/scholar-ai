import type { AnswerContractDto, CompareMatrixDto } from '@scholar-ai/types';

import { ScrollArea } from '@/app/components/ui/scroll-area';
import type { Paper } from '@/types';

interface CompareInspectorProps {
  isZh: boolean;
  selectedPapers: Paper[];
  question: string;
  insightCount: number;
  evidenceCount: number;
  compareResult: (AnswerContractDto & { compare_matrix: CompareMatrixDto }) | null;
}

export function CompareInspector({
  isZh,
  selectedPapers,
  question,
  insightCount,
  evidenceCount,
  compareResult,
}: CompareInspectorProps) {
  return (
    <div className="flex h-full min-h-0 flex-col bg-stone-50/70">
      <div className="border-b border-border/50 px-5 py-4">
        <h2 className="text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
          {isZh ? '对比概览' : 'Compare Overview'}
        </h2>
      </div>
      <ScrollArea className="flex-1">
        <div className="flex flex-col gap-6 px-5 py-6">
          <section className="space-y-3">
            <h3 className="text-[9px] font-bold uppercase tracking-[0.22em] text-muted-foreground">{isZh ? '当前选择' : 'Selection'}</h3>
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-xl border border-border/60 bg-background px-3 py-3">
                <div className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">{isZh ? '论文' : 'Papers'}</div>
                <div className="mt-2 font-serif text-2xl font-black text-foreground">{selectedPapers.length}</div>
              </div>
              <div className="rounded-xl border border-border/60 bg-background px-3 py-3">
                <div className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">{isZh ? '维度' : 'Dims'}</div>
                <div className="mt-2 font-serif text-2xl font-black text-foreground">{compareResult?.compare_matrix.dimensions.length ?? 0}</div>
              </div>
            </div>
            {question.trim() ? (
              <div className="rounded-xl border border-border/60 bg-background px-3 py-3 text-xs leading-relaxed text-foreground/80">
                {question.trim()}
              </div>
            ) : null}
          </section>

          <section className="space-y-3">
            <h3 className="text-[9px] font-bold uppercase tracking-[0.22em] text-muted-foreground">{isZh ? '论文列表' : 'Paper Set'}</h3>
            <div className="space-y-2">
              {selectedPapers.length > 0 ? selectedPapers.map((paper) => (
                <div key={paper.id} className="rounded-xl border border-border/60 bg-background px-3 py-2.5">
                  <div className="line-clamp-2 text-sm font-medium text-foreground">{paper.title}</div>
                  <div className="mt-1 text-[11px] text-muted-foreground">
                    {paper.year ? `${paper.year} · ` : ''}{paper.chunkCount ?? 0} {isZh ? '个证据分块' : 'evidence chunks'}
                  </div>
                </div>
              )) : (
                <div className="rounded-xl border border-dashed border-border/60 bg-background px-3 py-4 text-xs text-muted-foreground">
                  {isZh ? '先从左侧添加论文。' : 'Add papers from the left workspace first.'}
                </div>
              )}
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="text-[9px] font-bold uppercase tracking-[0.22em] text-muted-foreground">{isZh ? '结果摘要' : 'Result Summary'}</h3>
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-xl border border-border/60 bg-background px-3 py-3">
                <div className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">{isZh ? '洞察' : 'Insights'}</div>
                <div className="mt-2 font-serif text-2xl font-black text-foreground">{insightCount}</div>
              </div>
              <div className="rounded-xl border border-border/60 bg-background px-3 py-3">
                <div className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">{isZh ? '证据块' : 'Evidence'}</div>
                <div className="mt-2 font-serif text-2xl font-black text-foreground">{evidenceCount}</div>
              </div>
            </div>
            {compareResult?.compare_matrix.summary ? (
              <div className="rounded-xl border border-border/60 bg-background px-3 py-3 text-xs leading-relaxed text-foreground/80">
                {compareResult.compare_matrix.summary}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-border/60 bg-background px-3 py-4 text-xs text-muted-foreground">
                {isZh ? '生成对比表后，这里会显示结果摘要与洞察。' : 'Run the comparison to see summary and cross-paper insights here.'}
              </div>
            )}
          </section>
        </div>
      </ScrollArea>
    </div>
  );
}
