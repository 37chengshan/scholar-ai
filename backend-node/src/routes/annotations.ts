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

// GET /api/annotations/:paperId - List annotations for a paper
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

    // Get all annotations for this paper by the user
    const annotations = await prisma.annotations.findMany({
      where: { paperId: paperId, userId: userId },
      orderBy: [{ page_number: 'asc' }, { createdAt: 'asc' }],
    });

    res.json({
      success: true,
      data: annotations,
    });
  } catch (error) {
    next(error);
  }
});

// POST /api/annotations - Create annotation
router.post('/', requirePermission('papers', 'update'), async (req: AuthRequest, res, next) => {
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

    const { paperId, type, pageNumber, position, content, color } = req.body;

    // Validate required fields
    if (!paperId || !type || pageNumber === undefined || !position) {
      return res.status(400).json({
        success: false,
        error: {
          type: '/errors/validation-error',
          title: 'Validation Error',
          status: 400,
          detail: 'paperId, type, pageNumber, and position are required',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
    }

    // Validate annotation type
    const validTypes = ['highlight', 'note', 'bookmark'];
    if (!validTypes.includes(type)) {
      return res.status(400).json({
        success: false,
        error: {
          type: '/errors/validation-error',
          title: 'Validation Error',
          status: 400,
          detail: `Invalid annotation type. Must be one of: ${validTypes.join(', ')}`,
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
    }

    // Validate pageNumber
    if (typeof pageNumber !== 'number' || pageNumber < 1) {
      return res.status(400).json({
        success: false,
        error: {
          type: '/errors/validation-error',
          title: 'Validation Error',
          status: 400,
          detail: 'pageNumber must be a positive integer',
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

    // Validate color format if provided
    const colorRegex = /^#[0-9A-Fa-f]{6}$/;
    const annotationColor = color && colorRegex.test(color) ? color : '#FFEB3B';

    const annotation = await prisma.annotations.create({
      data: {
        id: uuidv4(),
        paperId: paperId,
        userId: userId,
        type,
        page_number: pageNumber,
        position,
        content: content || null,
        color: annotationColor,
        createdAt: new Date(),
        updatedAt: new Date(),
      },
    });

    logger.info(`Annotation created: ${annotation.id}`, { userId, paperId, type });

    res.status(201).json({
      success: true,
      data: annotation,
    });
  } catch (error) {
    next(error);
  }
});

// PATCH /api/annotations/:id - Update annotation
router.patch('/:id', requirePermission('papers', 'update'), async (req: AuthRequest, res, next) => {
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
    const { content, color } = req.body;

    // Verify annotation exists and belongs to user
    const annotation = await prisma.annotations.findFirst({
      where: { id, userId: userId },
    });

    if (!annotation) {
      return res.status(404).json({
        success: false,
        error: {
          type: '/errors/not-found',
          title: 'Not Found',
          status: 404,
          detail: 'Annotation not found',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
    }

    // Validate at least one field provided
    if (content === undefined && !color) {
      return res.status(400).json({
        success: false,
        error: {
          type: '/errors/validation-error',
          title: 'Validation Error',
          status: 400,
          detail: 'At least one field (content or color) is required',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
    }

    // Validate color format if provided
    const colorRegex = /^#[0-9A-Fa-f]{6}$/;
    const updates: { content?: string | null; color?: string } = {};
    if (content !== undefined) updates.content = content || null;
    if (color && colorRegex.test(color)) updates.color = color;

    const updated = await prisma.annotations.update({
      where: { id },
      data: updates,
    });

    logger.info(`Annotation updated: ${id}`, { userId });

    res.json({
      success: true,
      data: updated,
    });
  } catch (error) {
    next(error);
  }
});

// DELETE /api/annotations/:id - Delete annotation
router.delete('/:id', requirePermission('papers', 'update'), async (req: AuthRequest, res, next) => {
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

    // Verify annotation exists and belongs to user
    const annotation = await prisma.annotations.findFirst({
      where: { id, userId: userId },
    });

    if (!annotation) {
      return res.status(404).json({
        success: false,
        error: {
          type: '/errors/not-found',
          title: 'Not Found',
          status: 404,
          detail: 'Annotation not found',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
    }

    await prisma.annotations.delete({
      where: { id },
    });

    logger.info(`Annotation deleted: ${id}`, { userId });

    res.json({
      success: true,
      data: { id, deleted: true },
    });
  } catch (error) {
    next(error);
  }
});

export { router as annotationsRouter };