import { Router } from 'express';
import { authenticate } from '../middleware/auth';
import { requirePermission } from '../middleware/rbac';
import { prisma } from '../config/database';
import { AuthRequest } from '../types/auth';

const router = Router();

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

// GET /api/users/:id/stats - 获取用户统计
router.get('/:id/stats', authenticate, requirePermission('profile', 'read'), async (req, res, next) => {
  try {
    const { id } = req.params;
    // TODO: 实现获取用户统计
    res.json({
      success: true,
      data: {
        userId: id,
        paperCount: 0,
        queryCount: 0,
        knowledgeMapCount: 0
      }
    });
  } catch (error) {
    next(error);
  }
});

export { router as usersRouter };
