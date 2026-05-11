import { ArrowRight, BookOpen, Loader2, PanelRightClose, PanelRightOpen, Save } from 'lucide-react';

import type { AnswerContractDto, CompareMatrixDto, CompareCellDto, EvidenceBlockDto } from '@scholar-ai/types';

import { Badge } from '@/app/components/ui/badge';
import { Button } from '@/app/components/ui/button';
import { ScrollArea } from '@/app/components/ui/scroll-area';

import { CompareMatrixTable } from './CompareMatrixTable';

interface CompareMainPanelProps {
  isZh: boolean;
  showInspector: boolean;
  selectedPaperCount: number;
  compareResult: (AnswerContractDto & { compare_matrix: CompareMatrixDto }) | null;
  compareLoading: boolean;
  compareError: string | null;
  onToggleInspector: () => void;
  onOpenChat: () => void;
  onSaveWholeCompare: () => void;
  onJumpEvidence: (block: EvidenceBlockDto) => void;
  onSaveCellEvidence: (cell: CompareCellDto, paperId: string) => void;
  onContinueCellInChat: (cell: CompareCellDto, paperId: string) => void;
}

export function CompareMainPanel({
  isZh,
  showInspector,
  selectedPaperCount,
  compareResult,
  compareLoading,
  compareError,
  onToggleInspector,
  onOpenChat,
  onSaveWholeCompare,
  onJumpEvidence,
  onSaveCellEvidence,
  onContinueCellInChat,
}: CompareMainPanelProps) {
  return (
    <div className="flex h-full min-h-0 flex-col bg-paper-1">
      <div className="border-b border-border/50 px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="font-serif text-xl font-bold tracking-tight">{isZh ? '多论文对比' : 'Compare Papers'}</h1>
            <p className="mt-1 text-xs text-muted-foreground">
              {isZh ? '围绕证据维度比较多篇论文，并继续沉淀到对话或笔记。' : 'Compare papers across evidence-backed dimensions and continue in chat or notes.'}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={onToggleInspector}
              className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-paper-2 px-3 py-2 text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground transition-colors hover:border-primary/20 hover:text-primary"
              aria-pressed={showInspector}
              aria-label={showInspector ? (isZh ? '收起右侧栏' : 'Hide inspector') : (isZh ? '展开右侧栏' : 'Show inspector')}
            >
              {showInspector ? <PanelRightClose className="h-3.5 w-3.5" /> : <PanelRightOpen className="h-3.5 w-3.5" />}
              {showInspector ? (isZh ? '收起侧注' : 'Hide rail') : (isZh ? '展开侧注' : 'Show rail')}
            </button>
            {selectedPaperCount >= 2 && compareResult ? (
              <>
                <Button variant="outline" size="sm" onClick={onOpenChat}>
                  <ArrowRight className="mr-1.5 h-4 w-4" />
                  {isZh ? '继续追问' : 'Continue in Chat'}
                </Button>
                <Button variant="outline" size="sm" onClick={onSaveWholeCompare}>
                  <Save className="mr-1.5 h-4 w-4" />
                  {isZh ? '保存到笔记' : 'Save to Notes'}
                </Button>
              </>
            ) : null}
          </div>
        </div>
      </div>
      <ScrollArea className="flex-1 p-3">
        {compareLoading ? (
          <div className="flex h-64 items-center justify-center gap-2 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>{isZh ? '正在检索并构建对比表…' : 'Retrieving evidence and building table…'}</span>
          </div>
        ) : compareError ? (
          <div className="flex h-64 items-center justify-center text-destructive">{compareError}</div>
        ) : compareResult?.compare_matrix ? (
          <div className="space-y-6">
            <CompareMatrixTable
              matrix={compareResult.compare_matrix}
              onJumpEvidence={onJumpEvidence}
              onSaveEvidence={onSaveCellEvidence}
              onContinueInChat={onContinueCellInChat}
            />
            {compareResult.compare_matrix.cross_paper_insights.length > 0 ? (
              <section>
                <h3 className="mb-2 font-serif text-sm font-semibold tracking-tight text-foreground">
                  {isZh ? '跨论文洞察' : 'Cross-paper Insights'}
                </h3>
                <div className="space-y-2">
                  {compareResult.compare_matrix.cross_paper_insights.map((insight, index) => (
                    <div
                      key={index}
                      className="rounded-xl border border-border/50 bg-background px-3 py-2"
                    >
                      <p className="text-sm text-foreground/90">{insight.claim}</p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {insight.supporting_paper_ids.map((paperId) => (
                          <Badge key={paperId} variant="outline" className="text-[10px]">
                            {paperId}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}
          </div>
        ) : (
          <div className="flex h-64 flex-col items-center justify-center gap-3 text-muted-foreground">
            <BookOpen className="h-8 w-8 opacity-40" />
            <p className="text-sm">
              {isZh ? '选择 2-10 篇论文，点击「生成对比表」' : 'Select 2–10 papers and click "Generate Compare Table"'}
            </p>
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
