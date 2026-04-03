import { Router } from 'express';
import crypto from 'crypto';
import multer from 'multer';
import { authenticate } from '../middleware/auth';
import { requirePermission } from '../middleware/rbac';
import { requireReauth, ReauthRequest } from '../middleware/reauth';
import { prisma } from '../config/database';
import { AuthRequest } from '../types/auth';
import { hashPassword } from '../utils/crypto';
import { uploadFile } from '../services/storage';
import { Errors } from '../middleware/errorHandler';
import { logger } from '../utils/logger';

const router = Router();

// Multer configuration for avatar upload (5MB max, memory storage)
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 5 * 1024 * 1024 }, // 5MB max
});

// Generate API key: sk_live_xxxx format
const generateApiKey = (): string => {
  const randomBytes = crypto.randomBytes(32).toString('base64url');
  return `sk_live_${randomBytes}`;
};

// GET /api/users/me - 获取当前用户信息
router.get('/me', authenticate, async (req: AuthRequest, res, next) => {
  try {
    // 从 JWT token 获取用户ID，查询数据库获取真实用户信息
    const userId = req.user?.sub;
    if (!userId) {
      return res.status(401).json({
        success: false,
        error: {
          message: 'Unauthorized',
          code: 'UNAUTHORIZED'
        }
      });
    }

    const user = await prisma.user.findUnique({
      where: { id: userId },
      select: {
        id: true,
        email: true,
        name: true,
        emailVerified: true,
        avatar: true,
        createdAt: true,
        updatedAt: true
      }
    });

    if (!user) {
      return res.status(404).json({
        success: false,
        error: {
          message: 'User not found',
          code: 'USER_NOT_FOUND'
        }
      });
    }

    res.json({
      success: true,
      data: user
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/users/:id/stats - Get user statistics for Dashboard
router.get('/:id/stats', authenticate, async (req: AuthRequest, res, next) => {
  try {
    const userId = req.params.id;
    const currentUserId = req.user?.sub;

    // Only allow users to view their own stats (or admin)
    if (userId !== currentUserId && req.user?.roles?.includes('admin') !== true) {
      return res.status(403).json({
        success: false,
        error: {
          message: 'Cannot view other user stats',
          code: 'FORBIDDEN'
        }
      });
    }

    // 1. Basic counts
    const [paperCount, entityCount, queryCount, sessionCount] = await Promise.all([
      prisma.paper.count({ where: { userId } }),
      prisma.paperChunk.count({ where: { paper: { userId } } }),
      prisma.query.count({ where: { userId } }),
      prisma.session.count({ where: { userId } }),
    ]);

    // 2. LLM Tokens (aggregate from chat messages)
    const tokensResult = await prisma.chatMessage.aggregate({
      where: { session: { userId } },
      _sum: { tokensUsed: true },
    });
    const llmTokens = tokensResult._sum.tokensUsed || 0;

    // 3. Weekly trend (last 7 days)
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

    const weeklyTrend = await prisma.$queryRaw<
      Array<{ date: Date; papers: number; queries: number; tokens: number }>
    >`
      SELECT DATE(created_at) as date,
             COUNT(*) FILTER (WHERE type = 'paper') as papers,
             COUNT(*) FILTER (WHERE type = 'query') as queries,
             SUM(tokens_used) as tokens
      FROM (
        SELECT created_at, 'paper' as type, 0 as tokens_used FROM papers WHERE user_id = ${userId}
        UNION ALL
        SELECT created_at, 'query' as type, 0 as tokens_used FROM queries WHERE user_id = ${userId}
      ) combined
      WHERE created_at >= ${sevenDaysAgo}
      GROUP BY DATE(created_at)
      ORDER BY date
    `;

    // 4. Subject distribution (extract from keywords)
    const subjectDistribution = await prisma.$queryRaw<
      Array<{ name: string; value: number }>
    >`
      SELECT keyword as name, COUNT(*) as value
      FROM papers, unnest(keywords) as keyword
      WHERE user_id = ${userId}
      GROUP BY keyword
      ORDER BY COUNT(*) DESC
      LIMIT 4
    `;

    // 5. Storage usage (placeholder - Python internal endpoint)
    // TODO: Call Python /internal/storage-stats when available
    const storageUsage = {
      vectorDB: { used: 1.2, total: 5 },
      blobStorage: { used: 14.5, total: 50 },
    };

    res.json({
      success: true,
      data: {
        paperCount,
        entityCount,
        llmTokens,
        queryCount,
        sessionCount,
        weeklyTrend: weeklyTrend.map((row) => ({
          date: row.date.toISOString().split('T')[0],
          papers: Number(row.papers),
          queries: Number(row.queries),
          tokens: Number(row.tokens),
        })),
        subjectDistribution,
        storageUsage,
      },
    });

  } catch (error) {
    next(error);
  }
});

// GET /api/users/me/api-keys - List user API keys
router.get('/me/api-keys', authenticate, async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;

    const apiKeys = await prisma.apiKey.findMany({
      where: { userId },
      select: {
        id: true,
        name: true,
        prefix: true,
        createdAt: true,
        lastUsedAt: true,
      },
      orderBy: { createdAt: 'desc' },
    });

    logger.info('API keys listed', { userId, count: apiKeys.length });

    res.json({
      success: true,
      data: apiKeys,
    });

  } catch (error) {
    next(error);
  }
});

// POST /api/users/me/api-keys - Create new API key
router.post('/me/api-keys', authenticate, async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { name } = req.body;

    if (!name || name.length < 1) {
      throw Errors.validation('API key name required');
    }

    // Generate key
    const apiKey = generateApiKey();
    const prefix = apiKey.substring(0, 12); // "sk_live_abc"

    // Hash key (reuse Argon2 from crypto utils)
    const keyHash = await hashPassword(apiKey);

    // Save to database
    const newKey = await prisma.apiKey.create({
      data: {
        userId,
        name,
        keyHash,
        prefix,
      },
      select: {
        id: true,
        name: true,
        prefix: true,
        createdAt: true,
      },
    });

    logger.info('API key created', { userId, keyId: newKey.id, name });

    // Return full key ONLY on creation (never again)
    res.json({
      success: true,
      data: {
        ...newKey,
        key: apiKey, // Full key shown once
        message: 'Save this key securely. It will not be shown again.',
      },
    });

  } catch (error) {
    next(error);
  }
});

// DELETE /api/users/me/api-keys/:keyId - Delete API key
router.delete('/me/api-keys/:keyId', authenticate, requireReauth, async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { keyId } = req.params;

    // requireReauth already validated currentPassword
    if (!req.reauthVerified) {
      throw Errors.validation('Re-authentication required');
    }

    // Verify ownership
    const apiKey = await prisma.apiKey.findFirst({
      where: { id: keyId, userId },
    });

    if (!apiKey) {
      throw Errors.notFound('API key not found');
    }

    // Delete key
    await prisma.apiKey.delete({
      where: { id: keyId },
    });

    logger.info('API key deleted', { userId, keyId });

    res.json({
      success: true,
      data: { message: 'API key deleted' },
    });

  } catch (error) {
    next(error);
  }
});

export { router as usersRouter };
