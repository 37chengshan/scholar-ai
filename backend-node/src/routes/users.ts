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

// PATCH /api/users/me - Update user profile
router.patch('/me', authenticate, async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { name, email, avatar } = req.body;

    // Validate at least one field provided
    if (!name && !email && !avatar) {
      throw Errors.validation('At least one field (name, email, avatar) required');
    }

    // Build update object
    const updates: { name?: string; email?: string; avatar?: string } = {};
    if (name) updates.name = name;
    if (email) {
      // Check email uniqueness
      const existingUser = await prisma.user.findUnique({ where: { email } });
      if (existingUser && existingUser.id !== userId) {
        throw Errors.validation('Email already in use');
      }
      updates.email = email;
    }
    if (avatar) updates.avatar = avatar;

    const user = await prisma.user.update({
      where: { id: userId },
      data: updates,
      select: { id: true, name: true, email: true, avatar: true },
    });

    logger.info('Profile updated', { userId, fields: Object.keys(updates) });

    res.json({
      success: true,
      data: user,
    });

  } catch (error) {
    next(error);
  }
});

// POST /api/users/me/avatar - Upload avatar
router.post('/me/avatar', authenticate, upload.single('avatar'), async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

    if (!req.file) {
      throw Errors.validation('Avatar file required');
    }

    // Validate file type (image only)
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(req.file.mimetype)) {
      throw Errors.validation('Invalid file type. Allowed: JPEG, PNG, WebP');
    }

    // Upload to S3/MinIO
    const filename = `avatars/${userId}-${Date.now()}.${req.file.mimetype.split('/')[1]}`;
    const avatarUrl = await uploadFile(
      userId,
      req.file.buffer,
      filename,
      req.file.mimetype
    );

    // Update user avatar URL
    await prisma.user.update({
      where: { id: userId },
      data: { avatar: avatarUrl },
    });

    logger.info('Avatar uploaded', { userId, url: avatarUrl });

    res.json({
      success: true,
      data: { avatar: avatarUrl },
    });

  } catch (error) {
    next(error);
  }
});

// GET /api/users/me/settings - Get user preferences
router.get('/me/settings', authenticate, async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;

    const user = await prisma.user.findUnique({
      where: { id: userId },
      select: { settings: true },
    });

    if (!user) {
      throw Errors.notFound('User not found');
    }

    // Default settings if null
    const settings = user.settings || {
      language: 'zh',
      defaultModel: 'glm-4-flash',
      theme: 'light',
    };

    res.json({
      success: true,
      data: settings,
    });

  } catch (error) {
    next(error);
  }
});

// PATCH /api/users/me/settings - Update user preferences
router.patch('/me/settings', authenticate, async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { language, defaultModel, theme } = req.body;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

    // Validate language
    if (language && !['zh', 'en'].includes(language)) {
      throw Errors.validation('Invalid language. Allowed: zh, en');
    }

    // Validate theme
    if (theme && !['light', 'dark'].includes(theme)) {
      throw Errors.validation('Invalid theme. Allowed: light, dark');
    }

    // Get current settings or default
    const user = await prisma.user.findUnique({
      where: { id: userId },
      select: { settings: true },
    });

    const defaultSettings = { language: 'zh', defaultModel: 'glm-4-flash', theme: 'light' };
    const currentSettings = (user?.settings as Record<string, unknown>) || defaultSettings;

    // Merge updates
    const updatedSettings = {
      ...currentSettings,
      ...(language && { language }),
      ...(defaultModel && { defaultModel }),
      ...(theme && { theme }),
    };

    await prisma.user.update({
      where: { id: userId },
      data: { settings: updatedSettings },
    });

    logger.info('Settings updated', { userId, settings: updatedSettings });

    res.json({
      success: true,
      data: updatedSettings,
    });

  } catch (error) {
    next(error);
  }
});

// PATCH /api/users/me/password - Change password
router.patch('/me/password', authenticate, requireReauth, async (req: ReauthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { newPassword } = req.body;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

    // requireReauth already validated currentPassword
    if (!req.reauthVerified) {
      throw Errors.validation('Re-authentication required');
    }

    // Validate new password strength
    if (!newPassword || newPassword.length < 8) {
      throw Errors.validation('New password must be at least 8 characters');
    }

    // Hash new password
    const passwordHash = await hashPassword(newPassword);

    // Update user password
    await prisma.user.update({
      where: { id: userId },
      data: { passwordHash },
    });

    logger.info('Password changed', { userId });

    // Invalidate all refresh tokens (security measure)
    await prisma.refreshToken.deleteMany({
      where: { userId },
    });

    res.json({
      success: true,
      data: { message: 'Password changed successfully. Please log in again.' },
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

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

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
router.delete('/me/api-keys/:keyId', authenticate, requireReauth, async (req: ReauthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { keyId } = req.params;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

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
