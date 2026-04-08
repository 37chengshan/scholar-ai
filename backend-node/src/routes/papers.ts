import { Router, raw } from 'express';
import { v4 as uuidv4 } from 'uuid';
import multer from 'multer';
import { Prisma } from '@prisma/client';
import { logger } from '../utils/logger';
import { authenticate } from '../middleware/auth';
import { requirePermission } from '../middleware/rbac';
import { Errors } from '../middleware/errorHandler';
import { prisma } from '../config/database';
import { AuthRequest } from '../types/auth';
import {
  generatePresignedUploadUrl,
  objectExists,
  generateStorageKey,
  uploadToLocalStorage,
  USE_LOCAL_STORAGE,
  getLocalFileBuffer,
} from '../services/storage';
import {
  createTask,
  getTaskStatus,
  TaskStatus,
  getProgressPercent,
} from '../services/tasks';
import { triggerBatchProcessing } from '../services/celery_client';

const router = Router();

// Multer configuration for direct upload
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 50 * 1024 * 1024 }, // 50MB
  fileFilter: (req, file, cb) => {
    if (file.mimetype === 'application/pdf' || file.originalname.toLowerCase().endsWith('.pdf')) {
      cb(null, true);
    } else {
      cb(new Error('Only PDF files are allowed'));
    }
  },
});

// GET /api/download/local/:storageKey - Serve local files (development only)
// This endpoint must be BEFORE authenticate middleware for presigned URLs
router.get(
  '/download/local/:storageKey',
  async (req: AuthRequest, res, next) => {
    try {
      const { storageKey } = req.params;

      if (!USE_LOCAL_STORAGE) {
        return res.status(404).json({
          success: false,
          error: {
            type: '/errors/not-found',
            title: 'Not Found',
            status: 404,
            detail: 'Local storage not enabled',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      const buffer = await getLocalFileBuffer(storageKey);

      if (!buffer) {
        return res.status(404).json({
          success: false,
          error: {
            type: '/errors/not-found',
            title: 'Not Found',
            status: 404,
            detail: 'File not found',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Set content type and send file
      res.setHeader('Content-Type', 'application/pdf');
      res.setHeader('Content-Disposition', `inline; filename="${storageKey}"`);
      res.send(buffer);
    } catch (error) {
      next(error);
    }
  }
);

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
          storageKey: storageKey,
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

    // Parse filters
    const starredParam = req.query.starred as string | undefined;
    const starredFilter = starredParam === 'true' ? true : starredParam === 'false' ? false : undefined;
    const readStatus = req.query.readStatus as string | undefined;
    const dateFrom = req.query.dateFrom as string | undefined;
    const dateTo = req.query.dateTo as string | undefined;

    // Build where clause
    const where: any = {};
    if (userId) where.userId = userId;
    if (starredFilter !== undefined) where.starred = starredFilter;

    // Date range filter
    if (dateFrom || dateTo) {
      where.createdAt = {};
      if (dateFrom) where.createdAt.gte = new Date(dateFrom);
      if (dateTo) where.createdAt.lte = new Date(dateTo);
    }

    // Read status filter (D-03)
    // unread: papers with no reading_progress record
    // in-progress: papers with reading_progress.currentPage > 0 but < totalPages
    // completed: papers with reading_progress.currentPage >= totalPages
    let papersQuery: any;
    let countQuery: any;

    if (readStatus === 'unread') {
      // Papers without reading progress
      where.NOT = {
        readingProgress: {
          some: {
            userId: userId,
          },
        },
      };
    } else if (readStatus === 'in-progress' || readStatus === 'completed') {
      // Need to join with reading_progress table
      papersQuery = prisma.$queryRaw`
        SELECT p.*,
               pt.status as "processingStatus",
               pt.error_message as "processingError",
               pt.updated_at as "lastUpdated"
        FROM papers p
        LEFT JOIN processing_tasks pt ON p.id = pt.paper_id
        INNER JOIN reading_progress rp ON p.id = rp.paper_id
        WHERE p.user_id = ${userId}
          AND rp.user_id = ${userId}
          ${starredFilter !== undefined ? Prisma.sql`AND p.starred = ${starredFilter}` : Prisma.sql``}
          ${dateFrom ? Prisma.sql`AND p.created_at >= ${new Date(dateFrom)}` : Prisma.sql``}
          ${dateTo ? Prisma.sql`AND p.created_at <= ${new Date(dateTo)}` : Prisma.sql``}
          ${readStatus === 'in-progress' 
            ? Prisma.sql`AND rp.current_page > 0 AND rp.current_page < COALESCE(rp.total_pages, 999999)` 
            : Prisma.sql`AND rp.current_page >= COALESCE(rp.total_pages, 0)`
          }
        ORDER BY p.created_at DESC
        LIMIT ${limit}
        OFFSET ${skip}
      `;

      countQuery = prisma.$queryRaw`
        SELECT COUNT(*) as count
        FROM papers p
        INNER JOIN reading_progress rp ON p.id = rp.paper_id
        WHERE p.user_id = ${userId}
          AND rp.user_id = ${userId}
          ${starredFilter !== undefined ? Prisma.sql`AND p.starred = ${starredFilter}` : Prisma.sql``}
          ${dateFrom ? Prisma.sql`AND p.created_at >= ${new Date(dateFrom)}` : Prisma.sql``}
          ${dateTo ? Prisma.sql`AND p.created_at <= ${new Date(dateTo)}` : Prisma.sql``}
          ${readStatus === 'in-progress' 
            ? Prisma.sql`AND rp.current_page > 0 AND rp.current_page < COALESCE(rp.total_pages, 999999)` 
            : Prisma.sql`AND rp.current_page >= COALESCE(rp.total_pages, 0)`
          }
      `;
    }

    let papers: any[];
    let total: number;

    if (readStatus === 'in-progress' || readStatus === 'completed') {
      // Use raw query for complex join
      const [rawPapers, countResult] = await Promise.all([
        papersQuery,
        countQuery,
      ]);
      papers = rawPapers;
      total = Number((countResult as any)[0]?.count || 0);
    } else {
      // Use Prisma ORM for simpler queries
      [papers, total] = await Promise.all([
        prisma.papers.findMany({
          where,
          skip,
          take: limit,
          orderBy: { createdAt: 'desc' },
          include: {
            processingTasks: {
              select: {
                status: true,
                errorMessage: true,
                updatedAt: true,
              },
            },
            readingProgress: {
              where: { userId: userId },
              select: {
                currentPage: true,
                totalPages: true,
              },
            },
          },
        }),
        prisma.papers.count({ where }),
      ]);
    }

    const totalPages = Math.ceil(total / limit);

    // 计算处理进度和阅读进度
    const papersWithProgress = papers.map(paper => {
      const processingStatus = paper.processingTasks?.status as TaskStatus || paper.status;
      const progress = getProgressPercent(processingStatus);
      
      // Calculate reading progress (D-03)
      const readingProgressData = paper.readingProgress?.[0];
      let readingProgressPercent = 0;
      if (readingProgressData && readingProgressData.totalPages) {
        readingProgressPercent = Math.round((readingProgressData.currentPage / readingProgressData.totalPages) * 100);
      }

      // Destructure to remove nested relations
      const { processingTasks, readingProgress, ...paperData } = paper as any;

      return {
        ...paperData,
        processingStatus,
        progress,
        readingProgress: readingProgressPercent,
        processingError: processingTasks?.errorMessage || null,
        lastUpdated: processingTasks?.updatedAt || paperData.updatedAt,
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

// GET /api/papers/search - Search papers by title, authors, or abstract
router.get(
  '/search',
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

      // Parse query parameters
      const { q, page: pageStr, limit: limitStr } = req.query;

      // Validate search query
      if (!q || typeof q !== 'string') {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'Search query (q) is required',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      if (q.length < 1 || q.length > 100) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'Search query must be between 1 and 100 characters',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Parse pagination with validation
      const page = Math.max(1, parseInt(pageStr as string, 10) || 1);
      const limit = Math.min(100, Math.max(1, parseInt(limitStr as string, 10) || 20));
      const skip = (page - 1) * limit;

      // Build search query - multi-field fuzzy search
      const papers = await prisma.papers.findMany({
        where: {
          userId,
          OR: [
            { title: { contains: q, mode: 'insensitive' } },
            { authors: { hasSome: [q] } },
            { abstract: { contains: q, mode: 'insensitive' } },
          ],
        },
        skip,
        take: limit,
        orderBy: { createdAt: 'desc' },
        include: {
          processingTasks: {
            select: {
              status: true,
              errorMessage: true,
              updatedAt: true,
            },
          },
        },
      });

      // Get total count for pagination
      const total = await prisma.papers.count({
        where: {
          userId,
          OR: [
            { title: { contains: q, mode: 'insensitive' } },
            { authors: { hasSome: [q] } },
            { abstract: { contains: q, mode: 'insensitive' } },
          ],
        },
      });

      const totalPages = Math.ceil(total / limit);

      // Calculate processing status and progress
      const papersWithProgress = papers.map(paper => {
        const processingStatus = paper.processingTasks?.status as TaskStatus || paper.status;
        const progress = getProgressPercent(processingStatus);

        return {
          ...paper,
          processingStatus,
          progress,
          processingError: paper.processingTasks?.errorMessage || null,
          lastUpdated: paper.processingTasks?.updatedAt || paper.updatedAt,
          processingTasks: undefined,
        };
      });

      logger.info(`Search completed for user ${userId}`, {
        query: q,
        results: papers.length,
        total,
        page,
      });

      res.json({
        success: true,
        data: {
          papers: papersWithProgress,
          total,
          page,
          limit,
          totalPages,
          query: q,
        },
      });
    } catch (error) {
      logger.error('Search failed:', error);
      next(error);
    }
  }
);

// POST /api/papers - 请求上传 URL
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

      // Extract title from filename
      const title = filename.replace(/\.pdf$/i, '');

      // Check for duplicate paper (same user + same title)
      const existingPaper = await prisma.papers.findFirst({
        where: {
          userId: userId,
          title: title,
        },
        include: {
          processingTasks: {
            select: {
              status: true,
              errorMessage: true,
            },
          },
        },
      });

      if (existingPaper) {
        logger.warn(`Duplicate paper detected: ${title} for user ${userId}`);
        
        return res.status(409).json({
          success: false,
          error: {
            type: '/errors/conflict',
            title: 'Duplicate Paper',
            status: 409,
            detail: `A paper with title "${title}" already exists in your library.`,
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
          data: {
            existingPaper: {
              id: existingPaper.id,
              title: existingPaper.title,
              status: existingPaper.status,
              processingStatus: existingPaper.processingTasks?.status || null,
              createdAt: existingPaper.createdAt,
              storageKey: existingPaper.storageKey,
            },
            suggestion: existingPaper.storageKey
              ? 'This paper has already been uploaded. You can view it in your library or upload a different file.'
              : 'A paper record exists but file upload is incomplete. You can continue the upload or delete the record.',
          },
        });
      }

      // Generate storage key
      const storageKey = generateStorageKey(userId, filename);

      // Create paper record in database
      const paperId = uuidv4();
      const paper = await prisma.papers.create({
        data: {
          id: paperId,
          title: filename.replace(/\.pdf$/i, ''),
          authors: [],
          status: 'pending',
          userId: userId,
          storageKey: storageKey,
          keywords: [],
          updatedAt: new Date(),
        },
      });

      // Generate presigned upload URL
      const { url, expiresIn } = await generatePresignedUploadUrl(userId, filename);

      // Create UploadHistory record (Task 3: wire upload history creation)
      const uploadHistoryId = uuidv4();
      await prisma.uploadHistory.create({
        data: {
          id: uploadHistoryId,
          userId,
          filename,
          status: 'PROCESSING',
          createdAt: new Date(),
          updatedAt: new Date(),
        },
      });

      logger.info(`Created UploadHistory record ${uploadHistoryId} for upload request`, {
        userId,
        filename,
        paperId: paper.id,
      });

      logger.info(`Generated upload URL for paper ${paper.id}, file: ${filename}`);

      res.status(201).json({
        success: true,
        data: {
          paperId: paper.id,
          uploadUrl: url,
          expiresIn,
          storageKey: storageKey,
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

      const { paperId: paperId, storageKey } = req.body;

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
      const paper = await prisma.papers.findFirst({
        where: { id: paperId, userId: userId },
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
      const existingTask = await prisma.processing_tasks.findUnique({
        where: { paperId: paperId },
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
        prisma.processing_tasks.create({
          data: {
            id: uuidv4(),
            paperId: paperId,
            status: 'pending',
            storageKey: storageKey,
            updatedAt: new Date(),
          },
        }),
        prisma.papers.update({
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
        await prisma.paper_batches.update({
          where: { id: paper.batchId },
          data: { uploadedCount: { increment: 1 } },
        });

        // Check if all files uploaded
        const batch = await prisma.paper_batches.findUnique({
          where: { id: paper.batchId },
          select: { uploadedCount: true, totalFiles: true },
        });

        if (batch && batch.uploadedCount === batch.totalFiles) {
          logger.info('All files uploaded for batch, triggering processing', {
            batchId: paper.batchId,
          });

          // Update batch status
          await prisma.paper_batches.update({
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
          paperId: paperId,
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

// POST /api/papers/upload - Direct file upload (for E2E tests and development)
router.post(
  '/upload',
  requirePermission('papers', 'create'),
  upload.single('file'),
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

      const file = req.file;
      
      if (!file) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'No file uploaded. Use form field name "file"',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      const filename = file.originalname;
      const title = filename.replace(/\.pdf$/i, '');

      // Check for duplicates
      const existingPaper = await prisma.papers.findFirst({
        where: { userId, title },
      });

      if (existingPaper) {
        return res.status(409).json({
          success: false,
          error: {
            type: '/errors/conflict',
            title: 'Duplicate Paper',
            status: 409,
            detail: `A paper with title "${title}" already exists`,
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
          data: { existingPaper: { id: existingPaper.id, title: existingPaper.title } },
        });
      }

      // Generate storage key
      const storageKey = generateStorageKey(userId, filename);
      const paperId = uuidv4();

      // Save file to storage
      if (USE_LOCAL_STORAGE) {
        await uploadToLocalStorage(storageKey, file.buffer);
      } else {
        return res.status(501).json({
          success: false,
          error: {
            type: '/errors/not-implemented',
            title: 'Not Implemented',
            status: 501,
            detail: 'Cloud storage not implemented, use local development mode',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Create paper record
      const paper = await prisma.papers.create({
        data: {
          id: paperId,
          title,
          authors: [],
          status: 'processing',
          userId,
          storageKey,
          fileSize: file.size,
          keywords: [],
          uploadStatus: 'completed',
          uploadProgress: 100,
          uploadedAt: new Date(),
          updatedAt: new Date(),
        },
      });

      // Create UploadHistory record (Task 3: wire upload history creation)
      const uploadHistoryId = uuidv4();
      const startTime = Date.now();
      await prisma.uploadHistory.create({
        data: {
          id: uploadHistoryId,
          userId,
          filename,
          status: 'PROCESSING',
          createdAt: new Date(),
          updatedAt: new Date(),
        },
      });

      logger.info(`Created UploadHistory record ${uploadHistoryId} for paper upload ${paperId}`, {
        userId,
        filename,
        paperId,
      });

      // Create processing task
      const task = await prisma.processing_tasks.create({
        data: {
          id: uuidv4(),
          paperId: paperId,
          status: 'pending',
          storageKey,
        },
      });

      // Store upload history context for later updates (Task 3)
      // Python service will populate chunksCount/llmTokens/etc. in future task
      // We track startTime for processingTime calculation

      // Trigger PDF processing via webhook endpoint
      await fetch(`http://localhost:${process.env.PORT || 4000}/api/papers/webhook`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Cookie': req.headers.cookie || '',
        },
        body: JSON.stringify({ paperId, storageKey }),
      });

      logger.info(`Direct upload completed for paper ${paperId}`, { filename, size: file.size });

      res.status(201).json({
        success: true,
        data: {
          paperId: paper.id,
          taskId: task.id,
          status: 'processing',
          message: 'File uploaded successfully. Processing started.',
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
      const paper = await prisma.papers.findFirst({
        where: { id: paperId, userId: userId },
        include: {
          processingTasks: {
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
      const effectiveStatus = paper.processingTasks?.status || paper.status;
      const progress = statusProgress[effectiveStatus] ?? getProgressPercent(effectiveStatus as TaskStatus);

      res.json({
        success: true,
        data: {
          paperId: paper.id,
          title: paper.title,
          status: effectiveStatus,
          progress,
          errorMessage: paper.processingTasks?.errorMessage || null,
          updatedAt: paper.processingTasks?.updatedAt || paper.updatedAt,
          completedAt: paper.processingTasks?.completedAt || null,
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

      const paper = await prisma.papers.findFirst({
        where: { id, userId: userId },
        include: {
          processingTasks: {
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
      const processingStatus = paper.processingTasks?.status as TaskStatus || paper.status;
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
          processingError: paper.processingTasks?.errorMessage || null,
          processingStartedAt: paper.processingTasks?.createdAt || null,
          processingCompletedAt: paper.processingTasks?.completedAt || null,
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

      const paper = await prisma.papers.findFirst({
        where: { id, userId: userId },
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
      const paper = await prisma.papers.findFirst({
        where: { id, userId: userId },
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
      const paper = await prisma.papers.findFirst({
        where: { id, userId: userId },
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
      const paper = await prisma.papers.findFirst({
        where: { id, userId: userId },
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

// PATCH /api/papers/:id/starred - Toggle starred status
router.patch(
  '/:id/starred',
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
      const { starred } = req.body;

      // Validate starred field
      if (typeof starred !== 'boolean') {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'starred field must be a boolean',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Verify paper exists and belongs to user
      const paper = await prisma.papers.findFirst({
        where: { id, userId: userId },
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

      // Update starred status
      const updated = await prisma.papers.update({
        where: { id },
        data: { starred },
        select: {
          id: true,
          title: true,
          starred: true,
          updatedAt: true,
        },
      });

      logger.info(`Paper ${id} starred status updated to ${starred}`, { userId });

      res.json({
        success: true,
        data: updated,
      });
    } catch (error) {
      logger.error('Failed to update starred status:', error);
      next(error);
    }
  }
);

// PATCH /api/papers/:id - Update paper metadata (title, authors, abstract, etc.)
// Used by PDF worker to update extracted metadata after parsing
router.patch(
  '/:id',
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
      const { title, authors, abstract, doi, keywords, uploadStatus, uploadProgress } = req.body;

      // Verify paper exists and belongs to user
      const paper = await prisma.papers.findFirst({
        where: { id, userId: userId },
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

      // Build update data (only include provided fields)
      const updateData: Record<string, any> = {};
      if (title !== undefined) updateData.title = title;
      if (authors !== undefined) updateData.authors = authors;
      if (abstract !== undefined) updateData.abstract = abstract;
      if (doi !== undefined) updateData.doi = doi;
      if (keywords !== undefined) updateData.keywords = keywords;
      if (uploadStatus !== undefined) updateData.uploadStatus = uploadStatus;
      if (uploadProgress !== undefined) updateData.uploadProgress = uploadProgress;

      // Ensure updatedAt is always updated
      updateData.updatedAt = new Date();

      // Update paper
      const updated = await prisma.papers.update({
        where: { id },
        data: updateData,
        select: {
          id: true,
          title: true,
          authors: true,
          abstract: true,
          doi: true,
          keywords: true,
          uploadStatus: true,
          uploadProgress: true,
          updatedAt: true,
        },
      });

      logger.info(`Paper ${id} metadata updated`, { 
        userId, 
        titleChanged: title !== undefined,
        newTitle: title 
      });

      res.json({
        success: true,
        data: updated,
      });
    } catch (error) {
      logger.error('Failed to update paper metadata:', error);
      next(error);
    }
  }
);

// POST /api/papers/batch/star - Batch star/unstar papers
router.post(
  '/batch/star',
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

      const { paperIds, starred } = req.body;

      // Validate input
      if (!paperIds || !Array.isArray(paperIds) || paperIds.length === 0) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'paperIds must be a non-empty array',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      if (typeof starred !== 'boolean') {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'starred field must be a boolean',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Limit batch size
      if (paperIds.length > 100) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'Cannot update more than 100 papers at once',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Update papers (only those belonging to user)
      const result = await prisma.papers.updateMany({
        where: {
          id: { in: paperIds },
          userId: userId,
        },
        data: {
          starred: starred,
          updatedAt: new Date(),
        },
      });

      logger.info(`Batch starred ${result.count} papers for user ${userId}`, {
        starred,
        requested: paperIds.length,
        updated: result.count,
      });

      res.json({
        success: true,
        data: {
          updatedCount: result.count,
          requestedCount: paperIds.length,
          starred: starred,
          message: `Successfully ${starred ? 'starred' : 'unstarred'} ${result.count} papers`,
        },
      });
    } catch (error) {
      logger.error('Failed to batch star papers:', error);
      next(error);
    }
  }
);

// POST /api/papers/batch-delete - Batch delete papers
router.post(
  '/batch-delete',
  requirePermission('papers', 'delete'),
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

      const { paperIds } = req.body;

      // Validate paperIds
      if (!paperIds || !Array.isArray(paperIds) || paperIds.length === 0) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'paperIds must be a non-empty array',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Limit batch size to prevent abuse
      if (paperIds.length > 100) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'Cannot delete more than 100 papers at once',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Verify all papers belong to user
      const papers = await prisma.papers.findMany({
        where: {
          id: { in: paperIds },
          userId: userId,
        },
        select: { id: true, storageKey: true },
      });

      if (papers.length !== paperIds.length) {
        const foundIds = papers.map(p => p.id);
        const missingIds = paperIds.filter(id => !foundIds.includes(id));
        logger.warn(`Batch delete: Some papers not found or not owned by user: ${missingIds.join(', ')}`);
      }

      // Delete papers in transaction
      const deleteResult = await prisma.$transaction(async (tx) => {
        // Delete papers (cascade will handle processing_tasks, etc.)
        const result = await tx.papers.deleteMany({
          where: {
            id: { in: paperIds },
            userId: userId,
          },
        });

        return result;
      });

      // Delete from object storage
      for (const paper of papers) {
        if (paper.storageKey) {
          try {
            const { deleteObject } = await import('../services/storage.js');
            await deleteObject(paper.storageKey);
            logger.info(`Deleted object ${paper.storageKey} from storage`);
          } catch (storageError) {
            logger.warn(`Failed to delete object ${paper.storageKey} from storage:`, storageError);
          }
        }
      }

      logger.info(`Batch deleted ${deleteResult.count} papers for user ${userId}`);

      res.json({
        success: true,
        data: {
          deletedCount: deleteResult.count,
          requestedCount: paperIds.length,
          message: `Successfully deleted ${deleteResult.count} papers`,
        },
      });
    } catch (error) {
      next(error);
    }
  }
);

// DELETE /api/papers/:id - Delete paper
router.delete(
  '/:id',
  requirePermission('papers', 'delete'),
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
      const paper = await prisma.papers.findFirst({
        where: { id, userId: userId },
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
      await prisma.papers.delete({
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
