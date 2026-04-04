import { Router, raw } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';
import { authenticate } from '../middleware/auth';
import { requirePermission } from '../middleware/rbac';
import { requireReauth, ReauthRequest } from '../middleware/reauth';
import { Errors } from '../middleware/errorHandler';
import { prisma } from '../config/database';
import { AuthRequest } from '../types/auth';
import {
  generatePresignedUploadUrl,
  objectExists,
  generateStorageKey,
  uploadToLocalStorage,
  USE_LOCAL_STORAGE,
} from '../services/storage';
import {
  createTask,
  getTaskStatus,
  TaskStatus,
  getProgressPercent,
} from '../services/tasks';
import { triggerBatchProcessing } from '../services/celery_client';

const router = Router();

// POST /api/upload/local/:storageKey - Local file upload endpoint (development only)
// 注意：此端点必须在 authenticate middleware 之前，因为它不需要认证
router.post(
  '/upload/local/:storageKey',
  raw({ type: 'application/octet-stream', limit: '50mb' }),
  async (req: AuthRequest, res, next) => {
    try {
      const { storageKey } = req.params;

      if (!storageKey) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'Storage key is required',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      const fileBuffer = req.body as Buffer;

      if (!fileBuffer || fileBuffer.length === 0) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'Empty file',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      await uploadToLocalStorage(storageKey, fileBuffer);

      logger.info(`File uploaded to local storage: ${storageKey} (${fileBuffer.length} bytes)`);

      res.status(200).json({
        success: true,
        data: {
          storageKey,
          size: fileBuffer.length,
          message: 'File uploaded successfully',
        },
      });
    } catch (error) {
      next(error);
    }
  }
);

// Apply authentication to all other routes
router.use(authenticate);

// GET /api/papers - 获取论文列表
router.get('/', requirePermission('papers', 'read'), async (req: AuthRequest, res, next) => {
  try {
    // 从查询参数解析分页参数，使用默认值
    const page = Math.max(1, parseInt(req.query.page as string, 10) || 1);
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit as string, 10) || 20));
    const skip = (page - 1) * limit;

    // 获取当前用户ID
    const userId = req.user?.sub;

    // 查询数据库获取论文列表，包含处理任务状态
    const where = userId ? { userId } : {};

    const [papers, total] = await Promise.all([
      prisma.paper.findMany({
        where,
        skip,
        take: limit,
        orderBy: { createdAt: 'desc' },
        include: {
          processingTask: {
            select: {
              status: true,
              errorMessage: true,
              updatedAt: true,
            },
          },
        },
      }),
      prisma.paper.count({ where }),
    ]);

    const totalPages = Math.ceil(total / limit);

    // 计算处理进度
    const papersWithProgress = papers.map(paper => {
      const processingStatus = paper.processingTask?.status as TaskStatus || paper.status;
      const progress = getProgressPercent(processingStatus);

      return {
        ...paper,
        processingStatus,
        progress,
        processingError: paper.processingTask?.errorMessage || null,
        lastUpdated: paper.processingTask?.updatedAt || paper.updatedAt,
        // Remove the nested processingTask from response
        processingTask: undefined,
      };
    });

    res.json({
      success: true,
      data: {
        papers: papersWithProgress,
        total,
        page,
        limit,
        totalPages,
      },
    });
  } catch (error) {
    next(error);
  }
});

// POST /api/papers - 请求上传URL
router.post(
  '/',
  requirePermission('papers', 'create'),
  async (req: AuthRequest, res, next) => {
    try {
      const userId = req.user?.sub;
      if (!userId) {
        return res.status(401).json({
          success: false,
          error: {
            type: '/errors/unauthorized',
            title: 'Unauthorized',
            status: 401,
            detail: 'User not authenticated',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      const { filename } = req.body;

      // Validate filename
      if (!filename) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'Filename is required',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Check file extension
      if (!filename.toLowerCase().endsWith('.pdf')) {
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

      // Generate storage key
      const storageKey = generateStorageKey(userId, filename);

      // Create paper record in database
      const paper = await prisma.paper.create({
        data: {
          title: filename.replace(/\.pdf$/i, ''), // Use filename as initial title
          authors: [],
          status: 'pending',
          userId,
          storageKey,
          keywords: [],
        },
      });

      // Generate presigned upload URL
      const { url, expiresIn } = await generatePresignedUploadUrl(userId, filename);

      logger.info(`Generated upload URL for paper ${paper.id}, file: ${filename}`);

      res.status(201).json({
        success: true,
        data: {
          paperId: paper.id,
          uploadUrl: url,
          expiresIn,
          storageKey,
          message: 'Please upload file to the provided URL, then call /api/papers/webhook to confirm',
        },
      });
    } catch (error) {
      next(error);
    }
  }
);

// POST /api/papers/webhook - Upload completion webhook
router.post(
  '/webhook',
  requirePermission('papers', 'create'),
  async (req: AuthRequest, res, next) => {
    try {
      const userId = req.user?.sub;
      if (!userId) {
        return res.status(401).json({
          success: false,
          error: {
            type: '/errors/unauthorized',
            title: 'Unauthorized',
            status: 401,
            detail: 'User not authenticated',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      const { paperId, storageKey } = req.body;

      // Validate required fields
      if (!paperId || !storageKey) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'paperId and storageKey are required',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Verify paper exists and belongs to user
      const paper = await prisma.paper.findFirst({
        where: { id: paperId, userId },
      });

      if (!paper) {
        return res.status(404).json({
          success: false,
          error: {
            type: '/errors/not-found',
            title: 'Not Found',
            status: 404,
            detail: 'Paper not found',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Verify object exists in storage
      const exists = await objectExists(storageKey);
      if (!exists) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'File not found in storage. Please upload first.',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Check if task already exists
      const existingTask = await prisma.processingTask.findUnique({
        where: { paperId },
      });

      if (existingTask) {
        return res.status(409).json({
          success: false,
          error: {
            type: '/errors/conflict',
            title: 'Conflict',
            status: 409,
            detail: 'Processing task already exists for this paper',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Create processing task and update paper status atomically
      const [task] = await prisma.$transaction([
        prisma.processingTask.create({
          data: {
            paperId,
            status: 'pending',
            storageKey,
          },
        }),
        prisma.paper.update({
          where: { id: paperId },
          data: {
            status: 'processing',
            uploadStatus: 'completed',
            uploadProgress: 100,
            uploadedAt: new Date(),
          },
        }),
      ]);

      logger.info(`Created processing task ${task.id} for paper ${paperId}`);

      // Batch tracking logic (per D-02: auto-start when all files uploaded)
      if (paper.batchId) {
        // Increment batch uploaded count
        await prisma.paperBatch.update({
          where: { id: paper.batchId },
          data: { uploadedCount: { increment: 1 } },
        });

        // Check if all files uploaded
        const batch = await prisma.paperBatch.findUnique({
          where: { id: paper.batchId },
          select: { uploadedCount: true, totalFiles: true },
        });

        if (batch && batch.uploadedCount === batch.totalFiles) {
          logger.info('All files uploaded for batch, triggering processing', {
            batchId: paper.batchId,
          });

          // Update batch status
          await prisma.paperBatch.update({
            where: { id: paper.batchId },
            data: { status: 'processing' },
          });

          // Trigger Celery batch processing task
          try {
            await triggerBatchProcessing(paper.batchId);
          } catch (error) {
            logger.error('Failed to trigger batch processing:', error);
            // Don't fail the webhook if batch trigger fails
          }
        }
      }

      res.status(201).json({
        success: true,
        data: {
          taskId: task.id,
          paperId,
          status: task.status,
          progress: 0,
          message: 'Upload confirmed. Processing task created.',
        },
      });
    } catch (error) {
      next(error);
    }
  }
);

// GET /api/papers/:id/status - Get processing status
router.get(
  '/:id/status',
  requirePermission('papers', 'read'),
  async (req: AuthRequest, res, next) => {
    try {
      const userId = req.user?.sub;
      if (!userId) {
        return res.status(401).json({
          success: false,
          error: {
            type: '/errors/unauthorized',
            title: 'Unauthorized',
            status: 401,
            detail: 'User not authenticated',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      const { id: paperId } = req.params;

      // Verify paper exists and belongs to user
      const paper = await prisma.paper.findFirst({
        where: { id: paperId, userId },
        include: {
          processingTask: {
            select: {
              status: true,
              errorMessage: true,
              updatedAt: true,
              completedAt: true,
            },
          },
        },
      });

      if (!paper) {
        return res.status(404).json({
          success: false,
          error: {
            type: '/errors/not-found',
            title: 'Not Found',
            status: 404,
            detail: 'Paper not found',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Calculate progress percentage based on status
      const statusProgress: Record<string, number> = {
        'pending': 10,
        'processing_ocr': 25,
        'parsing': 40,
        'extracting_imrad': 55,
        'generating_notes': 70,
        'completed': 100,
        'failed': 0,
        'no_pdf': 5,
      };

      // Use processing task status if available, otherwise paper status
      const effectiveStatus = paper.processingTask?.status || paper.status;
      const progress = statusProgress[effectiveStatus] ?? getProgressPercent(effectiveStatus as TaskStatus);

      res.json({
        success: true,
        data: {
          paperId: paper.id,
          title: paper.title,
          status: effectiveStatus,
          progress,
          errorMessage: paper.processingTask?.errorMessage || null,
          updatedAt: paper.processingTask?.updatedAt || paper.updatedAt,
          completedAt: paper.processingTask?.completedAt || null,
        },
      });
    } catch (error) {
      next(error);
    }
  }
);

// GET /api/papers/:id - Get paper details
router.get(
  '/:id',
  requirePermission('papers', 'read'),
  async (req: AuthRequest, res, next) => {
    try {
      const userId = req.user?.sub;
      if (!userId) {
        return res.status(401).json({
          success: false,
          error: {
            type: '/errors/unauthorized',
            title: 'Unauthorized',
            status: 401,
            detail: 'User not authenticated',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      const { id } = req.params;

      const paper = await prisma.paper.findFirst({
        where: { id, userId },
        include: {
          processingTask: {
            select: {
              status: true,
              errorMessage: true,
              createdAt: true,
              updatedAt: true,
              completedAt: true,
            },
          },
        },
      });

      if (!paper) {
        return res.status(404).json({
          success: false,
          error: {
            type: '/errors/not-found',
            title: 'Not Found',
            status: 404,
            detail: 'Paper not found',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Calculate processing status and progress
      const processingStatus = paper.processingTask?.status as TaskStatus || paper.status;
      const progress = getProgressPercent(processingStatus);

      res.json({
        success: true,
        data: {
          id: paper.id,
          title: paper.title,
          authors: paper.authors,
          year: paper.year,
          abstract: paper.abstract,
          doi: paper.doi,
          arxivId: paper.arxivId,
          status: paper.status,
          processingStatus,
          progress,
          storageKey: paper.storageKey,
          fileSize: paper.fileSize,
          pageCount: paper.pageCount,
          keywords: paper.keywords,
          venue: paper.venue,
          citations: paper.citations,
          createdAt: paper.createdAt,
          updatedAt: paper.updatedAt,
          processingError: paper.processingTask?.errorMessage || null,
          processingStartedAt: paper.processingTask?.createdAt || null,
          processingCompletedAt: paper.processingTask?.completedAt || null,
        },
      });
    } catch (error) {
      next(error);
    }
  }
);

// GET /api/papers/:id/summary - Get paper reading notes
router.get(
  '/:id/summary',
  requirePermission('papers', 'read'),
  async (req: AuthRequest, res, next) => {
    try {
      const userId = req.user?.sub;
      if (!userId) {
        return res.status(401).json({
          success: false,
          error: {
            type: '/errors/unauthorized',
            title: 'Unauthorized',
            status: 401,
            detail: 'User not authenticated',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      const { id } = req.params;

      const paper = await prisma.paper.findFirst({
        where: { id, userId },
        select: {
          id: true,
          readingNotes: true,
          status: true,
          imradJson: true,
        },
      });

      if (!paper) {
        return res.status(404).json({
          success: false,
          error: {
            type: '/errors/not-found',
            title: 'Not Found',
            status: 404,
            detail: 'Paper not found',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      res.json({
        success: true,
        data: {
          paperId: paper.id,
          summary: paper.readingNotes,
          imrad: paper.imradJson,
          status: paper.status,
          hasNotes: !!paper.readingNotes,
        },
      });
    } catch (error) {
      next(error);
    }
  }
);

// POST /api/papers/:id/regenerate-notes - Regenerate reading notes
router.post(
  '/:id/regenerate-notes',
  requirePermission('papers', 'update'),
  async (req: AuthRequest, res, next) => {
    try {
      const userId = req.user?.sub;
      if (!userId) {
        return res.status(401).json({
          success: false,
          error: {
            type: '/errors/unauthorized',
            title: 'Unauthorized',
            status: 401,
            detail: 'User not authenticated',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      const { id } = req.params;
      const { modificationRequest } = req.body;

      // Verify paper exists and belongs to user
      const paper = await prisma.paper.findFirst({
        where: { id, userId },
      });

      if (!paper) {
        return res.status(404).json({
          success: false,
          error: {
            type: '/errors/not-found',
            title: 'Not Found',
            status: 404,
            detail: 'Paper not found',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Call Python service to regenerate notes
      const aiServiceUrl = process.env.AI_SERVICE_URL || 'http://localhost:8000';
      const response = await fetch(`${aiServiceUrl}/internal/regenerate-notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          paperId: id,
          modificationRequest: modificationRequest || '',
          storageKey: paper.storageKey,
        }),
      });

      if (!response.ok) {
        throw new Error(`AI service returned ${response.status}`);
      }

      logger.info(`Triggered notes regeneration for paper ${id}`);

      res.json({
        success: true,
        data: {
          paperId: id,
          status: 'regenerating',
          message: 'Notes regeneration started',
        },
      });
    } catch (error) {
      logger.error('Failed to regenerate notes:', error);
      next(error);
    }
  }
);

// GET /api/papers/:id/notes/export - Export notes as Markdown
router.get(
  '/:id/notes/export',
  requirePermission('papers', 'read'),
  async (req: AuthRequest, res, next) => {
    try {
      const userId = req.user?.sub;
      if (!userId) {
        return res.status(401).json({
          success: false,
          error: {
            type: '/errors/unauthorized',
            title: 'Unauthorized',
            status: 401,
            detail: 'User not authenticated',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      const { id } = req.params;

      // Verify paper exists and belongs to user
      const paper = await prisma.paper.findFirst({
        where: { id, userId },
        select: {
          id: true,
          title: true,
          readingNotes: true,
          authors: true,
          year: true,
        },
      });

      if (!paper) {
        return res.status(404).json({
          success: false,
          error: {
            type: '/errors/not-found',
            title: 'Not Found',
            status: 404,
            detail: 'Paper not found',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      if (!paper.readingNotes) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'No notes available to export',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Generate Markdown content
      const authors = paper.authors?.join(', ') || 'Unknown';
      const year = paper.year || 'N/A';
      const markdown = `# ${paper.title}

**Authors:** ${authors}
**Year:** ${year}

---

${paper.readingNotes}

---

*Generated by ScholarAI*
`;

      // Set headers for download
      const sanitizedTitle = paper.title.replace(/[^a-zA-Z0-9\-_]/g, '_').substring(0, 50);
      res.setHeader('Content-Type', 'text/markdown');
      res.setHeader('Content-Disposition', `attachment; filename="${sanitizedTitle}_notes.md"`);
      res.send(markdown);
    } catch (error) {
      logger.error('Failed to export notes:', error);
      next(error);
    }
  }
);

// GET /api/papers/:id/pdf - Serve PDF file
router.get(
  '/:id/pdf',
  requirePermission('papers', 'read'),
  async (req: AuthRequest, res, next) => {
    try {
      const userId = req.user?.sub;
      if (!userId) {
        return res.status(401).json({
          success: false,
          error: {
            type: '/errors/unauthorized',
            title: 'Unauthorized',
            status: 401,
            detail: 'User not authenticated',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      const { id } = req.params;

      // Verify paper exists and belongs to user
      const paper = await prisma.paper.findFirst({
        where: { id, userId },
        select: {
          id: true,
          storageKey: true,
          pdfUrl: true,
        },
      });

      if (!paper) {
        return res.status(404).json({
          success: false,
          error: {
            type: '/errors/not-found',
            title: 'Not Found',
            status: 404,
            detail: 'Paper not found',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // If external PDF URL exists, redirect to it
      if (paper.pdfUrl) {
        return res.redirect(paper.pdfUrl);
      }

      // Otherwise, generate presigned URL for object storage
      if (paper.storageKey) {
        const { generatePresignedDownloadUrl } = await import('../services/storage.js');
        const url = await generatePresignedDownloadUrl(paper.storageKey);
        return res.redirect(url);
      }

      return res.status(404).json({
        success: false,
        error: {
          type: '/errors/not-found',
          title: 'Not Found',
          status: 404,
          detail: 'PDF file not available',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
    } catch (error) {
      logger.error('Failed to serve PDF:', error);
      next(error);
    }
  }
);

// DELETE /api/papers/:id - Delete paper (requires re-auth)
router.delete(
  '/:id',
  requirePermission('papers', 'delete'),
  requireReauth,
  async (req: ReauthRequest, res, next) => {
    try {
      const userId = req.user?.sub;
      if (!userId) {
        return res.status(401).json({
          success: false,
          error: {
            type: '/errors/unauthorized',
            title: 'Unauthorized',
            status: 401,
            detail: 'User not authenticated',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      const { id } = req.params;

      // requireReauth already validated currentPassword
      if (!req.reauthVerified) {
        throw Errors.validation('Re-authentication required');
      }

      // Verify paper exists and belongs to user
      const paper = await prisma.paper.findFirst({
        where: { id, userId },
      });

      if (!paper) {
        return res.status(404).json({
          success: false,
          error: {
            type: '/errors/not-found',
            title: 'Not Found',
            status: 404,
            detail: 'Paper not found',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Delete paper (cascade will handle related records)
      await prisma.paper.delete({
        where: { id },
      });

      // TODO: Also delete from object storage if storageKey exists
      if (paper.storageKey) {
        try {
          const { deleteObject } = await import('../services/storage.js');
          await deleteObject(paper.storageKey);
          logger.info(`Deleted object ${paper.storageKey} from storage`);
        } catch (storageError) {
          logger.warn(`Failed to delete object ${paper.storageKey} from storage:`, storageError);
          // Don't fail the request if storage deletion fails
        }
      }

      logger.info(`Deleted paper ${id}`);

      res.json({
        success: true,
        data: { id, deleted: true },
      });
    } catch (error) {
      next(error);
    }
  }
);

export { router as papersRouter };
