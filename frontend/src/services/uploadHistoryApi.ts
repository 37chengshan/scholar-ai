/**
 * Upload History API Service
 *
 * Upload history management API calls:
 * - getList(): Get paginated upload history records
 * - getById(): Get detailed upload history record
 * - delete(): Delete upload history record (safe deletion)
 *
 * Per D-01: User isolation - each user only sees their own history
 * Per D-02: Safe deletion - deleting history does not delete paper
 */

import apiClient from '@/utils/apiClient';

/**
 * Upload history record interface
 */
export interface UploadHistoryRecord {
  id: string;
  userId: string;
  filename: string;
  status: 'PROCESSING' | 'COMPLETED' | 'FAILED';
  chunksCount?: number | null;
  llmTokens?: number | null;
  pageCount?: number | null;
  imageCount?: number | null;
  tableCount?: number | null;
  errorMessage?: string | null;
  processingTime?: number | null;
  paperId?: string | null;
  createdAt: string;
  updatedAt: string;
  paper?: {
    id: string;
    title: string;
    filename: string;
  } | null;
}

/**
 * Upload history list response
 */
export interface UploadHistoryListResponse {
  success: boolean;
  data: {
    records: UploadHistoryRecord[];
    total: number;
  };
}

/**
 * Get paginated upload history list
 *
 * GET /api/v1/upload-history
 * Returns user's upload history records
 *
 * @param limit - Number of records per page (default 50, max 100)
 * @param offset - Offset for pagination (default 0)
 * @returns Upload history records with total count
 */
export async function getList(limit = 50, offset = 0): Promise<UploadHistoryListResponse> {
  const response = await apiClient.get<UploadHistoryListResponse>('/api/v1/uploads/history', {
    params: {
      limit: Math.min(100, Math.max(1, limit)),
      offset: Math.max(0, offset),
    },
  });

  return response.data;
}

/**
 * Get detailed upload history record
 *
 * GET /api/v1/upload-history/:id
 * Returns detailed upload history record with paper info
 *
 * @param id - Upload history record ID
 * @returns Detailed upload history record
 */
export async function getById(id: string): Promise<{
  success: boolean;
  data: UploadHistoryRecord;
}> {
  const response = await apiClient.get<{
    success: boolean;
    data: UploadHistoryRecord;
  }>(`/api/v1/uploads/history/${id}`);

  return response.data;
}

/**
 * Delete upload history record
 *
 * DELETE /api/v1/upload-history/:id
 * Safe deletion - only removes history record, paper remains in library
 *
 * Per D-01: Deleting history does not delete paper
 *
 * @param id - Upload history record ID
 * @returns Deletion confirmation
 */
export async function deleteRecord(id: string): Promise<{
  success: boolean;
  data: {
    message: string;
    paperPreserved: boolean;
  };
}> {
  const response = await apiClient.delete<{
    success: boolean;
    data: {
      message: string;
      paperPreserved: boolean;
    };
  }>(`/api/v1/uploads/history/${id}`);

  return response.data;
}

/**
 * Export all functions as named exports for convenience
 */
export const uploadHistoryApi = {
  getList,
  getById,
  delete: deleteRecord,
};