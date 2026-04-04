/**
 * Upload API Service
 *
 * Paper upload workflow API calls:
 * - getUploadUrl(): Request presigned upload URL
 * - uploadFile(): Upload file to storage (local or S3)
 * - confirmUpload(): Confirm upload and trigger processing
 *
 * Two upload modes:
 * 1. S3/MinIO (production): Request URL → Upload to S3 → Confirm
 * 2. Local storage (development): Direct upload to /upload/local/:key
 */

import apiClient from '@/utils/apiClient';
import type { UploadResult } from '@/types';

/**
 * Request presigned upload URL (S3/MinIO mode)
 *
 * POST /api/papers
 * Creates paper record and returns presigned upload URL
 *
 * @param filename - PDF filename
 * @returns Upload URL, paper ID, and storage key
 */
export async function getUploadUrl(filename: string): Promise<{
  paperId: string;
  uploadUrl: string;
  expiresIn: number;
  storageKey: string;
  message: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    data: {
      paperId: string;
      uploadUrl: string;
      expiresIn: number;
      storageKey: string;
      message: string;
    };
  }>('/api/papers', {
    filename,
  });

  return response.data.data;
}

/**
 * Upload file directly to local storage (development mode)
 *
 * POST /api/upload/local/:storageKey
 * Bypasses S3, directly uploads to local filesystem
 *
 * Note: Only used when USE_LOCAL_STORAGE=true in backend
 *
 * @param storageKey - Storage key from getUploadUrl()
 * @param file - PDF file to upload
 * @returns Upload confirmation
 */
export async function uploadFile(
  storageKey: string,
  file: File,
  onProgress?: (progress: number) => void
): Promise<{
  storageKey: string;
  size: number;
  message: string;
}> {
  // Use FormData for file upload
  const formData = new FormData();
  formData.append('file', file);

  // Upload with progress tracking
  const response = await apiClient.post<{
    success: boolean;
    data: {
      storageKey: string;
      size: number;
      message: string;
    };
  }>(`/api/papers/upload/local/${storageKey}`, file, {
    headers: {
      'Content-Type': 'application/octet-stream',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        onProgress(percentCompleted);
      }
    },
  });

  return response.data.data;
}

/**
 * Confirm upload and trigger processing
 *
 * POST /api/papers/webhook
 * Verifies file exists in storage and creates processing task
 *
 * @param paperId - Paper ID from getUploadUrl()
 * @param storageKey - Storage key from getUploadUrl()
 * @returns Processing task info
 */
export async function confirmUpload(
  paperId: string,
  storageKey: string
): Promise<UploadResult> {
  const response = await apiClient.post<{
    success: boolean;
    data: UploadResult;
  }>('/api/papers/webhook', {
    paperId,
    storageKey,
  });

  return response.data.data;
}

/**
 * Upload file to S3 using presigned URL
 *
 * Note: This is a direct S3 upload, NOT via apiClient.
 * Presigned URL allows direct upload without authentication.
 *
 * @param uploadUrl - Presigned S3 URL from getUploadUrl()
 * @param file - PDF file to upload
 * @param onProgress - Progress callback
 */
export async function uploadToS3(
  uploadUrl: string,
  file: File,
  onProgress?: (progress: number) => void
): Promise<void> {
  // Check if this is local storage upload (URL contains /upload/local/)
  const isLocalUpload = uploadUrl.includes('/upload/local/');

  if (isLocalUpload) {
    // Local storage upload: Use POST with apiClient (requires auth)
    await apiClient.post(uploadUrl, file, {
      headers: {
        'Content-Type': 'application/octet-stream',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });
  } else {
    // S3/MinIO upload: Use PUT without auth (presigned URL)
    await fetch(uploadUrl, {
      method: 'PUT',
      body: file,
      headers: {
        'Content-Type': 'application/pdf',
      },
    });

    // Simulate progress for S3 (no native progress tracking with fetch)
    if (onProgress) {
      onProgress(50);
      setTimeout(() => onProgress(100), 500);
    }
  }
}