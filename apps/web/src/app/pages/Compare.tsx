/**
 * Compare Page — Phase 4 Multi-paper Research
 *
 * Main workbench for comparing 2-10 papers across evidence-backed dimensions.
 *
 * Layout:
 *   - Left: paper selector (2-10 papers) + dimension toggles
 *   - Center: compare matrix table with evidence-backed cells
 *   - Bottom: cross-paper insights + save to Notes actions
 */

import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import type {
  AnswerContractDto,
  CompareCellDto,
  CompareMatrixDto,
  EvidenceBlockDto,
} from '@scholar-ai/types';
import {
  ALLOWED_COMPARE_DIMENSIONS,
  DIMENSION_LABELS,
  compareV4,
} from '@/services/compareApi';
import type { CompareDimensionId } from '@/services/compareApi';
import * as notesApi from '@/services/notesApi';
import * as papersApi from '@/services/papersApi';
import { useEvidenceNavigation } from '@/features/chat/hooks/useEvidenceNavigation';
import { navigateToChatWithHandoff } from '@/features/chat/chatHandoff';
import { Button } from '../components/ui/button';
import { ScrollArea } from '../components/ui/scroll-area';
import { Badge } from '../components/ui/badge';
import { useLanguage } from '../contexts/LanguageContext';
import { toast } from 'sonner';
import {
  Loader2,
  Search,
  Plus,
  X,
  ArrowRight,
  BookOpen,
  Save,
} from 'lucide-react';
import type { Paper } from '@/types';
import { useAuth } from '@/contexts/AuthContext';

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

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
      <td className="border border-border/40 px-3 py-2 text-center text-sm text-muted-foreground/60 italic">
        –
      </td>
    );
  }

  const block = cell.evidence_blocks[0];
  return (
    <td className="border border-border/40 px-3 py-2 align-top">
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

function CompareMatrixTable({ matrix, onJumpEvidence, onSaveEvidence, onContinueInChat }: CompareMatrixTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-collapse text-sm">
        <thead>
          <tr className="bg-muted/40">
            <th className="border border-border/40 px-3 py-2 text-left font-semibold text-foreground/80 min-w-[160px]">
              论文
            </th>
            {matrix.dimensions.map((dim) => (
              <th
                key={dim.id}
                className="border border-border/40 px-3 py-2 text-left font-semibold text-foreground/80 min-w-[140px]"
              >
                {dim.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.rows.map((row) => (
            <tr key={row.paper_id} className="hover:bg-muted/20">
              <td className="border border-border/40 px-3 py-2 align-top">
                <div className="font-medium text-foreground text-sm">{row.title}</div>
                {row.year ? (
                  <div className="text-xs text-muted-foreground">{row.year}</div>
                ) : null}
              </td>
              {row.cells.map((cell) => (
                <CompareCellView
                  key={cell.dimension_id}
                  cell={cell}
                  onJumpEvidence={onJumpEvidence}
                  onSaveEvidence={(c) => onSaveEvidence?.(c, row.paper_id)}
                  onContinueInChat={(c) => onContinueInChat?.(c, row.paper_id)}
                />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Paper selector helpers
// ---------------------------------------------------------------------------

function PaperChip({
  paper,
  onRemove,
}: {
  paper: Paper;
  onRemove: () => void;
}) {
  return (
    <div className="flex items-center gap-1 rounded-full border border-border/60 bg-background px-2 py-1 text-sm">
      <span className="max-w-[200px] truncate">{paper.title}</span>
      <button type="button" onClick={onRemove} className="ml-1 text-muted-foreground hover:text-foreground">
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}

function isEvidenceReadyPaper(paper: Paper): boolean {
  if (typeof paper.evidenceReady === 'boolean') {
    return paper.evidenceReady;
  }
  return (paper.chunkCount ?? 0) >= 2;
}

function makeParagraph(text: string) {
  return {
    type: 'paragraph',
    content: [
      {
        type: 'text',
        text,
      },
    ],
  };
}

type CompareHandoffEvidenceRow = {
  handoffId: string;
  origin: 'cell' | 'insight';
  paperId: string;
  sourceChunkId?: string;
  pageNum?: number;
  claim?: string;
  dimensionId?: string;
  sectionPath?: string;
  contentType?: string;
  text?: string;
  citationJumpUrl?: string;
  title?: string;
};

function buildCompareHandoffId(params: {
  paperId: string;
  dimensionId?: string;
  sourceChunkId?: string;
  claim?: string;
}) {
  const paperId = params.paperId || 'paper';
  const dimensionId = params.dimensionId || 'compare';
  const sourceChunkId = params.sourceChunkId || 'no-source';
  const claimSeed = (params.claim || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .slice(0, 96);
  return `${paperId}::${dimensionId}::${sourceChunkId}::${claimSeed}`;
}

function buildCompareContentDoc(params: {
  isZh: boolean;
  question: string;
  matrix: CompareMatrixDto;
  selectedPapers: Paper[];
}) {
  const { isZh, question, matrix, selectedPapers } = params;
  const content: Array<Record<string, unknown>> = [
    makeParagraph(
      isZh
        ? `对比了 ${matrix.paper_ids.length} 篇论文，覆盖 ${matrix.dimensions.length} 个维度。`
        : `Compared ${matrix.paper_ids.length} papers across ${matrix.dimensions.length} dimensions.`,
    ),
  ];

  if (question.trim()) {
    content.push(
      makeParagraph(
        isZh ? `研究问题：${question.trim()}` : `Research question: ${question.trim()}`,
      ),
    );
  }

  content.push(
    makeParagraph(
      isZh
        ? `论文：${selectedPapers.map((paper) => paper.title).join(' / ')}`
        : `Papers: ${selectedPapers.map((paper) => paper.title).join(' / ')}`,
    ),
  );

  if (matrix.summary?.trim()) {
    content.push(
      makeParagraph(
        isZh ? `总结：${matrix.summary.trim()}` : `Summary: ${matrix.summary.trim()}`,
      ),
    );
  }

  for (const row of matrix.rows) {
    content.push(
      makeParagraph(
        row.year
          ? `${row.title} (${row.year})`
          : row.title,
      ),
    );
    for (const cell of row.cells) {
      const dimension = matrix.dimensions.find((item) => item.id === cell.dimension_id);
      const label = dimension?.label || cell.dimension_id;
      const detail = cell.content?.trim()
        || (isZh ? '证据不足' : 'Not enough evidence');
      content.push(
        makeParagraph(`${label}: ${detail}`),
      );
    }
  }

  if (matrix.cross_paper_insights.length > 0) {
    content.push(
      makeParagraph(isZh ? '跨论文洞察：' : 'Cross-paper insights:'),
    );
    for (const insight of matrix.cross_paper_insights) {
      content.push(makeParagraph(`- ${insight.claim}`));
    }
  }

  return {
    type: 'doc' as const,
    content,
  };
}

// ---------------------------------------------------------------------------
// Main Compare page
// ---------------------------------------------------------------------------

export function Compare() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const { isAuthenticated, loading: authLoading } = useAuth();

  // --- paper selection state
  const [selectedPapers, setSelectedPapers] = useState<Paper[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Paper[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);

  // --- dimension selection state
  const [enabledDims, setEnabledDims] = useState<Set<CompareDimensionId>>(
    new Set(ALLOWED_COMPARE_DIMENSIONS),
  );

  // --- compare result state
  const [question, setQuestion] = useState('');
  const [compareResult, setCompareResult] = useState<
    (AnswerContractDto & { compare_matrix: CompareMatrixDto }) | null
  >(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);
  const [selectionNotice, setSelectionNotice] = useState<string | null>(null);
  const hasHydratedSelectionFromUrlRef = useRef(false);

  // --- evidence navigation
  const { jumpToSource, saveEvidence } = useEvidenceNavigation(isZh);

  useEffect(() => {
    let cancelled = false;

    const loadSelectedPapers = async () => {
      if (authLoading || !isAuthenticated) {
        return;
      }

      const paperIds = (searchParams.get('paper_ids') || searchParams.get('paperIds') || '')
        .split(',')
        .map((id) => id.trim())
        .filter(Boolean);

      if (paperIds.length === 0) {
        hasHydratedSelectionFromUrlRef.current = true;
        return;
      }

      try {
        const results = await Promise.allSettled(
          paperIds.map((paperId) => papersApi.get(paperId)),
        );

        if (cancelled) {
          return;
        }

        const papers = results
          .filter((result): result is PromiseFulfilledResult<Paper> => result.status === 'fulfilled')
          .map((result) => result.value);

        if (papers.length > 0) {
          const readyPapers = papers.filter((paper) => isEvidenceReadyPaper(paper));
          const unavailablePapers = papers.filter((paper) => !isEvidenceReadyPaper(paper));
          setSelectedPapers((current) => {
            const currentIds = current.map((paper) => paper.id);
            const nextIds = readyPapers.map((paper) => paper.id);
            return JSON.stringify(currentIds) === JSON.stringify(nextIds) ? current : readyPapers;
          });
          if (readyPapers.length !== papers.length) {
            const notice = unavailablePapers[0]?.title
              ? (isZh ? `《${unavailablePapers[0].title}》尚未完成证据索引，已从对比集中移除。` : `"${unavailablePapers[0].title}" is not evidence-ready and was removed from the comparison set.`)
              : (isZh ? '部分论文尚未完成证据索引，已从对比集中移除。' : 'Some papers were removed because evidence indexing is incomplete.');
            setSelectionNotice(notice);
            toast.warning(
              notice,
            );
          } else {
            setSelectionNotice(null);
          }
        }
        hasHydratedSelectionFromUrlRef.current = true;

        if (papers.length !== paperIds.length) {
          toast.warning(isZh ? '部分论文加载失败' : 'Some papers could not be loaded');
        }
      } catch {
        if (!cancelled) {
          hasHydratedSelectionFromUrlRef.current = true;
          toast.error(isZh ? '加载对比论文失败' : 'Failed to load comparison papers');
        }
      }
    };

    void loadSelectedPapers();

    return () => {
      cancelled = true;
    };
  }, [authLoading, isAuthenticated, isZh, searchParams]);

  // ---- Handlers ------------------------------------------------------------

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) return;
    setSearchLoading(true);
    try {
      const response = await papersApi.search(searchQuery.trim(), {
        page: 1,
        limit: 10,
      });
      setSearchResults(
        response.data.papers.filter((paper) => !selectedPapers.some((selected) => selected.id === paper.id)),
      );
    } catch {
      toast.error(isZh ? '搜索论文失败' : 'Failed to search papers');
    } finally {
      setSearchLoading(false);
    }
  }, [searchQuery, selectedPapers, isZh]);

  const handleAddPaper = useCallback(
    (paper: Paper) => {
      if (selectedPapers.length >= 10) {
        toast.warning(isZh ? '最多选 10 篇论文' : 'Maximum 10 papers');
        return;
      }
      if (!isEvidenceReadyPaper(paper)) {
        const notice = paper.evidenceMessage
          || (isZh ? '这篇论文尚未完成证据索引，暂不能用于对比。' : 'This paper is not evidence-ready for comparison yet.');
        setSelectionNotice(notice);
        toast.warning(notice);
        return;
      }
      setSelectionNotice(null);
      setSelectedPapers((prev) => [...prev, paper]);
      setSearchResults((prev) => prev.filter((p) => p.id !== paper.id));
    },
    [selectedPapers, isZh],
  );

  const handleRemovePaper = useCallback((paperId: string) => {
    setSelectedPapers((prev) => prev.filter((p) => p.id !== paperId));
  }, []);

  useEffect(() => {
    if (!hasHydratedSelectionFromUrlRef.current) {
      return;
    }

    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('paperIds');
    if (selectedPapers.length > 0) {
      nextParams.set('paper_ids', selectedPapers.map((paper) => paper.id).join(','));
    } else {
      nextParams.delete('paper_ids');
    }

    const currentSerialized = searchParams.toString();
    const nextSerialized = nextParams.toString();
    if (currentSerialized !== nextSerialized) {
      navigate({ search: nextSerialized ? `?${nextSerialized}` : '' }, { replace: true });
    }
  }, [navigate, searchParams, selectedPapers]);

  const handleToggleDim = useCallback((dimId: CompareDimensionId) => {
    setEnabledDims((prev) => {
      const next = new Set(prev);
      if (next.has(dimId)) {
        if (next.size <= 1) return prev; // always keep at least 1
        next.delete(dimId);
      } else {
        next.add(dimId);
      }
      return next;
    });
  }, []);

  const handleCompare = useCallback(async () => {
    if (selectedPapers.length < 2) {
      toast.warning(isZh ? '请至少选择 2 篇论文' : 'Please select at least 2 papers');
      return;
    }
    setCompareLoading(true);
    setCompareError(null);
    setCompareResult(null);
    try {
      const result = await compareV4({
        paper_ids: selectedPapers.map((p) => p.id),
        dimensions: [...enabledDims] as CompareDimensionId[],
        question: question.trim() || undefined,
      });
      setCompareResult(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setCompareError(msg);
      toast.error(isZh ? '对比失败' : 'Compare failed');
    } finally {
      setCompareLoading(false);
    }
  }, [selectedPapers, enabledDims, question, isZh]);

  const handleJumpEvidence = useCallback(
    (block: EvidenceBlockDto) => {
      void jumpToSource(
        block.source_chunk_id,
        block.paper_id,
        block.page_num ?? undefined,
      );
    },
    [jumpToSource],
  );

  const handleSaveCellEvidence = useCallback(
    async (cell: CompareCellDto, _paperId: string) => {
      const block = cell.evidence_blocks[0];
      if (!block) return;
      try {
        await saveEvidence(cell.content || cell.dimension_id, {
          ...block,
          text: block.text || cell.content || cell.dimension_id,
          citation_jump_url: block.citation_jump_url || '',
        }, {
          surface: 'compare',
        });
        toast.success(isZh ? '证据已保存到笔记' : 'Evidence saved to Notes');
      } catch {
        toast.error(isZh ? '保存失败' : 'Save failed');
      }
    },
    [isZh, saveEvidence],
  );

  const handleSaveWholeCompare = useCallback(async () => {
    if (!compareResult?.compare_matrix) return;
    const matrix = compareResult.compare_matrix;

    // Collect all deduped evidence blocks
    const seen = new Set<string>();
    const allBlocks: EvidenceBlockDto[] = [];
    for (const row of matrix.rows) {
      for (const cell of row.cells) {
        for (const block of cell.evidence_blocks) {
          if (!seen.has(block.evidence_id)) {
            seen.add(block.evidence_id);
            allBlocks.push(block);
          }
        }
      }
    }

    const title = `Compare: ${selectedPapers.map((p) => p.title).join(' vs ')}`;
    const contentDoc = buildCompareContentDoc({
      isZh,
      question,
      matrix,
      selectedPapers,
    });

    try {
      await notesApi.createNote({
        title,
        contentDoc,
        linkedEvidence: allBlocks,
        sourceType: 'compare',
        paperIds: selectedPapers.map((p) => p.id),
      });
      toast.success(isZh ? '对比结果已保存到笔记' : 'Compare result saved to Notes');
    } catch {
      toast.error(isZh ? '保存失败' : 'Save failed');
    }
  }, [compareResult, isZh, question, selectedPapers]);

  const paperTitleById = useMemo(
    () => new Map(selectedPapers.map((paper) => [paper.id, paper.title])),
    [selectedPapers],
  );

  const handleContinueCellInChat = useCallback(
    (cell: CompareCellDto, paperId: string) => {
      const dimensionLabel = DIMENSION_LABELS[cell.dimension_id as CompareDimensionId] || cell.dimension_id;
      navigateToChatWithHandoff(
        navigate,
        {
          paperIds: selectedPapers.map((paper) => paper.id),
        },
        {
          origin: 'compare',
          promptDraft: isZh
            ? `继续分析对比维度“${dimensionLabel}”，重点解释《${selectedPapers.find((paper) => paper.id === paperId)?.title || '这篇论文'}》在该维度上的证据、结论和局限。`
            : `Continue the comparison on "${dimensionLabel}" and explain the evidence, conclusion, and limitation for "${selectedPapers.find((paper) => paper.id === paperId)?.title || 'this paper'}".`,
          evidence: cell.evidence_blocks.slice(0, 2).map((block) => ({
            handoffId: buildCompareHandoffId({
              paperId: block.paper_id,
              dimensionId: cell.dimension_id,
              sourceChunkId: block.source_chunk_id,
              claim: cell.content,
            }),
            paperId: block.paper_id,
            sourceChunkId: block.source_chunk_id,
            pageNum: block.page_num ?? undefined,
            claim: cell.content,
            dimensionId: cell.dimension_id,
            sectionPath: block.section_path ?? undefined,
            contentType: block.content_type,
            text: block.text,
            citationJumpUrl: block.citation_jump_url,
            title: paperTitleById.get(block.paper_id),
          })),
          returnTo: `/compare?paper_ids=${selectedPapers.map((paper) => paper.id).join(',')}`,
        },
      );
    },
    [isZh, navigate, paperTitleById, selectedPapers],
  );

  const handleOpenChat = useCallback(() => {
    const topEvidence = compareResult?.compare_matrix
      ? (() => {
          const seen = new Set<string>();
          const orderedRows: CompareHandoffEvidenceRow[] = [];
          const byPaper = new Map<string, CompareHandoffEvidenceRow[]>();

          const collect = (row: CompareHandoffEvidenceRow) => {
            if (!row.handoffId || seen.has(row.handoffId)) {
              return;
            }
            seen.add(row.handoffId);
            orderedRows.push(row);
            const paperRows = byPaper.get(row.paperId) || [];
            paperRows.push(row);
            byPaper.set(row.paperId, paperRows);
          };

          for (const insight of compareResult.compare_matrix.cross_paper_insights) {
            for (const block of insight.evidence_blocks) {
              collect({
                handoffId: buildCompareHandoffId({
                  paperId: block.paper_id,
                  dimensionId: 'cross_paper_insight',
                  sourceChunkId: block.source_chunk_id,
                  claim: insight.claim,
                }),
                origin: 'insight',
                paperId: block.paper_id,
                sourceChunkId: block.source_chunk_id,
                pageNum: block.page_num ?? undefined,
                claim: insight.claim,
                dimensionId: 'cross_paper_insight',
                sectionPath: block.section_path ?? undefined,
                contentType: block.content_type,
                text: block.text,
                citationJumpUrl: block.citation_jump_url,
                title: paperTitleById.get(block.paper_id),
              });
            }
          }

          for (const row of compareResult.compare_matrix.rows) {
            for (const cell of row.cells) {
              for (const block of cell.evidence_blocks) {
                collect({
                  handoffId: buildCompareHandoffId({
                    paperId: row.paper_id,
                    dimensionId: cell.dimension_id,
                    sourceChunkId: block.source_chunk_id,
                    claim: cell.content,
                  }),
                  origin: 'cell',
                  paperId: row.paper_id,
                  sourceChunkId: block.source_chunk_id,
                  pageNum: block.page_num ?? undefined,
                  claim: cell.content,
                  dimensionId: cell.dimension_id,
                  sectionPath: block.section_path ?? undefined,
                  contentType: block.content_type,
                  text: block.text,
                  citationJumpUrl: block.citation_jump_url,
                  title: paperTitleById.get(row.paper_id),
                });
              }
            }
          }

          const balanced: CompareHandoffEvidenceRow[] = [];
          const balancedSeen = new Set<string>();
          const paperIds = selectedPapers.map((paper) => paper.id);

          for (const paperId of paperIds) {
            const paperRows = byPaper.get(paperId) || [];
            const preferredRows = [
              ...paperRows.filter((row) => row.origin === 'cell'),
              ...paperRows.filter((row) => row.origin === 'insight'),
            ];
            const usedSourceChunks = new Set<string>();

            for (const row of preferredRows) {
              if (balanced.length >= 6) {
                break;
              }
              if (balancedSeen.has(row.handoffId)) {
                continue;
              }
              const sourceChunkKey = row.sourceChunkId || `no-source:${row.handoffId}`;
              if (usedSourceChunks.has(sourceChunkKey) && row.origin !== 'cell') {
                continue;
              }
              balanced.push(row);
              balancedSeen.add(row.handoffId);
              usedSourceChunks.add(sourceChunkKey);
              if (usedSourceChunks.size >= 2) {
                break;
              }
            }
          }

          for (const row of orderedRows) {
            if (balanced.length >= 6) {
              break;
            }
            if (balancedSeen.has(row.handoffId)) {
              continue;
            }
            balanced.push(row);
            balancedSeen.add(row.handoffId);
          }

          return balanced.slice(0, 6);
        })()
      : [];

    navigateToChatWithHandoff(
      navigate,
      { paperIds: selectedPapers.map((paper) => paper.id) },
      {
        origin: 'compare',
        promptDraft: isZh
          ? `基于这组论文对比，继续分析${question.trim() ? `“${question.trim()}”` : '核心差异、共同点和下一步研究问题'}。`
          : `Using this comparison set, continue analyzing ${question.trim() ? `"${question.trim()}"` : 'the major differences, common ground, and next research questions'}.`,
        evidence: topEvidence.length > 0
          ? topEvidence.map((row) => ({
              handoffId: row.handoffId,
              paperId: row.paperId,
              sourceChunkId: row.sourceChunkId,
              pageNum: row.pageNum,
              claim: row.claim || question.trim() || undefined,
              dimensionId: row.dimensionId,
              sectionPath: row.sectionPath,
              contentType: row.contentType,
              text: row.text,
              citationJumpUrl: row.citationJumpUrl,
              title: row.title,
            }))
          : selectedPapers.map((paper) => ({
              paperId: paper.id,
              title: paper.title,
            })),
        returnTo: `/compare?paper_ids=${selectedPapers.map((paper) => paper.id).join(',')}`,
      },
    );
  }, [compareResult, isZh, navigate, paperTitleById, question, selectedPapers]);

  // ---- Render --------------------------------------------------------------

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold font-serif tracking-tight">{isZh ? '多论文对比' : 'Compare Papers'}</h1>
        {selectedPapers.length >= 2 && compareResult ? (
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleOpenChat}>
              <ArrowRight className="mr-1.5 h-4 w-4" />
              {isZh ? '继续追问' : 'Continue in Chat'}
            </Button>
            <Button variant="outline" size="sm" onClick={handleSaveWholeCompare}>
              <Save className="mr-1.5 h-4 w-4" />
              {isZh ? '保存到笔记' : 'Save to Notes'}
            </Button>
          </div>
        ) : null}
      </div>

      <div className="flex flex-1 gap-4 overflow-hidden">
        {/* Left panel: paper selector + dimensions */}
        <aside className="flex w-72 flex-shrink-0 flex-col gap-4">
          {/* Paper search */}
          <div className="rounded-2xl border border-border/60 bg-card p-3">
            <h3 className="mb-2 text-sm font-semibold font-serif tracking-tight">
              {isZh ? '选择论文' : 'Select Papers'}
              <span className="ml-1 text-xs text-muted-foreground">
                ({selectedPapers.length}/10)
              </span>
            </h3>
            {selectionNotice ? (
              <p className="mb-2 rounded-lg border border-amber-300/60 bg-amber-50 px-2 py-1.5 text-[11px] text-amber-900">
                {selectionNotice}
              </p>
            ) : null}
            <div className="flex gap-1">
              <input
                name="paperSearch"
                type="text"
                className="flex-1 rounded-lg border border-border/60 bg-background px-2 py-1 text-sm outline-none focus:border-primary/50"
                placeholder={isZh ? '搜索论文…' : 'Search papers…'}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && void handleSearch()}
              />
              <Button size="sm" variant="outline" onClick={() => void handleSearch()} disabled={searchLoading}>
                <span className="sr-only">{isZh ? '搜索论文' : 'Search papers'}</span>
                {searchLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              </Button>
            </div>
            {/* Search results */}
            {searchResults.length > 0 ? (
              <ul className="mt-2 space-y-1">
                {searchResults.map((paper) => (
                  <li key={paper.id}>
                    <button
                      type="button"
                      className="flex w-full items-start gap-1 rounded-lg px-2 py-1 text-left text-sm hover:bg-muted/40"
                      onClick={() => handleAddPaper(paper)}
                    >
                      <Plus className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
                      <span className="line-clamp-2">{paper.title}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
            {/* Selected papers */}
            {selectedPapers.length > 0 ? (
              <div className="mt-2 flex flex-wrap gap-1">
                {selectedPapers.map((p) => (
                  <PaperChip key={p.id} paper={p} onRemove={() => handleRemovePaper(p.id)} />
                ))}
              </div>
            ) : null}
          </div>

          {/* Dimension toggles */}
          <div className="rounded-2xl border border-border/60 bg-card p-3">
            <h3 className="mb-2 text-sm font-semibold font-serif tracking-tight">{isZh ? '对比维度' : 'Dimensions'}</h3>
            <div className="flex flex-wrap gap-1.5">
              {ALLOWED_COMPARE_DIMENSIONS.map((dimId) => (
                <button
                  key={dimId}
                  type="button"
                  onClick={() => handleToggleDim(dimId)}
                  className={`rounded-full border px-2 py-0.5 text-xs transition-colors ${
                    enabledDims.has(dimId)
                      ? 'border-primary/40 bg-primary/10 text-primary'
                      : 'border-border/50 text-muted-foreground'
                  }`}
                >
                  {DIMENSION_LABELS[dimId]}
                </button>
              ))}
            </div>
          </div>

          {/* Optional research question */}
          <div className="rounded-2xl border border-border/60 bg-card p-3">
            <h3 className="mb-2 text-sm font-semibold font-serif tracking-tight">{isZh ? '研究问题（可选）' : 'Research Question (optional)'}</h3>
            <textarea
              name="researchQuestion"
              className="w-full resize-none rounded-lg border border-border/60 bg-background px-2 py-1.5 text-sm outline-none focus:border-primary/50"
              rows={3}
              placeholder={isZh ? '输入研究问题，引导检索…' : 'Type a question to guide retrieval…'}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
          </div>

          <Button
            className="w-full"
            onClick={() => void handleCompare()}
            disabled={selectedPapers.length < 2 || compareLoading}
          >
            {compareLoading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <BookOpen className="mr-2 h-4 w-4" />
            )}
            {isZh ? '生成对比表' : 'Generate Compare Table'}
          </Button>
        </aside>

        {/* Main area: compare matrix */}
        <ScrollArea className="flex-1 rounded-2xl border border-border/60 bg-card p-3">
          {compareLoading ? (
            <div className="flex h-64 items-center justify-center gap-2 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>{isZh ? '正在检索并构建对比表…' : 'Retrieving evidence and building table…'}</span>
            </div>
          ) : compareError ? (
            <div className="flex h-64 items-center justify-center text-destructive">
              {compareError}
            </div>
          ) : compareResult?.compare_matrix ? (
            <div className="space-y-6">
            <CompareMatrixTable
              matrix={compareResult.compare_matrix}
              onJumpEvidence={handleJumpEvidence}
              onSaveEvidence={handleSaveCellEvidence}
              onContinueInChat={handleContinueCellInChat}
            />
              {compareResult.compare_matrix.cross_paper_insights.length > 0 ? (
                <section>
                  <h3 className="mb-2 text-sm font-semibold text-foreground font-serif tracking-tight">
                    {isZh ? '跨论文洞察' : 'Cross-paper Insights'}
                  </h3>
                  <div className="space-y-2">
                    {compareResult.compare_matrix.cross_paper_insights.map((insight, i) => (
                      <div
                        key={i}
                        className="rounded-xl border border-border/50 bg-background px-3 py-2"
                      >
                        <p className="text-sm text-foreground/90">{insight.claim}</p>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {insight.supporting_paper_ids.map((pid) => (
                            <Badge key={pid} variant="outline" className="text-[10px]">
                              {paperTitleById.get(pid) || pid}
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
                {isZh
                  ? '选择 2-10 篇论文，点击「生成对比表」'
                  : 'Select 2–10 papers and click "Generate Compare Table"'}
              </p>
            </div>
          )}
        </ScrollArea>
      </div>
    </div>
  );
}
