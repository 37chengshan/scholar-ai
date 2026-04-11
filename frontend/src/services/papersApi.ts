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
import type { PapersListResponse, Paper, PaperWithProgress, PapersQueryParams, ProcessingTaskStatus } from '@/types';

/**
 * Get paginated papers list
 *
 * GET /api/v1/papers
 * Returns user's papers with processing status and progress
 *
 * @param params - Query parameters (page, limit, search, sortBy, starred, readStatus, dateFrom, dateTo)
 * @returns Papers list with pagination info
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

  return response.data;
}

/**
 * Get paper details
 *
 * GET /api/v1/papers/:id
 * Returns full paper metadata and processing info
 *
 * @param id - Paper ID
 * @returns Paper details
 */
export async function get(id: string): Promise<Paper> {
  const response = await apiClient.get<{
    success: boolean;
    data: Paper;
  }>(`/api/v1/papers/${id}`);

  return response.data.data;
}

/**
 * Delete paper
 *
 * DELETE /api/v1/papers/:id
 * Requires re-authentication (currentPassword in request body)
 *
 * Note: This endpoint has requireReauth middleware.
 * Frontend should prompt user for password confirmation.
 *
 * @param id - Paper ID
 * @param currentPassword - User's current password for re-auth
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

  return response.data.data;
}

/**
 * Batch star/unstar papers
 *
 * POST /api/v1/papers/batch/star
 * Updates starred status for multiple papers at once
 *
 * @param paperIds - Array of paper IDs
 * @param starred - New starred status
 * @returns Update result
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

  return response.data.data;
}

/**
 * Get paper processing status
 *
 * GET /api/v1/papers/:id/status
 * Returns real-time processing status and progress
 *
 * @param id - Paper ID
 * @returns Processing status info
 */
export async function getStatus(id: string): Promise<{
  paperId: string;
  title: string;
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
      title: string;
      status: ProcessingTaskStatus | string;
      progress: number;
      errorMessage?: string | null;
      updatedAt: string;
      completedAt?: string | null;
    };
  }>(`/api/v1/papers/${id}/status`);

  return response.data.data;
}

/**
 * Get paper reading notes
 *
 * GET /api/v1/papers/:id/summary
 * Returns generated reading notes and IMRaD structure
 *
 * @param id - Paper ID
 * @returns Reading notes data
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

  return response.data.data;
}

/**
 * Regenerate paper reading notes
 *
 * POST /api/v1/papers/:id/regenerate-notes
 * Triggers AI service to regenerate notes with optional modifications
 *
 * @param id - Paper ID
 * @param modificationRequest - Optional instructions for modification
 * @returns Regeneration status
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

  return response.data.data;
}

/**
 * Export paper notes as Markdown
 *
 * GET /api/v1/papers/:id/notes/export
 * Returns Markdown file for download
 *
 * @param id - Paper ID
 * @returns Markdown content (use response.text())
 */
export async function exportNotes(id: string): Promise<string> {
  const response = await apiClient.get(`/api/v1/papers/${id}/notes/export`, {
    responseType: 'text',
  });

  return response.data;
}

/**
 * Toggle paper starred status
 *
 * PATCH /api/v1/papers/:id/starred
 * Updates the starred boolean on a paper
 *
 * NOTE: This endpoint requires Plan 15-01 to be completed first.
 * Backend must have:
 * - `starred` field in Paper model (Prisma schema)
 * - PATCH /api/v1/papers/:id/starred route implementation
 *
 * @param id - Paper ID
 * @param starred - New starred status
 * @returns Updated paper data
 */
export async function toggleStar(id: string, starred: boolean): Promise<Paper> {
  const response = await apiClient.patch<{
    success: boolean;
    data: Paper;
  }>(`/api/v1/papers/${id}/starred`, {
    starred,
  });

  return response.data.data;
}

/**
 * Update paper fields
 *
 * PATCH /api/v1/papers/:id
 * Updates paper metadata (e.g., readingNotes)
 *
 * @param id - Paper ID
 * @param data - Fields to update
 * @returns Updated paper data
 */
export async function update(id: string, data: { readingNotes?: string }): Promise<Paper> {
  const response = await apiClient.patch<{
    success: boolean;
    data: Paper;
  }>(`/api/v1/papers/${id}`, data);

  return response.data.data;
}

/**
 * Get PDF download URL
 *
 * GET /api/v1/papers/:id/pdf
 * Redirects to PDF URL (presigned S3 URL or external URL)
 *
 * Note: This endpoint returns a redirect, not JSON.
 * Frontend should open in new tab or use direct link.
 *
 * @param id - Paper ID
 * @returns PDF URL (redirect target)
 */
export function getPdfUrl(id: string): string {
  // Returns the URL that will redirect to actual PDF
  return `${apiClient.defaults.baseURL}/api/v1/papers/${id}/pdf`;
}

// DELETED: createFromExternal() function
// This referenced /api/v1/search/external which doesn't exist in backend.
// TODO: Implement proper external paper import using backend endpoints
// Backend has: /api/v1/search/arxiv and /api/v1/search/semantic-scholar for search
// Paper creation should use standard POST /api/v1/papers endpoint