/**
 * CompareCard – Chat 中 response_type=compare 的轻量对比卡片渲染
 *
 * Phase 5.0-6: Visual upgrade to design system v2 tokens.
 * Card-based layout with hover/focus states, accent highlights.
 *
 * 当 Chat 返回 compare 结果时，复用 CompareMatrixDto 数据，渲染
 * 精简版对比卡片，并提供"进入 Compare 工作台"的跳转入口。
 */
import { useNavigate } from 'react-router';
import type { CompareCellDto, EvidenceBlockDto } from '@scholar-ai/types';
import { useEvidenceNavigation } from '@/features/chat/hooks/useEvidenceNavigation';
import type { AnswerContractPayload } from '@/features/chat/components/workspaceTypes';
import { Button } from '@/app/components/ui/button';
import { Badge } from '@/app/components/ui/badge';
import { ArrowRight, AlertCircle } from 'lucide-react';
import { clsx } from 'clsx';

interface CompareCardProps {
  contract: AnswerContractPayload;
  isZh?: boolean;
}

function SupportDot({ status }: { status: CompareCellDto['support_status'] }) {
  const colorMap: Record<string, string> = {
    supported: 'bg-emerald-500',
    partially_supported: 'bg-amber-500',
    unsupported: 'bg-red-500',
    not_enough_evidence: 'bg-muted-foreground/30',
  };
  return (
    <span
      className={clsx(
        'inline-block h-2 w-2 rounded-full transition-colors',
        colorMap[status] ?? colorMap.not_enough_evidence,
      )}
      title={status}
    />
  );
}

export function CompareCard({ contract, isZh = true }: CompareCardProps) {
  const matrix = contract.compare_matrix;
  const navigate = useNavigate();
  const { jumpToSource } = useEvidenceNavigation(isZh);

  if (!matrix) {
    return null;
  }

  const handleJump = (block: EvidenceBlockDto) => {
    void jumpToSource(
      block.source_chunk_id,
      block.paper_id,
      block.page_num ?? undefined,
    );
  };

  const handleOpenWorkbench = () => {
    const ids = matrix.paper_ids.join(',');
    navigate(`/compare?paper_ids=${ids}`);
  };

  // Show at most 4 dimensions inline to avoid overflow in chat panel
  const visibleDims = matrix.dimensions.slice(0, 4);
  const hiddenCount = matrix.dimensions.length - visibleDims.length;

  return (
    <div className="mt-2 rounded-xl border border-border/60 bg-card shadow-[var(--shadow-sm)] p-3 transition-[border-color,box-shadow] duration-[var(--duration-fast)] ease-[var(--ease-standard)] hover:shadow-[var(--shadow-md)] hover:border-border/80">
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-semibold text-foreground/70">
          {isZh ? `多论文对比 (${matrix.paper_ids.length} 篇)` : `Compare (${matrix.paper_ids.length} papers)`}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs transition-colors duration-[var(--duration-fast)]"
          onClick={handleOpenWorkbench}
        >
          {isZh ? '在工作台查看完整表格' : 'View full table'}
          <ArrowRight className="ml-1 h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Card-based layout: one card per paper */}
      <div className="space-y-2">
        {matrix.rows.map((row) => (
          <div
            key={row.paper_id}
            className="rounded-lg border border-border/40 bg-background/60 p-2.5 transition-[border-color,background-color] duration-[var(--duration-fast)] ease-[var(--ease-standard)] hover:border-border/70 hover:bg-background/80 focus-within:border-primary/30 focus-within:ring-1 focus-within:ring-primary/10"
            tabIndex={0}
          >
            {/* Paper title */}
            <div className="mb-2 text-xs font-medium text-foreground truncate">
              {row.title}
            </div>

            {/* Dimension cells */}
            <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${Math.min(visibleDims.length, 3)}, 1fr)` }}>
              {visibleDims.map((d) => {
                const cell = row.cells.find((c) => c.dimension_id === d.id);
                if (!cell || cell.support_status === 'not_enough_evidence') {
                  return (
                    <div key={d.id} className="rounded-md bg-muted/20 px-2 py-1.5">
                      <div className="text-[10px] font-medium text-muted-foreground mb-0.5">{d.label}</div>
                      <div className="text-[11px] text-muted-foreground/40">–</div>
                    </div>
                  );
                }
                const block = cell.evidence_blocks[0];
                return (
                  <div
                    key={d.id}
                    className={clsx(
                      'rounded-md px-2 py-1.5 transition-colors duration-[var(--duration-fast)]',
                      cell.support_status === 'supported' && 'bg-emerald-500/5 border border-emerald-500/20',
                      cell.support_status === 'partially_supported' && 'bg-amber-500/5 border border-amber-500/20',
                      cell.support_status === 'unsupported' && 'bg-red-500/5 border border-red-500/20',
                    )}
                  >
                    <div className="flex items-center gap-1 mb-0.5">
                      <SupportDot status={cell.support_status} />
                      <span className="text-[10px] font-medium text-muted-foreground">{d.label}</span>
                    </div>
                    <div className="text-[11px] text-foreground/80 line-clamp-2">{cell.content}</div>
                    {block && (
                      <button
                        type="button"
                        className="mt-1 text-[10px] text-primary/70 hover:text-primary underline-offset-2 hover:underline transition-colors duration-[var(--duration-fast)]"
                        onClick={() => handleJump(block)}
                      >
                        p.{block.page_num ?? 1}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>

            {hiddenCount > 0 && (
              <div className="mt-1 text-[10px] text-muted-foreground/50">
                +{hiddenCount} {isZh ? '更多维度' : 'more dimensions'}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Cross-paper insights preview */}
      {matrix.cross_paper_insights.length > 0 ? (
        <div className="mt-3 flex items-start gap-1.5 rounded-lg border border-border/40 bg-muted/20 px-2.5 py-2 text-xs transition-colors duration-[var(--duration-fast)] hover:bg-muted/30">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-primary/60" />
          <span className="text-foreground/80">{matrix.cross_paper_insights[0].claim}</span>
          <div className="ml-1 flex gap-1">
            {matrix.cross_paper_insights[0].supporting_paper_ids.slice(0, 2).map((pid) => (
              <Badge key={pid} variant="outline" className="text-[9px]">
                {pid.slice(-6)}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
