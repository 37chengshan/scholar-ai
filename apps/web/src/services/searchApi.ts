/**
 * Search API Service
 *
 * Search API calls:
 * - unified(): Unified search (internal + external sources)
 * - external(): Search external sources (arXiv, Semantic Scholar)
 * - autocomplete(): Paper title autocomplete (Phase 23)
 * - searchAuthors(): Search authors by name (Phase 23)
 * - getAuthorPapers(): Get papers by author ID (Phase 23)
 *
 * All endpoints require authentication.
 */

import apiClient from '@/utils/apiClient';

// ============================================================
// Types for Phase 23: Autocomplete and Author Search
// ============================================================

export interface AutocompletePaper {
  paperId: string;
  title: string;
  year?: number;
  authors?: Array<{
    authorId: string;
    name: string;
  }>;
}

export interface AuthorSearchResult {
  authorId: string;
  name: string;
  hIndex?: number;
  citationCount?: number;
  paperCount?: number;
}

export interface AuthorPaper {
  paperId: string;
  title: string;
  year?: number;
  citationCount?: number;
}

// ============================================================
// Phase 23: Autocomplete and Author Search APIs
// ============================================================

/**
 * Get paper autocomplete suggestions
 *
 * GET /api/v1/search/autocomplete
 * Per D-03: Default limit 5
 * Per D-04: Results cached by backend (1h TTL)
 *
 * @param query - Search query string
 * @param limit - Maximum results (default: 5)
 * @returns List of autocomplete suggestions
 */
export async function autocomplete(
  query: string,
  limit: number = 5
): Promise<AutocompletePaper[]> {
  const response = await apiClient.get<AutocompletePaper[]>('/api/v1/semantic-scholar/autocomplete', {
    params: { query, limit },
  });

  return response.data || [];
}

/**
 * Search authors by name
 *
 * GET /api/v1/search/author
 * Per D-05: Called from Author tab
 * Per D-06: Returns hIndex, citationCount, paperCount
 * Per D-12: Results cached by backend (24h TTL)
 *
 * @param query - Author name query
 * @param limit - Maximum results (default: 10)
 * @param offset - Pagination offset (default: 0)
 * @returns Author search results
 */
export async function searchAuthors(
  query: string,
  limit: number = 10,
  offset: number = 0
): Promise<{ data: AuthorSearchResult[]; total?: number }> {
  const response = await apiClient.get<{ data?: AuthorSearchResult[]; total?: number }>('/api/v1/semantic-scholar/author/search', {
    params: { query, limit, offset },
  });

  return {
    data: response.data?.data || [],
    total: response.data?.total,
  };
}

/**
 * Get papers by author ID
 *
 * GET /api/v1/search/author/:authorId/papers
 * Per D-07: Pagination 10 per page
 * Per D-12: Results cached by backend (7d TTL)
 *
 * @param authorId - Semantic Scholar author ID
 * @param limit - Maximum results (default: 10)
 * @param offset - Pagination offset (default: 0)
 * @returns Author's papers with pagination
 */
export async function getAuthorPapers(
  authorId: string,
  limit: number = 10,
  offset: number = 0
): Promise<{ data: AuthorPaper[]; next?: number }> {
  const response = await apiClient.get<{ data?: AuthorPaper[]; next?: number }>(`/api/v1/semantic-scholar/author/${authorId}/papers`, {
    params: { limit, offset },
  });

  return {
    data: response.data?.data || [],
    next: response.data?.next,
  };
}

// ============================================================
// Existing Search APIs
// ============================================================

/**
 * Unified search across internal library and external sources
 *
 * GET /api/v1/search/unified
 * Returns results from both internal papers and external sources (arXiv, S2)
 *
 * @param query - Search query string
 * @param limit - Maximum results per source (default: 20)
 * @param offset - Pagination offset (default: 0)
 * @param year_from - Filter by year (optional)
 * @param year_to - Filter by year (optional)
 * @returns Unified search results
 */
export async function unified(
  query: string,
  limit: number = 20,
  offset: number = 0,
  year_from?: number,
  year_to?: number
): Promise<{
  query: string;
  results: Array<{
    id: string;
    title: string;
    authors?: string[];
    abstract?: string;
    year?: number;
    source: 'internal' | 'arxiv' | 's2';
    paperId?: string;
    externalId?: string;
    pdfUrl?: string;
    citations?: number;
  }>;
  total: number;
  filters: {
    year_from: number | null;
    year_to: number | null;
  };
}> {
  const params = new URLSearchParams();
  params.append('query', query);
  params.append('limit', limit.toString());
  params.append('offset', offset.toString());
  if (year_from) params.append('year_from', year_from.toString());
  if (year_to) params.append('year_to', year_to.toString());

  const response = await apiClient.get<{
    query: string;
    results: Array<{
      id: string;
      title: string;
      authors?: string[];
      abstract?: string;
      year?: number;
      source: 'internal' | 'arxiv' | 's2';
      paperId?: string;
      externalId?: string;
      pdfUrl?: string;
      citations?: number;
    }>;
    total: number;
    filters: {
      year_from: number | null;
      year_to: number | null;
    };
  }>(`/api/v1/search/unified?${params.toString()}`);

  return response.data;
}

/**
 * External paper import is handled by kbApi, not searchApi.
 *
 * Import workflow:
 * 1. Use searchApi.unified() to find external papers
 * 2. Use kbApi.importFromArxiv() or kbApi.importFromUrl() to import to a knowledge base
 *
 * See Search.tsx handleImportToKB() for complete implementation example.
 */
