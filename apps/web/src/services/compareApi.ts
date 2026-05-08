import apiClient from '@/utils/apiClient';
import type { AnswerContractDto, CompareMatrixDto } from '@scholar-ai/types';

// ---------------------------------------------------------------------------
// Request types
// ---------------------------------------------------------------------------

export const ALLOWED_COMPARE_DIMENSIONS = [
  'problem',
  'method',
  'dataset',
  'metrics',
  'results',
  'limitations',
  'innovation',
] as const;

export type CompareDimensionId = (typeof ALLOWED_COMPARE_DIMENSIONS)[number];

export const DIMENSION_LABELS: Record<CompareDimensionId, string> = {
  problem: '研究问题',
  method: '方法',
  dataset: '数据集',
  metrics: '指标',
  results: '结果',
  limitations: '局限性',
  innovation: '关键创新',
};

export interface CompareV4Request {
  paper_ids: string[];
  dimensions?: CompareDimensionId[];
  question?: string;
  knowledge_base_id?: string;
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

/**
 * POST /api/v1/compare/v4
 * Phase 4 evidence-backed multi-paper compare.
 */
export async function compareV4(
  req: CompareV4Request,
): Promise<AnswerContractDto & { compare_matrix: CompareMatrixDto }> {
  const response = await apiClient.post<AnswerContractDto & { compare_matrix: CompareMatrixDto }>(
    '/api/v1/compare/v4',
    req,
  );
  return response.data;
}
