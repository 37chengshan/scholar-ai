import { Router } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { authenticate } from '../middleware/auth';
import { requirePermission } from '../middleware/rbac';
import { Errors } from '../middleware/errorHandler';
import { prisma } from '../config/database';
import { generateStorageKey, generatePresignedUploadUrl } from '../services/storage';
import { logger } from '../utils/logger';
import type { AuthRequest } from '../types/auth';
import { retrySinglePdf, retryBatchFailedPapers } from '../services/celery_client';

const router = Router();

// Apply authentication to all batch routes
router.use(authenticate);

/**
 * POST /api/papers/batch - Create batch upload task
 *
 * Creates a batch upload task with presigned URLs for multiple files.
 *
 * Request body:
 * {
 *   files: [
 *     { filename: "paper1.pdf", fileSize: 12345678, title?: string, doi?: string },
 *     { filename: "paper2.pdf", fileSize: 23456789 },
 *     ...
 *   ]
 * }
 *
 * Response:
 * {
 *   success: true,
 *   data: {
 *     batchId: "batch-uuid-xxx",
 *     totalFiles: 50,
 *     papers: [
 *       { id: "paper-1", uploadUrl: "presigned-url-1", filename: "paper1.pdf" },
 *       { id: "paper-2", uploadUrl: "presigned-url-2", filename: "paper2.pdf" },
 *       ...
 *     ]
 *   }
 * }
 *
 * Per D-01: Maximum 50 files per batch
 * Per D-02: Batch ID + per-file confirmation workflow
 */
router.post(
  '/',
  requirePermission('papers', 'create'),
  async (req: AuthRequest, res, next) => {
    try {
      const userId = req.user?.sub;
      if (!userId) {
        throw Errors.unauthorized('User not authenticated');
      }

      const { files } = req.body; // Array<{filename: string, fileSize: number, title?: string, doi?: string}>

      // Validation: files array required
      if (!files || !Array.isArray(files) || files.length === 0) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'files array is required and must not be empty',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Validation: max 50 files per batch (D-01)
      if (files.length > 50) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'Maximum 50 files allowed per batch',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Validate each file has required fields
      for (const file of files) {
        if (!file.filename || !file.fileSize) {
          return res.status(400).json({
            success: false,
            error: {
              type: '/errors/validation-error',
              title: 'Validation Error',
              status: 400,
              detail: 'Each file must have filename and fileSize',
              requestId: uuidv4(),
              timestamp: new Date().toISOString(),
            },
          });
        }

        // Check PDF extension
        if (!file.filename.toLowerCase().endsWith('.pdf')) {
          return res.status(400).json({
            success: false,
            error: {
              type: '/errors/validation-error',
              title: 'Validation Error',
              status: 400,
              detail: 'Only PDF files are accepted',
              requestId: uuidv4(),
              timestamp: new Date().toISOString(),
            },
          });
        }
      }

      // Create batch record
      const batchId = uuidv4();
      const batch = await prisma.paperBatch.create({
        data: {
          id: batchId,
          userId,
          totalFiles: files.length,
          status: 'uploading',
        },
      });

      // Generate presigned URLs and create paper records for all files
      const papers = await Promise.all(
        files.map(async (file) => {
          const paperId = uuidv4();
          const storageKey = generateStorageKey(userId, file.filename);

          // Generate presigned upload URL
          const { url: uploadUrl } = await generatePresignedUploadUrl(
            userId,
            file.filename
          );

          // Create paper record with batch association
          await prisma.paper.create({
            data: {
              id: paperId,
              userId,
              batchId,
              title: file.title || file.filename.replace(/\.pdf$/i, ''),
              authors: [],
              storageKey,
              uploadStatus: 'pending',
              uploadProgress: 0,
              status: 'pending',
              fileSize: file.fileSize,
              doi: file.doi || null,
              keywords: [],
            },
          });

          return {
            id: paperId,
            uploadUrl,
            filename: file.filename,
          };
        })
      );

      logger.info('Batch upload created', {
        userId,
        batchId,
        totalFiles: files.length,
      });

      res.status(201).json({
        success: true,
        data: {
          batchId,
          totalFiles: files.length,
          papers,
        },
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * GET /api/papers/batch/:batchId - Get batch status
 *
 * Returns basic batch information.
 */
router.get(
  '/:batchId',
  requirePermission('papers', 'read'),
  async (req: AuthRequest, res, next) => {
    try {
      const userId = req.user?.sub;
      if (!userId) {
        throw Errors.unauthorized('User not authenticated');
      }

      const { batchId } = req.params;

      // Query batch
      const batch = await prisma.paperBatch.findFirst({
        where: { id: batchId, userId },
      });

      if (!batch) {
        return res.status(404).json({
          success: false,
          error: {
            type: '/errors/not-found',
            title: 'Not Found',
            status: 404,
            detail: 'Batch not found',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      res.json({
        success: true,
        data: batch,
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * Helper function to get processing stage name
 */
function getProcessingStage(status: string): string {
  const stageNames: Record<string, string> = {
    'processing_ocr': 'OCR Processing',
    'parsing': 'Parsing Document',
    'extracting_imrad': 'Extracting Structure',
    'generating_notes': 'Generating Notes',
    'storing_vectors': 'Storing Vectors',
    'indexing_multimodal': 'Indexing Multimodal',
    'completed': 'Completed',
    'failed': 'Failed',
    'pending': 'Pending',
  };
  return stageNames[status] || status;
}

/**
 * Helper function to calculate progress percentage
 */
function getProgressPercent(status: string): number {
  const progressMap: Record<string, number> = {
    'pending': 0,
    'processing_ocr': 15,
    'parsing': 30,
    'extracting_imrad': 45,
    'generating_notes': 60,
    'storing_vectors': 75,
    'indexing_multimodal': 90,
    'completed': 100,
    'failed': 0,
  };
  return progressMap[status] || 0;
}

/**
 * GET /api/papers/batch/:batchId/progress - Query batch progress
 *
 * Returns detailed progress information for all files in a batch.
 * Per D-05: Shows processing stages with progress percentages.
 */
router.get(
  '/:batchId/progress',
  requirePermission('papers', 'read'),
  async (req: AuthRequest, res, next) => {
    try {
      const userId = req.user?.sub;
      if (!userId) {
        throw Errors.unauthorized('User not authenticated');
      }

      const { batchId } = req.params;

      // Query batch basic info
      const batch = await prisma.paperBatch.findFirst({
        where: { id: batchId, userId },
      });

      if (!batch) {
        return res.status(404).json({
          success: false,
          error: {
            type: '/errors/not-found',
            title: 'Not Found',
            status: 404,
            detail: 'Batch not found',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Query all papers with processing tasks
      const papers = await prisma.paper.findMany({
        where: { batchId },
        include: {
          processingTask: {
            select: {
              status: true,
              errorMessage: true,
              errorStage: true,
              errorTime: true,
              retryCount: true,
              updatedAt: true,
            },
          },
        },
        orderBy: { createdAt: 'asc' },
      });

      // Calculate aggregated statistics
      const uploadedCount = papers.filter(p => p.uploadStatus === 'completed').length;
      const processingCount = papers.filter(
        p => p.processingTask && !['completed', 'failed', 'pending'].includes(p.processingTask.status)
      ).length;
      const completedCount = papers.filter(p => p.status === 'completed').length;
      const failedCount = papers.filter(p => p.status === 'failed').length;

      // Overall progress: upload (20%) + processing (80%)
      const uploadProgress = Math.round((uploadedCount / batch.totalFiles) * 20);
      const processingProgress = Math.round((completedCount / batch.totalFiles) * 80);
      const overallProgress = uploadProgress + processingProgress;

      // Format per-file progress
      const formattedPapers = papers.map(paper => {
        const processingStatus = paper.processingTask?.status || paper.status || 'pending';
        const processingProgress = getProgressPercent(processingStatus);
        const processingStage = getProcessingStage(processingStatus);

        return {
          id: paper.id,
          filename: paper.title || 'Untitled',

          // Upload phase
          uploadStatus: paper.uploadStatus || 'pending',
          uploadProgress: paper.uploadProgress || 0,

          // Processing phase
          processingStatus,
          processingProgress,
          processingStage,

          // Error info
          errorMessage: paper.processingTask?.errorMessage || null,
          errorStage: paper.processingTask?.errorStage || null,
          retryCount: paper.processingTask?.retryCount || 0,

          // Timestamps
          uploadedAt: paper.uploadedAt,
          processingStartedAt: paper.processingTask?.updatedAt || null,
          completedAt: paper.status === 'completed' ? paper.updatedAt : null,
        };
      });

      // Estimated times (simplified - could be enhanced with historical data)
      const avgProcessingTime = 300; // 5 minutes per paper
      const estimatedUploadTime = Math.max(0, (batch.totalFiles - uploadedCount) * 30);
      const estimatedProcessingTime = Math.max(
        0,
        (batch.totalFiles - completedCount - failedCount) * avgProcessingTime
      );

      res.json({
        success: true,
        data: {
          batchId,
          totalFiles: batch.totalFiles,
          status: batch.status,

          // Upload phase
          uploadedCount,
          uploadProgress: Math.round((uploadedCount / batch.totalFiles) * 100),

          // Processing phase
          processingCount,
          completedCount,
          failedCount,
          overallProgress,

          // Time estimates
          estimatedUploadTime,
          estimatedProcessingTime,

          // Per-file details
          papers: formattedPapers,
        },
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * POST /api/papers/batch/:id/retry - Retry single failed paper
 *
 * Per D-07: Manual retry by user
 */
router.post(
  '/:id/retry',
  requirePermission('papers', 'update'),
  async (req: AuthRequest, res, next) => {
    try {
      const userId = req.user?.sub;
      if (!userId) {
        throw Errors.unauthorized('User not authenticated');
      }

      const paperId = req.params.id;

      // Verify paper exists and is failed
      const paper = await prisma.paper.findFirst({
        where: {
          id: paperId,
          userId,
          status: 'failed',
        },
        include: {
          processingTask: true,
        },
      });

      if (!paper) {
        return res.status(404).json({
          success: false,
          error: {
            type: '/errors/not-found',
            title: 'Not Found',
            status: 404,
            detail: 'Paper not found or not in failed state',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Increment retry count
      if (paper.processingTask) {
        await prisma.processingTask.update({
          where: { id: paper.processingTask.id },
          data: {
            retryCount: { increment: 1 },
            errorMessage: null,
            errorStage: null,
            status: 'pending',
          },
        });
      }

      // Reset paper status
      await prisma.paper.update({
        where: { id: paperId },
        data: { status: 'pending' },
      });

      // Trigger Celery retry task
      await retrySinglePdf(paperId);

      logger.info('Retry initiated for paper', { userId, paperId });

      res.json({
        success: true,
        message: 'Retry initiated',
        data: { paperId },
      });
    } catch (error) {
      next(error);
    }
  }
);

/**
 * POST /api/papers/batch/:batchId/retry-failed - Retry all failed papers in batch
 *
 * Per D-07: Batch retry for all failed papers
 */
router.post(
  '/:batchId/retry-failed',
  requirePermission('papers', 'update'),
  async (req: AuthRequest, res, next) => {
    try {
      const userId = req.user?.sub;
      if (!userId) {
        throw Errors.unauthorized('User not authenticated');
      }

      const { batchId } = req.params;

      // Verify batch exists
      const batch = await prisma.paperBatch.findFirst({
        where: { id: batchId, userId },
      });

      if (!batch) {
        return res.status(404).json({
          success: false,
          error: {
            type: '/errors/not-found',
            title: 'Not Found',
            status: 404,
            detail: 'Batch not found',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Count failed papers
      const failedCount = await prisma.paper.count({
        where: {
          batchId,
          userId,
          status: 'failed',
        },
      });

      if (failedCount === 0) {
        return res.json({
          success: true,
          message: 'No failed papers to retry',
          data: { batchId, retryCount: 0 },
        });
      }

      // Reset failed papers to pending
      await prisma.paper.updateMany({
        where: {
          batchId,
          userId,
          status: 'failed',
        },
        data: { status: 'pending' },
      });

      // Reset processing tasks
      await prisma.processingTask.updateMany({
        where: {
          paper: {
            batchId,
            userId,
          },
          status: 'failed',
        },
        data: {
          status: 'pending',
          errorMessage: null,
          errorStage: null,
          retryCount: { increment: 1 },
        },
      });

      // Trigger Celery batch retry task
      await retryBatchFailedPapers(batchId);

      logger.info('Batch retry initiated', { userId, batchId, failedCount });

      res.json({
        success: true,
        message: 'Batch retry initiated',
        data: { batchId, retryCount: failedCount },
      });
    } catch (error) {
      next(error);
    }
  }
);

export { router as batchRouter };