import { Router } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';
import { authenticate } from '../middleware/auth';
import { prisma } from '../config/database';
import { AuthRequest } from '../types/auth';

const router = Router();

// All routes require authentication
router.use(authenticate);

// GET /api/dashboard/stats - Get dashboard statistics
router.get('/stats', async (req: AuthRequest, res, next) => {
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

    // Run all aggregations in parallel
    const [
      totalPapers,
      starredPapers,
      processingPapers,
      completedPapers,
      queriesCount,
      sessionsCount,
      projectsCount,
      tokensResult,
    ] = await Promise.all([
      prisma.paper.count({ where: { userId } }),
      prisma.paper.count({ where: { userId, starred: true } }),
      prisma.paper.count({ where: { userId, status: 'processing' } }),
      prisma.paper.count({ where: { userId, status: 'completed' } }),
      prisma.query.count({ where: { userId } }),
      prisma.session.count({ where: { userId } }),
      prisma.project.count({ where: { userId } }),
      prisma.chatMessage.aggregate({
        where: { session: { userId } },
        _sum: { tokensUsed: true },
      }),
    ]);

    const llmTokens = tokensResult._sum.tokensUsed || 0;

    res.json({
      success: true,
      data: {
        totalPapers,
        starredPapers,
        processingPapers,
        completedPapers,
        queriesCount,
        sessionsCount,
        projectsCount,
        llmTokens,
      },
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/dashboard/trends - Get time-series data
router.get('/trends', async (req: AuthRequest, res, next) => {
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

    const { period = 'weekly' } = req.query;
    const days = period === 'monthly' ? 30 : 7;
    const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000);

    // Get papers created in the time range
    const papers = await prisma.paper.findMany({
      where: {
        userId,
        createdAt: { gte: since },
      },
      select: { createdAt: true },
    });

    // Get queries in the time range
    const queries = await prisma.query.findMany({
      where: {
        userId,
        createdAt: { gte: since },
      },
      select: { createdAt: true },
    });

    // Group by day
    const dataPoints: Array<{ date: string; papers: number; queries: number }> = [];

    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(Date.now() - i * 24 * 60 * 60 * 1000);
      const dateStr = date.toISOString().split('T')[0];
      const dayStart = new Date(dateStr);
      const dayEnd = new Date(dateStr + 'T23:59:59.999Z');

      const papersCount = papers.filter(p => p.createdAt >= dayStart && p.createdAt <= dayEnd).length;
      const queriesCount = queries.filter(q => q.createdAt >= dayStart && q.createdAt <= dayEnd).length;

      dataPoints.push({
        date: dateStr,
        papers: papersCount,
        queries: queriesCount,
      });
    }

    res.json({
      success: true,
      data: {
        dataPoints,
        period,
      },
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/dashboard/recent-papers - Get recently accessed papers
router.get('/recent-papers', async (req: AuthRequest, res, next) => {
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

    const limit = Math.min(10, parseInt(req.query.limit as string, 10) || 5);

    // Get recent papers by reading progress
    const recentProgress = await prisma.readingProgress.findMany({
      where: { userId },
      orderBy: { lastReadAt: 'desc' },
      take: limit,
      include: {
        paper: {
          select: {
            id: true,
            title: true,
            authors: true,
            year: true,
            starred: true,
            status: true,
            pageCount: true,
          },
        },
      },
    });

    const recentPapers = recentProgress.map(rp => ({
      ...rp.paper,
      currentPage: rp.currentPage,
      lastReadAt: rp.lastReadAt,
      progress: rp.totalPages ? Math.round((rp.currentPage / rp.totalPages) * 100) : 0,
    }));

    res.json({
      success: true,
      data: recentPapers,
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/dashboard/reading-stats - Get reading statistics
router.get('/reading-stats', async (req: AuthRequest, res, next) => {
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

    // Get all reading progress
    const allProgress = await prisma.readingProgress.findMany({
      where: { userId },
      include: {
        paper: {
          select: { pageCount: true },
        },
      },
    });

    // Calculate statistics
    const totalPapersWithProgress = allProgress.length;
    const totalPagesRead = allProgress.reduce((sum, rp) => sum + rp.currentPage, 0);
    const completedPapers = allProgress.filter(
      rp => rp.paper.pageCount && rp.currentPage >= rp.paper.pageCount
    ).length;

    // Average progress
    const avgProgress = allProgress.length > 0
      ? allProgress.reduce((sum, rp) => {
          const progress = rp.paper.pageCount
            ? Math.min(100, Math.round((rp.currentPage / rp.paper.pageCount) * 100))
            : 0;
          return sum + progress;
        }, 0) / allProgress.length
      : 0;

    res.json({
      success: true,
      data: {
        totalPapersWithProgress,
        totalPagesRead,
        completedPapers,
        averageProgress: Math.round(avgProgress),
      },
    });
  } catch (error) {
    next(error);
  }
});

export { router as dashboardRouter };