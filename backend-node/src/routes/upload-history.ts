import { Router } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';
import { authenticate } from '../middleware/auth';
import { requirePermission } from '../middleware/rbac';
import { prisma } from '../config/database';
import { AuthRequest } from '../types/auth';

const router = Router();

// Apply authentication to all routes
router.use(authenticate);

// GET /api/upload-history - List upload history records with pagination
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

    // Parse pagination parameters
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit as string, 10) || 50));
    const offset = Math.max(0, parseInt(req.query.offset as string, 10) || 0);

    // Query upload history records for the current user
    const records = await prisma.uploadHistory.findMany({
      where: { userId },
      skip: offset,
      take: limit,
      orderBy: { createdAt: 'desc' },
      include: {
        user: {
          select: {
            id: true,
            email: true,
            name: true,
          },
        },
      },
    });

    // Get total count
    const total = await prisma.uploadHistory.count({ where: { userId } });

    logger.info(`Retrieved ${records.length} upload history records for user ${userId}`, {
      userId,
      limit,
      offset,
      total,
    });

    res.json({
      success: true,
      data: {
        records,
        total,
      },
    });
  } catch (error) {
    logger.error('Failed to retrieve upload history:', error);
    next(error);
  }
});

// GET /api/upload-history/:id - Get detailed upload history record
router.get('/:id', requirePermission('papers', 'read'), async (req: AuthRequest, res, next) => {
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

    // Query upload history record with all details
    const record = await prisma.uploadHistory.findFirst({
      where: { id, userId }, // Enforce user isolation
      include: {
        user: {
          select: {
            id: true,
            email: true,
            name: true,
          },
        },
        paper: {
          select: {
            id: true,
            title: true,
            storageKey: true,
          },
        },
      },
    });

    if (!record) {
      return res.status(404).json({
        success: false,
        error: {
          type: '/errors/not-found',
          title: 'Not Found',
          status: 404,
          detail: 'Upload history record not found',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
    }

    logger.info(`Retrieved upload history record ${id} for user ${userId}`, {
      userId,
      recordId: id,
      paperId: record.paperId,
    });

    res.json({
      success: true,
      data: record,
    });
  } catch (error) {
    logger.error('Failed to retrieve upload history record:', error);
    next(error);
  }
});

// DELETE /api/upload-history/:id - Delete upload history record (safe deletion)
router.delete('/:id', requirePermission('papers', 'delete'), async (req: AuthRequest, res, next) => {
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

    // Verify record exists and belongs to user (user isolation)
    const record = await prisma.uploadHistory.findFirst({
      where: { id, userId },
    });

    if (!record) {
      return res.status(404).json({
        success: false,
        error: {
          type: '/errors/not-found',
          title: 'Not Found',
          status: 404,
          detail: 'Upload history record not found',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
    }

    // Delete history record only (paper remains in library per D-01)
    await prisma.uploadHistory.delete({
      where: { id },
    });

    logger.info(`Deleted upload history record ${id} for user ${userId}`, {
      userId,
      recordId: id,
      paperId: record.paperId,
      paperPreserved: !!record.paperId,
    });

    res.json({
      success: true,
      data: {
        message: 'Upload history record deleted successfully',
        paperPreserved: !!record.paperId,
      },
    });
  } catch (error) {
    logger.error('Failed to delete upload history record:', error);
    next(error);
  }
});

export { router as uploadHistoryRouter };