import { Router } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';
import { authenticate } from '../middleware/auth';
import { requirePermission } from '../middleware/rbac';
import { prisma } from '../config/database';
import { AuthRequest } from '../types/auth';

const router = Router();

// All routes require authentication
router.use(authenticate);

// GET /api/reading-progress/:paperId - Get user's reading progress for a paper
router.get('/:paperId', requirePermission('papers', 'read'), async (req: AuthRequest, res, next) => {
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

    const { paperId } = req.params;

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

    // Get reading progress
    const progress = await prisma.readingProgress.findUnique({
      where: {
        paperId_userId: { paperId, userId },
      },
    });

    res.json({
      success: true,
      data: progress || {
        paperId,
        userId,
        currentPage: 1,
        totalPages: paper.pageCount || null,
        lastReadAt: null,
      },
    });
  } catch (error) {
    next(error);
  }
});

// POST /api/reading-progress/:paperId - Upsert reading progress
router.post('/:paperId', requirePermission('papers', 'read'), async (req: AuthRequest, res, next) => {
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

    const { paperId } = req.params;
    const { currentPage, totalPages } = req.body;

    // Validate currentPage
    if (typeof currentPage !== 'number' || currentPage < 1) {
      return res.status(400).json({
        success: false,
        error: {
          type: '/errors/validation-error',
          title: 'Validation Error',
          status: 400,
          detail: 'currentPage must be a positive integer',
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

    // Upsert reading progress
    const progress = await prisma.readingProgress.upsert({
      where: {
        paperId_userId: { paperId, userId },
      },
      update: {
        currentPage,
        totalPages: totalPages || paper.pageCount || null,
        lastReadAt: new Date(),
      },
      create: {
        paperId,
        userId,
        currentPage,
        totalPages: totalPages || paper.pageCount || null,
      },
    });

    logger.info(`Reading progress updated: paper=${paperId}, page=${currentPage}`, { userId });

    res.json({
      success: true,
      data: progress,
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/reading-progress - Get all reading progress for user
router.get('/', requirePermission('papers', 'read'), async (req: AuthRequest, res, next) => {
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

    // Get all reading progress for user with paper details
    const progressList = await prisma.readingProgress.findMany({
      where: { userId },
      orderBy: { lastReadAt: 'desc' },
      include: {
        paper: {
          select: {
            id: true,
            title: true,
            authors: true,
            pageCount: true,
          },
        },
      },
    });

    res.json({
      success: true,
      data: progressList,
    });
  } catch (error) {
    next(error);
  }
});

export { router as readingProgressRouter };