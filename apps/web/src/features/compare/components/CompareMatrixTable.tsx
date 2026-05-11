import type { CompareCellDto, CompareMatrixDto, EvidenceBlockDto } from '@scholar-ai/types';

function SupportBadge({ status }: { status: CompareCellDto['support_status'] }) {
  const colorMap: Record<string, string> = {
    supported: 'bg-emerald-500/10 text-emerald-700 border-emerald-500/20',
    partially_supported: 'bg-amber-500/10 text-amber-700 border-amber-500/20',
    unsupported: 'bg-red-500/10 text-red-700 border-red-500/20',
    not_enough_evidence: 'bg-muted/60 text-muted-foreground border-border/50',
  };
  const labelMap: Record<string, string> = {
    supported: '证据充分',
    partially_supported: '部分支撑',
    unsupported: '证据不足',
    not_enough_evidence: '–',
  };

  return (
    <span
      className={`inline-flex rounded-full border px-1.5 py-0.5 text-[10px] font-medium ${colorMap[status] ?? colorMap.not_enough_evidence}`}
    >
      {labelMap[status] ?? status}
    </span>
  );
}

interface CompareCellViewProps {
  cell: CompareCellDto;
  onJumpEvidence?: (block: EvidenceBlockDto) => void;
  onSaveEvidence?: (cell: CompareCellDto) => void;
  onContinueInChat?: (cell: CompareCellDto) => void;
}

function CompareCellView({ cell, onJumpEvidence, onSaveEvidence, onContinueInChat }: CompareCellViewProps) {
  if (cell.support_status === 'not_enough_evidence') {
    return (
      <td className="border border-border/40 px-3 py-2 text-center text-sm italic text-muted-foreground/60">
        –
      </td>
    );
  }

  const block = cell.evidence_blocks[0];
  return (
    <td className="align-top border border-border/40 px-3 py-2">
      <p className="text-sm leading-relaxed text-foreground/90">{cell.content}</p>
      <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
        <SupportBadge status={cell.support_status} />
        {block ? (
          <>
            <button
              type="button"
              className="rounded-full border border-border/60 px-2 py-0.5 text-[11px] text-foreground hover:border-primary/50 hover:text-primary"
              onClick={() => onJumpEvidence?.(block)}
            >
              p.{block.page_num ?? 1}
            </button>
            <button
              type="button"
              className="rounded-full border border-border/60 px-2 py-0.5 text-[11px] text-muted-foreground hover:border-primary/50 hover:text-primary"
              onClick={() => onSaveEvidence?.(cell)}
            >
              保存证据
            </button>
            <button
              type="button"
              className="rounded-full border border-border/60 px-2 py-0.5 text-[11px] text-muted-foreground hover:border-primary/50 hover:text-primary"
              onClick={() => onContinueInChat?.(cell)}
            >
              继续问
            </button>
          </>
        ) : null}
      </div>
    </td>
  );
}

interface CompareMatrixTableProps {
  matrix: CompareMatrixDto;
  onJumpEvidence?: (block: EvidenceBlockDto) => void;
  onSaveEvidence?: (cell: CompareCellDto, paperId: string) => void;
  onContinueInChat?: (cell: CompareCellDto, paperId: string) => void;
}

export function CompareMatrixTable({
  matrix,
  onJumpEvidence,
  onSaveEvidence,
  onContinueInChat,
}: CompareMatrixTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-collapse text-sm">
        <thead>
          <tr className="bg-muted/40">
            <th className="min-w-[160px] border border-border/40 px-3 py-2 text-left font-semibold text-foreground/80">
              论文
            </th>
            {matrix.dimensions.map((dim) => (
              <th
                key={dim.id}
                className="min-w-[140px] border border-border/40 px-3 py-2 text-left font-semibold text-foreground/80"
              >
                {dim.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.rows.map((row) => (
            <tr key={row.paper_id} className="hover:bg-muted/20">
              <td className="align-top border border-border/40 px-3 py-2">
                <div className="text-sm font-medium text-foreground">{row.title}</div>
                {row.year ? <div className="text-xs text-muted-foreground">{row.year}</div> : null}
              </td>
              {row.cells.map((cell) => (
                <CompareCellView
                  key={cell.dimension_id}
                  cell={cell}
                  onJumpEvidence={onJumpEvidence}
                  onSaveEvidence={(currentCell) => onSaveEvidence?.(currentCell, row.paper_id)}
                  onContinueInChat={(currentCell) => onContinueInChat?.(currentCell, row.paper_id)}
                />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
