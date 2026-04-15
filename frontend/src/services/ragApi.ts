/**
 * RAG Query API Service
 *
 * RAG (Retrieval-Augmented Generation) query API calls:
 * - query(): Submit query and get AI-generated answer with sources
 *
 * Note: SSE streaming will be implemented in Phase 15
 */

import apiClient from '@/utils/apiClient';
import type { QueryParams, QueryResult } from '@/types';

/**
 * Submit RAG query
 *
 * POST /api/v1/rag/query
 * Searches papers and generates AI answer with citations
 *
 * @param params - Query parameters
 * @returns Query result with answer and sources
 */
export async function query(params: QueryParams): Promise<QueryResult> {
  const response = await apiClient.post<QueryResult>('/api/v1/rag/query', {
    question: params.question,
    paper_ids: params.paper_ids,
    top_k: params.top_k || 10,
    query_type: params.query_type || 'single',
    conversation_id: params.conversation_id,
  });

  return response.data;
}

/**
 * Query single paper
 *
 * POST /api/v1/rag/query (with paperIds=[singleId])
 * Searches within a single paper
 *
 * @param paperId - Paper ID
 * @param query - Query string
 * @param topK - Number of results (default 5)
 * @returns Query result
 */
export async function queryPaper(
  paperId: string,
  queryText: string,
  topK?: number
): Promise<QueryResult> {
  return query({
    question: queryText,
    paper_ids: [paperId],
    top_k: topK || 10,
    query_type: 'single',
  });
}

/**
 * Cross-paper comparison query
 *
 * POST /api/v1/rag/query (with queryType='cross_paper')
 * Compares findings across multiple papers
 *
 * @param paperIds - Array of paper IDs
 * @param query - Comparison query
 * @returns Query result with cross-paper synthesis
 */
export async function crossPaperQuery(
  paperIds: string[],
  queryText: string
): Promise<QueryResult> {
  return query({
    question: queryText,
    paper_ids: paperIds,
    top_k: 10,
    query_type: 'cross_paper',
  });
}

/**
 * Research evolution query
 *
 * POST /api/v1/rag/query (with queryType='evolution')
 * Traces research evolution across papers
 *
 * @param query - Evolution query (e.g., "How has X evolved?")
 * @param paperIds - Optional specific papers (otherwise searches all)
 * @returns Query result with evolution timeline
 */
export async function evolutionQuery(
  queryText: string,
  paperIds?: string[]
): Promise<QueryResult> {
  return query({
    question: queryText,
    paper_ids: paperIds,
    top_k: 15,
    query_type: 'evolution',
  });
}