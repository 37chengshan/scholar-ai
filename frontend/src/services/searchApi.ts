/**
 * Search API Service
 *
 * Search API calls:
 * - unified(): Unified search (internal + external sources)
 * - external(): Search external sources (arXiv, Semantic Scholar)
 *
 * All endpoints require authentication.
 */

import apiClient from '@/utils/apiClient';

/**
 * Unified search across internal library and external sources
 *
 * GET /api/search/unified
 * Returns results from both internal papers and external sources (arXiv, S2)
 *
 * @param query - Search query string
 * @param limit - Maximum results per source (default: 10)
 * @param year_from - Filter by year (optional)
 * @param year_to - Filter by year (optional)
 * @returns Unified search results
 */
export async function unified(
  query: string,
  limit: number = 10,
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
  if (year_from) params.append('year_from', year_from.toString());
  if (year_to) params.append('year_to', year_to.toString());

  const response = await apiClient.get<{
    success: boolean;
    data: {
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
    };
  }>(`/api/search/unified?${params.toString()}`);

  return response.data.data;
}

/**
 * Search external sources only
 *
 * GET /api/search/external
 * Searches arXiv and/or Semantic Scholar
 *
 * @param query - Search query string
 * @param sources - Sources to search (default: ['arxiv', 's2'])
 * @param limit - Maximum results per source (default: 10)
 * @returns External search results
 */
export async function external(
  query: string,
  sources: string[] = ['arxiv', 's2'],
  limit: number = 10
): Promise<{
  results: Array<{
    id: string;
    title: string;
    authors?: string[];
    abstract?: string;
    year?: number;
    source: 'arxiv' | 's2';
    externalId: string;
    pdfUrl?: string;
    citations?: number;
  }>;
  total: number;
}> {
  const params = new URLSearchParams();
  params.append('query', query);
  params.append('sources', sources.join(','));
  params.append('limit', limit.toString());

  const response = await apiClient.get<{
    success: boolean;
    data: {
      results: Array<{
        id: string;
        title: string;
        authors?: string[];
        abstract?: string;
        year?: number;
        source: 'arxiv' | 's2';
        externalId: string;
        pdfUrl?: string;
        citations?: number;
      }>;
      total: number;
    };
  }>(`/api/search/external?${params.toString()}`);

  return response.data.data;
}

/**
 * Add external paper to library
 *
 * POST /api/search/external
 * Creates a paper record from external source (arXiv, S2)
 *
 * @param paper - External paper data
 * @returns Created paper info
 */
export async function addExternal(paper: {
  source: 'arxiv' | 's2';
  externalId: string;
  title: string;
  authors?: string[];
  year?: number;
  abstract?: string;
  pdfUrl?: string;
}): Promise<{
  paperId: string;
  status: string;
  downloadTriggered: boolean;
  message: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    data: {
      paperId: string;
      status: string;
      downloadTriggered: boolean;
      message: string;
    };
  }>('/api/search/external', paper);

  return response.data.data;
}