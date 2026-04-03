import { Router } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { authenticate } from '../middleware/auth';
import { requirePermission } from '../middleware/rbac';
import { Errors } from '../middleware/errorHandler';
import { prisma } from '../config/database';
import { generateStorageKey, generatePresignedUploadUrl } from '../services/storage';
import { logger } from '../utils/logger';
import type { AuthRequest } from '../types/auth';

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

export { router as batchRouter };