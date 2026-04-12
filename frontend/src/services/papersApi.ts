/**
 * Papers API Service
 *
 * Paper management API calls:
 * - list(): Get paginated papers list
 * - get(): Get paper details
 * - delete(): Delete paper (requires re-auth)
 * - getStatus(): Get processing status
 * - toggleStar(): Toggle paper starred status
 *
 * All endpoints require authentication.
 */

import apiClient from '@/utils/apiClient';
import type { PapersListResponse, Paper, PapersQueryParams, ProcessingTaskStatus } from '@/types';

/**
 * Get paginated papers list
 */
export async function list(params?: PapersQueryParams): Promise<PapersListResponse> {
  const response = await apiClient.get<PapersListResponse>('/api/v1/papers', {
    params: {
      page: params?.page || 1,
      limit: params?.limit || 20,
      search: params?.search,
      sortBy: params?.sortBy || 'createdAt',
      sortOrder: params?.sortOrder || 'desc',
      starred: params?.starred,
      readStatus: params?.readStatus,
      dateFrom: params?.dateFrom,
      dateTo: params?.dateTo,
    },
  });

  return {
    success: true,
    data: response.data,
  } as unknown as PapersListResponse;
}

/**
 * Get paper details
 */
export async function get(id: string): Promise<Paper> {
  const response = await apiClient.get<{
    success: boolean;
    data: Paper;
  }>(`/api/v1/papers/${id}`);

  return response.data as unknown as Paper;
}

/**
 * Delete paper
 */
export async function deletePaper(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/papers/${id}`);
}

export async function remove(id: string): Promise<void> {
  return deletePaper(id);
}

export async function batchDelete(paperIds: string[]): Promise<{
  deletedCount: number;
  requestedCount: number;
  message: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    data: {
      deletedCount: number;
      requestedCount: number;
      message: string;
    };
  }>('/api/v1/papers/batch-delete', {
    paperIds,
  });

  return response.data as unknown as {
    deletedCount: number;
    requestedCount: number;
    message: string;
  };
}

/**
 * Batch star/unstar papers
 */
export async function batchStar(
  paperIds: string[],
  starred: boolean
): Promise<{
  updatedCount: number;
  requestedCount: number;
  starred: boolean;
  message: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    data: {
      updatedCount: number;
      requestedCount: number;
      starred: boolean;
      message: string;
    };
  }>('/api/v1/papers/batch/star', {
    paperIds,
    starred,
  });

  return response.data as unknown as {
    updatedCount: number;
    requestedCount: number;
    starred: boolean;
    message: string;
  };
}

/**
 * Get paper processing status
 */
export async function getStatus(id: string): Promise<{
  paperId: string;
  title?: string;
  status: ProcessingTaskStatus | string;
  progress: number;
  errorMessage?: string | null;
  updatedAt: string;
  completedAt?: string | null;
}> {
  const response = await apiClient.get<{
    success: boolean;
    data: {
      paperId: string;
      status: ProcessingTaskStatus | string;
      progress: number;
      errorMessage?: string | null;
      updatedAt: string;
      completedAt?: string | null;
    };
  }>(`/api/v1/papers/${id}/status`);

  return response.data as unknown as {
    paperId: string;
    title?: string;
    status: ProcessingTaskStatus | string;
    progress: number;
    errorMessage?: string | null;
    updatedAt: string;
    completedAt?: string | null;
  };
}

/**
 * Get paper reading notes
 */
export async function getSummary(id: string): Promise<{
  paperId: string;
  summary?: string | null;
  imrad?: any | null;
  status: string;
  hasNotes: boolean;
}> {
  const response = await apiClient.get<{
    success: boolean;
    data: {
      paperId: string;
      summary?: string | null;
      imrad?: any | null;
      status: string;
      hasNotes: boolean;
    };
  }>(`/api/v1/papers/${id}/summary`);

  return response.data as unknown as {
    paperId: string;
    summary?: string | null;
    imrad?: any | null;
    status: string;
    hasNotes: boolean;
  };
}

/**
 * Regenerate paper reading notes
 */
export async function regenerateNotes(
  id: string,
  modificationRequest?: string
): Promise<{
  paperId: string;
  status: string;
  message: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    data: {
      paperId: string;
      status: string;
      message: string;
    };
  }>(`/api/v1/papers/${id}/regenerate-notes`, {
    modificationRequest,
  });

  return response.data as unknown as {
    paperId: string;
    status: string;
    message: string;
  };
}

/**
 * Export paper notes as Markdown
 */
export async function exportNotes(id: string): Promise<string> {
  const response = await apiClient.get(`/api/v1/papers/${id}/notes/export`, {
    responseType: 'text',
  });

  return response.data as unknown as string;
}

/**
 * Toggle paper starred status
 */
export async function toggleStar(id: string, starred: boolean): Promise<Paper> {
  const response = await apiClient.patch<{
    success: boolean;
    data: Paper;
  }>(`/api/v1/papers/${id}/starred`, {
    starred,
  });

  return response.data as unknown as Paper;
}

/**
 * Update paper fields
 */
export async function update(id: string, data: { readingNotes?: string }): Promise<Paper> {
  const response = await apiClient.patch<{
    success: boolean;
    data: Paper;
  }>(`/api/v1/papers/${id}`, data);

  return response.data as unknown as Paper;
}

/**
 * Get PDF download URL
 */
export function getPdfUrl(id: string): string {
  return `${apiClient.defaults.baseURL}/api/v1/papers/${id}/pdf`;
}

// DELETED: createFromExternal() function
// This referenced /api/v1/search/external which doesn't exist in backend.
// TODO: Implement proper external paper import using backend endpoints
// Backend has: /api/v1/search/arxiv and /api/v1/search/semantic-scholar for search
// Paper creation should use standard POST /api/v1/papers endpoint
