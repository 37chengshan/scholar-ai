/**
 * CompareCard – Chat 中 response_type=compare 的轻量对比表渲染
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
      className={`inline-block h-2 w-2 rounded-full ${colorMap[status] ?? colorMap.not_enough_evidence}`}
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
    <div className="mt-2 rounded-2xl border border-border/60 bg-background/80 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold text-foreground/70">
          {isZh ? `多论文对比 (${matrix.paper_ids.length} 篇)` : `Compare (${matrix.paper_ids.length} papers)`}
        </span>
        <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={handleOpenWorkbench}>
          {isZh ? '在工作台查看完整表格' : 'View full table'}
          <ArrowRight className="ml-1 h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Compact table */}
      <div className="overflow-x-auto">
        <table className="min-w-full text-[12px]">
          <thead>
            <tr className="border-b border-border/40">
              <th className="pr-3 pb-1 text-left font-medium text-muted-foreground">
                {isZh ? '论文' : 'Paper'}
              </th>
              {visibleDims.map((d) => (
                <th key={d.id} className="pr-3 pb-1 text-left font-medium text-muted-foreground">
                  {d.label}
                </th>
              ))}
              {hiddenCount > 0 ? (
                <th className="pb-1 text-left font-medium text-muted-foreground/50">
                  +{hiddenCount}
                </th>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {matrix.rows.map((row) => (
              <tr key={row.paper_id} className="border-b border-border/30 last:border-0">
                <td className="max-w-[120px] truncate pr-3 py-1.5 font-medium text-foreground">
                  {row.title}
                </td>
                {visibleDims.map((d) => {
                  const cell = row.cells.find((c) => c.dimension_id === d.id);
                  if (!cell || cell.support_status === 'not_enough_evidence') {
                    return (
                      <td key={d.id} className="pr-3 py-1.5 text-muted-foreground/40">
                        –
                      </td>
                    );
                  }
                  const block = cell.evidence_blocks[0];
                  return (
                    <td key={d.id} className="max-w-[180px] pr-3 py-1.5">
                      <div className="flex items-start gap-1">
                        <SupportDot status={cell.support_status} />
                        <span className="line-clamp-2 text-foreground/90">{cell.content}</span>
                      </div>
                      {block ? (
                        <button
                          type="button"
                          className="mt-0.5 text-[10px] text-muted-foreground underline-offset-2 hover:text-primary hover:underline"
                          onClick={() => handleJump(block)}
                        >
                          p.{block.page_num ?? 1}
                        </button>
                      ) : null}
                    </td>
                  );
                })}
                {hiddenCount > 0 ? <td className="py-1.5" /> : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Cross-paper insights preview */}
      {matrix.cross_paper_insights.length > 0 ? (
        <div className="mt-2 flex items-start gap-1.5 rounded-xl border border-border/40 bg-muted/30 px-2.5 py-2 text-xs">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
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
