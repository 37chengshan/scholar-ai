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
  status: 'PROCESSING' | 'COMPLETED' | 'FAILED' | string;
  chunksCount?: number | null;
  llmTokens?: number | null;
  pageCount?: number | null;
  imageCount?: number | null;
  tableCount?: number | null;
  errorMessage?: string | null;
  processingTime?: number | null;
  progress?: number;
  processingStatus?: string | null;
  completedAt?: string | null;
  paperId?: string | null;
  createdAt: string;
  updatedAt?: string | null;
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

interface RawUploadHistoryRecord {
  id: string;
  user_id?: string;
  paper_id?: string | null;
  filename: string;
  status: string;
  chunks_count?: number | null;
  llm_tokens?: number | null;
  page_count?: number | null;
  image_count?: number | null;
  table_count?: number | null;
  error_message?: string | null;
  processing_time?: number | null;
  created_at: string;
  updated_at?: string | null;
  paper_title?: string | null;
  progress?: number;
  processingStatus?: string | null;
  completedAt?: string | null;
}

function normalizeUploadHistoryRecord(record: RawUploadHistoryRecord): UploadHistoryRecord {
  return {
    id: record.id,
    userId: record.user_id || '',
    paperId: record.paper_id ?? null,
    filename: record.filename,
    status: record.status,
    chunksCount: record.chunks_count ?? null,
    llmTokens: record.llm_tokens ?? null,
    pageCount: record.page_count ?? null,
    imageCount: record.image_count ?? null,
    tableCount: record.table_count ?? null,
    errorMessage: record.error_message ?? null,
    processingTime: record.processing_time ?? null,
    progress: record.progress,
    processingStatus: record.processingStatus ?? null,
    completedAt: record.completedAt ?? null,
    createdAt: record.created_at,
    updatedAt: record.updated_at ?? null,
    paper: record.paper_id
      ? {
          id: record.paper_id,
          title: record.paper_title || record.filename,
          filename: record.filename,
        }
      : null,
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
  const response = await apiClient.get<{ records: RawUploadHistoryRecord[]; total: number }>('/api/v1/uploads/history', {
    params: {
      limit: Math.min(100, Math.max(1, limit)),
      offset: Math.max(0, offset),
    },
  });

  return {
    success: true,
    data: {
      records: (response.data.records || []).map(normalizeUploadHistoryRecord),
      total: response.data.total || 0,
    },
  };
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
  const response = await apiClient.get<RawUploadHistoryRecord>(`/api/v1/uploads/history/${id}`);

  return {
    success: true,
    data: normalizeUploadHistoryRecord(response.data),
  };
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
  const response = await apiClient.delete<{ message: string; paperPreserved: boolean }>(`/api/v1/uploads/history/${id}`);

  return {
    success: true,
    data: response.data,
  };
}

/**
 * Export all functions as named exports for convenience
 */
export const uploadHistoryApi = {
  getList,
  getById,
  delete: deleteRecord,
};
