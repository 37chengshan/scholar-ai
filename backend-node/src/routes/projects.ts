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

// GET /api/projects - List user's projects
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

    const projects = await prisma.projects.findMany({
      where: { userId: userId },
      orderBy: { createdAt: 'desc' },
      include: {
        _count: {
          select: { papers: true },
        },
      },
    });

    res.json({
      success: true,
      data: projects.map(p => ({
        ...p,
        paperCount: p._count.papers,
        _count: undefined,
      })),
    });
  } catch (error) {
    next(error);
  }
});

// POST /api/projects - Create a new project
router.post('/', requirePermission('papers', 'create'), async (req: AuthRequest, res, next) => {
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

    const { name, color } = req.body;

    // Validate required fields
    if (!name || typeof name !== 'string' || name.trim().length === 0) {
      return res.status(400).json({
        success: false,
        error: {
          type: '/errors/validation-error',
          title: 'Validation Error',
          status: 400,
          detail: 'Project name is required',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
    }

    // Validate color format (hex color)
    const colorRegex = /^#[0-9A-Fa-f]{6}$/;
    const projectColor = color && colorRegex.test(color) ? color : '#3B82F6';

    const project = await prisma.projects.create({
      data: { id: uuidv4(), updatedAt: new Date(),
        userId: userId,
        name: name.trim(),
        color: projectColor,
      },
    });

    logger.info(`Project created: ${project.id}`, { userId, name });

    res.status(201).json({
      success: true,
      data: project,
    });
  } catch (error) {
    next(error);
  }
});

// PATCH /api/projects/:id - Update project
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
    const { name, color } = req.body;

    // Validate at least one field provided
    if (!name && !color) {
      return res.status(400).json({
        success: false,
        error: {
          type: '/errors/validation-error',
          title: 'Validation Error',
          status: 400,
          detail: 'At least one field (name or color) is required',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
    }

    // Verify project exists and belongs to user
    const existing = await prisma.projects.findFirst({
      where: { id, userId: userId },
    });

    if (!existing) {
      return res.status(404).json({
        success: false,
        error: {
          type: '/errors/not-found',
          title: 'Not Found',
          status: 404,
          detail: 'Project not found',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
    }

    // Validate color format if provided
    const colorRegex = /^#[0-9A-Fa-f]{6}$/;
    const updates: { name?: string; color?: string } = {};
    if (name) updates.name = name.trim();
    if (color && colorRegex.test(color)) updates.color = color;

    const updated = await prisma.projects.update({
      where: { id },
      data: updates,
    });

    logger.info(`Project updated: ${id}`, { userId, updates });

    res.json({
      success: true,
      data: updated,
    });
  } catch (error) {
    next(error);
  }
});

// DELETE /api/projects/:id - Delete project
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

    // Verify project exists and belongs to user
    const project = await prisma.projects.findFirst({
      where: { id, userId: userId },
    });

    if (!project) {
      return res.status(404).json({
        success: false,
        error: {
          type: '/errors/not-found',
          title: 'Not Found',
          status: 404,
          detail: 'Project not found',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
    }

    // Delete project (papers will have projectId set to null via SetNull)
    await prisma.projects.delete({
      where: { id },
    });

    logger.info(`Project deleted: ${id}`, { userId });

    res.json({
      success: true,
      data: { id, deleted: true },
    });
  } catch (error) {
    next(error);
  }
});

// PATCH /api/papers/:id/project - Assign paper to project
router.patch('/paper/:paperId', requirePermission('papers', 'update'), async (req: AuthRequest, res, next) => {
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
    const { projectId } = req.body;

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

    // If projectId is provided, verify it exists and belongs to user
    if (projectId) {
      const project = await prisma.projects.findFirst({
        where: { id: projectId, userId: userId },
      });

      if (!project) {
        return res.status(404).json({
          success: false,
          error: {
            type: '/errors/not-found',
            title: 'Not Found',
            status: 404,
            detail: 'Project not found',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }
    }

    // Update paper's project
    const updated = await prisma.papers.update({
      where: { id: paperId },
      data: { projectId: projectId || null },
      select: {
        id: true,
        title: true,
        projectId: true,
      },
    });

    logger.info(`Paper ${paperId} assigned to project ${projectId || 'none'}`, { userId });

    res.json({
      success: true,
      data: updated,
    });
  } catch (error) {
    next(error);
  }
});

export { router as projectsRouter };