/**
 * useUpload Hook
 *
 * Manages file upload workflow with validation, progress tracking, and status polling.
 *
 * Features:
 * - PDF validation (type + 50MB size limit)
 * - Batch upload support (up to 50 files)
 * - Concurrent uploads (max 5 at a time)
 * - Progress tracking per file
 * - Status polling for processing state
 *
 * Per D-01: Maximum 50 files per batch
 * Per D-13: Batch upload with concurrent processing
 */

import { useState, useCallback } from 'react';
import * as uploadApi from '@/services/uploadApi';
import * as papersApi from '@/services/papersApi';
import toast from 'react-hot-toast';

export interface UploadFile {
  file: File;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed';
  progress: number;
  paperId?: string;
  error?: string;
}

export function useUpload() {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  /**
   * Validate single file
   * Returns error message or null if valid
   */
  const validateFile = (file: File): string | null => {
    // Check file type
    if (file.type !== 'application/pdf') {
      return 'Only PDF files are allowed';
    }

    // Check file size (50MB max)
    if (file.size > 50 * 1024 * 1024) {
      return 'File size must be less than 50MB';
    }

    return null;
  };

  /**
   * Add files to upload queue
   * Validates each file and sets initial status
   */
  const addFiles = useCallback((newFiles: File[]) => {
    const validatedFiles = newFiles.slice(0, 50).map((file) => {
      const error = validateFile(file);
      return {
        file,
        status: error ? 'failed' : 'pending',
        progress: 0,
        error,
      } as UploadFile;
    });

    setFiles((prev) => [...prev, ...validatedFiles]);

    if (validatedFiles.some((f) => f.error)) {
      const failedCount = validatedFiles.filter((f) => f.error).length;
      toast.error(`${failedCount} file(s) failed validation`);
    }
  }, []);

  /**
   * Map processing status to progress percentage
   */
  const mapStatusToProgress = (
    status: string
  ): number => {
    switch (status) {
      case 'pending':
        return 50;
      case 'processing':
        return 60;
      case 'ocr':
        return 70;
      case 'parsed':
        return 80;
      case 'vectorizing':
        return 90;
      case 'completed':
        return 100;
      case 'failed':
        return 0;
      default:
        return 50;
    }
  };

  /**
   * Upload single file
   * Handles presigned URL flow and status polling
   */
  const uploadSingle = async (uploadFile: UploadFile, index: number) => {
    try {
      // Step 1: Mark as uploading
      setFiles((prev) =>
        prev.map((f, i) =>
          i === index ? { ...f, status: 'uploading', progress: 10 } : f
        )
      );

      // Step 2: Get presigned upload URL
      const { paperId, uploadUrl, storageKey } = await uploadApi.getUploadUrl(
        uploadFile.file.name
      );

      setFiles((prev) =>
        prev.map((f, i) =>
          i === index ? { ...f, status: 'uploading', progress: 20, paperId } : f
        )
      );

      // Step 3: Upload file to storage (S3 or local)
      await uploadApi.uploadToS3(uploadUrl, uploadFile.file, (progress) => {
        setFiles((prev) =>
          prev.map((f, i) =>
            i === index ? { ...f, progress: 20 + Math.floor(progress * 0.3) } : f
          )
        );
      });

      // Step 4: Confirm upload and trigger processing
      await uploadApi.confirmUpload(paperId, storageKey);

      setFiles((prev) =>
        prev.map((f, i) =>
          i === index ? { ...f, status: 'processing', progress: 50 } : f
        )
      );

      // Step 5: Poll for processing status
      await pollStatus(paperId, index);
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.error?.detail ||
        error.message ||
        'Upload failed';
      setFiles((prev) =>
        prev.map((f, i) =>
          i === index ? { ...f, status: 'failed', error: errorMessage } : f
        )
      );
      toast.error(`Upload failed: ${errorMessage}`);
    }
  };

  /**
   * Poll processing status
   * Checks status every 5 seconds for up to 5 minutes
   */
  const pollStatus = async (paperId: string, index: number) => {
    const maxAttempts = 60; // 5 minutes at 5s intervals
    let attempts = 0;

    while (attempts < maxAttempts) {
      try {
        const status = await papersApi.getStatus(paperId);
        const progress = mapStatusToProgress(status.status);

        setFiles((prev) =>
          prev.map((f, i) =>
            i === index ? { ...f, progress } : f
          )
        );

        // Check if completed
        if (status.status === 'completed') {
          setFiles((prev) =>
            prev.map((f, i) =>
              i === index ? { ...f, status: 'completed', progress: 100 } : f
            )
          );
          toast.success(`${status.title} uploaded successfully`);
          return;
        }

        // Check if failed
        if (status.status === 'failed') {
          const errorMsg = status.errorMessage || 'Processing failed';
          setFiles((prev) =>
            prev.map((f, i) =>
              i === index ? { ...f, status: 'failed', error: errorMsg } : f
            )
          );
          toast.error(`Processing failed: ${errorMsg}`);
          return;
        }

        // Wait 5 seconds before next poll
        await new Promise((r) => setTimeout(r, 5000));
        attempts++;
      } catch (error) {
        // Status polling error - continue polling silently
        // User feedback happens on final success/failure/timeout
        // Continue polling even if one request fails
        await new Promise((r) => setTimeout(r, 5000));
        attempts++;
      }
    }

    // Timeout after 5 minutes
    setFiles((prev) =>
      prev.map((f, i) =>
        i === index
          ? { ...f, status: 'failed', error: 'Processing timeout' }
          : f
      )
    );
    toast.error('Processing timeout - please check status later');
  };

  /**
   * Upload all pending files
   * Processes files in batches of 5 concurrently
   */
  const uploadAll = async () => {
    const pendingFiles = files.filter((f) => f.status === 'pending');
    if (pendingFiles.length === 0) {
      toast.error('No files to upload');
      return;
    }

    setIsUploading(true);

    // Upload max 5 files concurrently
    for (let i = 0; i < pendingFiles.length; i += 5) {
      const batch = pendingFiles.slice(i, i + 5);
      await Promise.all(
        batch.map((f) => {
          const globalIndex = files.findIndex((ff) => ff === f);
          return uploadSingle(f, globalIndex);
        })
      );
    }

    setIsUploading(false);
  };

  /**
   * Remove file from queue
   */
  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  /**
   * Clear all files
   */
  const clearFiles = useCallback(() => {
    setFiles([]);
  }, []);

  return {
    files,
    addFiles,
    uploadAll,
    removeFile,
    clearFiles,
    isUploading,
  };
}