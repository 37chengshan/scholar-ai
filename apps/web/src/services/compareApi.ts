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
  problem: 'Research Problem',
  method: 'Method',
  dataset: 'Dataset',
  metrics: 'Metrics',
  results: 'Results',
  limitations: 'Limitations',
  innovation: 'Key Innovation',
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
