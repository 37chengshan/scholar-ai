import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { toast } from 'sonner';

import type {
  AnswerContractDto,
  CompareCellDto,
  CompareMatrixDto,
  EvidenceBlockDto,
} from '@scholar-ai/types';

import { useAuth } from '@/contexts/AuthContext';
import { useEvidenceNavigation } from '@/features/chat/hooks/useEvidenceNavigation';
import { navigateToChatWithHandoff } from '@/features/chat/chatHandoff';
import {
  ALLOWED_COMPARE_DIMENSIONS,
  DIMENSION_LABELS,
  compareV4,
  type CompareDimensionId,
} from '@/services/compareApi';
import * as notesApi from '@/services/notesApi';
import * as papersApi from '@/services/papersApi';
import type { Paper } from '@/types';

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

export function useCompareWorkspace(isZh: boolean) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isAuthenticated, loading: authLoading } = useAuth();
  const { jumpToSource, saveEvidence } = useEvidenceNavigation(isZh);

  const [showInspector, setShowInspector] = useState(false);
  const [selectedPapers, setSelectedPapers] = useState<Paper[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Paper[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [enabledDims, setEnabledDims] = useState<Set<CompareDimensionId>>(
    new Set(ALLOWED_COMPARE_DIMENSIONS),
  );
  const [question, setQuestion] = useState('');
  const [compareResult, setCompareResult] = useState<
    (AnswerContractDto & { compare_matrix: CompareMatrixDto }) | null
  >(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);
  const [selectionNotice, setSelectionNotice] = useState<string | null>(null);
  const hasHydratedSelectionFromUrlRef = useRef(false);

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
            toast.warning(notice);
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

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) {
      return;
    }
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
      setSearchResults((prev) => prev.filter((candidate) => candidate.id !== paper.id));
    },
    [selectedPapers, isZh],
  );

  const handleRemovePaper = useCallback((paperId: string) => {
    setSelectedPapers((prev) => prev.filter((paper) => paper.id !== paperId));
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
        if (next.size <= 1) {
          return prev;
        }
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
        paper_ids: selectedPapers.map((paper) => paper.id),
        dimensions: [...enabledDims] as CompareDimensionId[],
        question: question.trim() || undefined,
      });
      setCompareResult(result);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setCompareError(message);
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
      if (!block) {
        return;
      }
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
    if (!compareResult?.compare_matrix) {
      return;
    }
    const matrix = compareResult.compare_matrix;

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

    const title = `Compare: ${selectedPapers.map((paper) => paper.title).join(' vs ')}`;
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
        paperIds: selectedPapers.map((paper) => paper.id),
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

  const insightCount = compareResult?.compare_matrix.cross_paper_insights.length ?? 0;
  const evidenceCount = compareResult?.compare_matrix.rows.reduce(
    (count, row) => count + row.cells.reduce((cellCount, cell) => cellCount + cell.evidence_blocks.length, 0),
    0,
  ) ?? 0;

  return {
    showInspector,
    selectedPapers,
    searchQuery,
    searchResults,
    searchLoading,
    enabledDims,
    question,
    compareResult,
    compareLoading,
    compareError,
    selectionNotice,
    insightCount,
    evidenceCount,
    setShowInspector,
    setSearchQuery,
    setQuestion,
    handleSearch,
    handleAddPaper,
    handleRemovePaper,
    handleToggleDim,
    handleCompare,
    handleJumpEvidence,
    handleSaveCellEvidence,
    handleSaveWholeCompare,
    handleContinueCellInChat,
    handleOpenChat,
  };
}
