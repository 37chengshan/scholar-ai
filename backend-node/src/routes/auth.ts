import { Router, Response, NextFunction } from 'express';
import { z } from 'zod';
import { v4 as uuidv4 } from 'uuid';
import { prisma } from '../config/database';
import { redisClient } from '../config/redis';
import { hashPassword, verifyPassword } from '../utils/crypto';
import {
  generateAccessToken,
  generateRefreshToken,
  verifyAccessToken,
  verifyRefreshToken,
} from '../utils/jwt';
import { AuthRequest, ErrorTypes } from '../types/auth';
import { Errors } from '../middleware/errorHandler';
import { COOKIE_SETTINGS } from '../config/auth';
import { authenticate } from '../middleware/auth';
import { logger } from '../utils/logger';

const router = Router();

// Validation schemas
const registerSchema = z.object({
  email: z.string().email('Invalid email format'),
  password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/[0-9]/, 'Password must contain at least one number'),
  name: z.string().min(2, 'Name must be at least 2 characters').max(50, 'Name must be less than 50 characters'),
});

const loginSchema = z.object({
  email: z.string().email('Invalid email format'),
  password: z.string().min(1, 'Password is required'),
});

/**
 * POST /api/auth/register
 * Register a new user with default 'user' role
 */
router.post('/register', async (req, res, next) => {
  try {
    // Validate input
    const result = registerSchema.safeParse(req.body);
    if (!result.success) {
      const errors = result.error.errors.map((e) => e.message).join(', ');
      res.status(400).json({
        success: false,
        error: {
          type: ErrorTypes.VALIDATION_ERROR,
          title: 'Validation Error',
          status: 400,
          detail: errors,
          instance: '/api/auth/register',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    const { email, password, name } = result.data;

    // Check if email already exists
    const existingUser = await prisma.users.findUnique({
      where: { email },
    });

    if (existingUser) {
      res.status(409).json({
        success: false,
        error: {
          type: ErrorTypes.CONFLICT,
          title: 'Conflict',
          status: 409,
          detail: 'Email already registered',
          instance: '/api/auth/register',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    // Hash password
    const passwordHash = await hashPassword(password);
    
    const userId = uuidv4();

    // Create user first
    const user = await prisma.users.create({
      data: {
        id: userId,
        email,
        name,
        passwordHash: passwordHash,
        emailVerified: true,
        updatedAt: new Date(),
      },
    });

    // Assign 'user' role - must query the actual role ID
    const userRole = await prisma.roles.findUnique({
      where: { name: 'user' },
    });

    if (!userRole) {
      throw Errors.internal('Default user role not found. Please run database seed.');
    }

    await prisma.user_roles.create({
      data: {
        id: uuidv4(),
        userId: userId,
        role_id: userRole.id,
      },
    });

    // Fetch user with roles
const userWithRoles = await prisma.users.findUnique({
      where: { id: user.id },
      include: {
        userRoles: {
          include: {
            roles: true,
          },
        },
      },
    });

    if (!userWithRoles) {
      throw Errors.internal('Failed to fetch created user');
    }

    logger.info({
      message: 'User registered',
      userId: userWithRoles.id,
      email: userWithRoles.email,
    });

    // Return user without password
    res.status(201).json({
      success: true,
      data: {
        id: userWithRoles.id,
        email: userWithRoles.email,
        name: userWithRoles.name,
        emailVerified: userWithRoles.emailVerified,
        roles: userWithRoles.userRoles.map((ur) => ur.roles.name),
        createdAt: userWithRoles.createdAt,
      },
      meta: {
        requestId: uuidv4(),
        timestamp: new Date().toISOString(),
      },
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/auth/login
 * Authenticate user and set cookies
 */
router.post('/login', async (req, res, next) => {
  try {
    // Validate input
    const result = loginSchema.safeParse(req.body);
    if (!result.success) {
      const errors = result.error.errors.map((e) => e.message).join(', ');
      res.status(400).json({
        success: false,
        error: {
          type: ErrorTypes.VALIDATION_ERROR,
          title: 'Validation Error',
          status: 400,
          detail: errors,
          instance: '/api/auth/login',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    const { email, password } = result.data;

    // Find user by email
    const user = await prisma.users.findUnique({
      where: { email },
      include: {
        userRoles: {
          include: {
            roles: true,
          },
        },
      },
    });

    if (!user) {
      res.status(401).json({
        success: false,
        error: {
          type: ErrorTypes.INVALID_CREDENTIALS,
          title: 'Invalid Credentials',
          status: 401,
          detail: 'Email or password is incorrect',
          instance: '/api/auth/login',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    // Verify password
    const isPasswordValid = await verifyPassword(user.passwordHash, password);
    if (!isPasswordValid) {
      res.status(401).json({
        success: false,
        error: {
          type: ErrorTypes.INVALID_CREDENTIALS,
          title: 'Invalid Credentials',
          status: 401,
          detail: 'Email or password is incorrect',
          instance: '/api/auth/login',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    // Get user roles
    const roles = user.userRoles.map((ur) => ur.roles.name);

    // Generate tokens
    const accessToken = generateAccessToken({
      sub: user.id,
      email: user.email,
      roles,
      jti: uuidv4(),
    });

    const { token: refreshToken, jti: refreshJti } = generateRefreshToken(user.id);

    // Store refresh token in Redis
    await redisClient.set(
      `refresh:${user.id}:${refreshJti}`,
      user.id,
      'EX',
      Math.floor(COOKIE_SETTINGS.refreshToken.maxAge / 1000)
    );

    // Store refresh token in database for persistence
    await prisma.refresh_tokens.create({
      data: {
        id: refreshJti,
        userId: user.id,
        tokenHash: refreshToken,
        expiresAt: new Date(Date.now() + COOKIE_SETTINGS.refreshToken.maxAge),
      },
    });

    // Set cookies
    res.cookie('accessToken', accessToken, COOKIE_SETTINGS.accessToken);
    res.cookie('refreshToken', refreshToken, COOKIE_SETTINGS.refreshToken);

    logger.info({
      message: 'User logged in',
      userId: user.id,
      email: user.email,
    });

    // Return user info
    res.json({
      success: true,
      data: {
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
emailVerified: user.emailVerified,
          roles,
        },
      },
      meta: {
        requestId: uuidv4(),
        timestamp: new Date().toISOString(),
      },
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/auth/logout
 * Blacklist tokens and clear cookies
 */
router.post('/logout', async (req: AuthRequest, res, next) => {
  try {
    // Get token from cookies or Authorization header
    let token: string | undefined;
    if (req.cookies?.accessToken) {
      token = req.cookies.accessToken;
    } else if (req.headers.authorization?.startsWith('Bearer ')) {
      token = req.headers.authorization.substring(7);
    }

    if (token) {
      try {
        // Decode token to get jti and exp
        const decoded = JSON.parse(Buffer.from(token.split('.')[1], 'base64').toString()) as {
          jti: string;
          exp: number;
        };

        // Calculate remaining TTL
        const now = Math.floor(Date.now() / 1000);
        const ttl = Math.max(decoded.exp - now, 1);

        // Add to blacklist with TTL
        await redisClient.setex(`blacklist:${decoded.jti}`, ttl, 'revoked');
      } catch {
        // Ignore decode errors on logout
      }
    }

    // Delete refresh token from Redis and database
    const refreshToken = req.cookies?.refreshToken;
    if (refreshToken) {
      try {
        const { jti, sub: userId } = verifyRefreshToken(refreshToken);
        await redisClient.del(`refresh:${userId}:${jti}`);
        await prisma.refresh_tokens.deleteMany({
          where: { tokenHash: refreshToken },
        });
      } catch {
        // Ignore verify errors on logout
      }
    }

    // Clear cookies
    res.clearCookie('accessToken', { path: COOKIE_SETTINGS.accessToken.path });
    res.clearCookie('refreshToken', { path: COOKIE_SETTINGS.refreshToken.path });

    logger.info({
      message: 'User logged out',
      userId: req.user?.sub,
    });

    res.json({
      success: true,
      data: { message: 'Logged out successfully' },
      meta: {
        requestId: uuidv4(),
        timestamp: new Date().toISOString(),
      },
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/auth/refresh
 * Refresh access token using refresh token
 */
router.post('/refresh', async (req, res, next) => {
  try {
    // Get refresh token from cookie
    const refreshToken = req.cookies?.refreshToken;

    if (!refreshToken) {
      res.status(401).json({
        success: false,
        error: {
          type: ErrorTypes.UNAUTHORIZED,
          title: 'Unauthorized',
          status: 401,
          detail: 'Refresh token required',
          instance: '/api/auth/refresh',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    // Verify refresh token
    let payload;
    try {
      payload = verifyRefreshToken(refreshToken);
    } catch {
      res.status(401).json({
        success: false,
        error: {
          type: ErrorTypes.UNAUTHORIZED,
          title: 'Unauthorized',
          status: 401,
          detail: 'Invalid refresh token',
          instance: '/api/auth/refresh',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    // Check if token exists in Redis
    const exists = await redisClient.exists(`refresh:${payload.sub}:${payload.jti}`);
    if (!exists) {
      res.status(401).json({
        success: false,
        error: {
          type: ErrorTypes.UNAUTHORIZED,
          title: 'Unauthorized',
          status: 401,
          detail: 'Refresh token revoked or expired',
          instance: '/api/auth/refresh',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    // Get user with roles
    const user = await prisma.users.findUnique({
      where: { id: payload.sub },
      include: {
        userRoles: {
          include: {
            roles: true,
          },
        },
      },
    });

    if (!user) {
      res.status(401).json({
        success: false,
        error: {
          type: ErrorTypes.UNAUTHORIZED,
          title: 'Unauthorized',
          status: 401,
          detail: 'User not found',
          instance: '/api/auth/refresh',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    const roles = user.userRoles.map((ur) => ur.roles.name);

    // Generate new access token
    const newAccessToken = generateAccessToken({
      sub: user.id,
      email: user.email,
      roles,
      jti: uuidv4(),
    });

    // Rotate refresh token
    const { token: newRefreshToken, jti: newJti } = generateRefreshToken(user.id);

    // Delete old refresh token from Redis
    await redisClient.del(`refresh:${payload.sub}:${payload.jti}`);

    // Store new refresh token in Redis
    await redisClient.set(
      `refresh:${user.id}:${newJti}`,
      user.id,
      'EX',
      Math.floor(COOKIE_SETTINGS.refreshToken.maxAge / 1000)
    );

    // Update refresh token in database
    await prisma.refresh_tokens.deleteMany({
      where: { tokenHash: refreshToken },
    });
    await prisma.refresh_tokens.create({
      data: {
        id: uuidv4(),
        tokenHash: newRefreshToken,
        userId: user.id,
        expiresAt: new Date(Date.now() + COOKIE_SETTINGS.refreshToken.maxAge),
      },
    });

    // Set new cookies
    res.cookie('accessToken', newAccessToken, COOKIE_SETTINGS.accessToken);
    res.cookie('refreshToken', newRefreshToken, COOKIE_SETTINGS.refreshToken);

    logger.info({
      message: 'Token refreshed',
      userId: user.id,
    });

    res.json({
      success: true,
      data: { message: 'Token refreshed successfully' },
      meta: {
        requestId: uuidv4(),
        timestamp: new Date().toISOString(),
      },
    });
  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/auth/me
 * Get current user info
 */
router.get('/me', authenticate, async (req: AuthRequest, res, next) => {
  try {
    if (!req.user) {
      res.status(401).json({
        success: false,
        error: {
          type: ErrorTypes.UNAUTHORIZED,
          title: 'Unauthorized',
          status: 401,
          detail: 'Authentication required',
          instance: '/api/auth/me',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    // Get user from database
    const user = await prisma.users.findUnique({
      where: { id: req.user.sub },
      include: {
        userRoles: {
          include: {
            roles: true,
          },
        },
      },
    });

    if (!user) {
      res.status(404).json({
        success: false,
        error: {
          type: ErrorTypes.NOT_FOUND,
          title: 'Not Found',
          status: 404,
          detail: 'User not found',
          instance: '/api/auth/me',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    res.json({
      success: true,
      data: {
        id: user.id,
        email: user.email,
        name: user.name,
        emailVerified: user.emailVerified,
        avatar: user.avatar,
        roles: user.userRoles.map((ur) => ur.roles.name),
        createdAt: user.createdAt,
      },
      meta: {
        requestId: uuidv4(),
        timestamp: new Date().toISOString(),
      },
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/auth/forgot-password
 * Request password reset - sends reset link to email
 */
router.post('/forgot-password', async (req, res, next) => {
  try {
    const { email } = req.body;

    if (!email) {
      res.status(400).json({
        success: false,
        error: {
          type: ErrorTypes.VALIDATION_ERROR,
          title: 'Validation Error',
          status: 400,
          detail: 'Email is required',
          instance: '/api/auth/forgot-password',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    // Find user by email
    const user = await prisma.users.findUnique({
      where: { email },
    });

    // Always return success to prevent email enumeration
    if (!user) {
      res.json({
        success: true,
        message: 'If the email exists, a reset link has been sent',
      });
      return;
    }

    // Generate reset token (JWT with 1 hour expiry)
    const resetToken = generateAccessToken({
      sub: user.id,
      email: user.email,
      roles: [],
      jti: uuidv4(),
      type: 'password_reset',
    });

    // Store token in Redis with 1 hour expiry
    await redisClient.setex(
      `password_reset:${user.id}`,
      3600, // 1 hour
      resetToken
    );

    // TODO: Send email with reset link
    // For MVP, we'll just log the reset link
    logger.info(`Password reset link for ${email}: http://localhost:3000/reset-password?token=${resetToken}`);

    res.json({
      success: true,
      message: 'If the email exists, a reset link has been sent',
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/auth/reset-password
 * Reset password using token from email
 */
router.post('/reset-password', async (req, res, next) => {
  try {
    const { token, password } = req.body;

    if (!token || !password) {
      res.status(400).json({
        success: false,
        error: {
          type: ErrorTypes.VALIDATION_ERROR,
          title: 'Validation Error',
          status: 400,
          detail: 'Token and password are required',
          instance: '/api/auth/reset-password',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    // Validate password strength
    if (password.length < 8) {
      res.status(400).json({
        success: false,
        error: {
          type: ErrorTypes.VALIDATION_ERROR,
          title: 'Validation Error',
          status: 400,
          detail: 'Password must be at least 8 characters',
          instance: '/api/auth/reset-password',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    // Verify token using verifyAccessToken (since reset token is generated with generateAccessToken)
    let decoded;
    try {
      decoded = verifyAccessToken(token);
    } catch {
      res.status(401).json({
        success: false,
        error: {
          type: ErrorTypes.UNAUTHORIZED,
          title: 'Unauthorized',
          status: 401,
          detail: 'Invalid or expired reset token',
          instance: '/api/auth/reset-password',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    // Check if token exists in Redis
    const storedToken = await redisClient.get(`password_reset:${decoded.sub}`);
    if (!storedToken || storedToken !== token) {
      res.status(401).json({
        success: false,
        error: {
          type: ErrorTypes.UNAUTHORIZED,
          title: 'Unauthorized',
          status: 401,
          detail: 'Invalid or expired reset token',
          instance: '/api/auth/reset-password',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    // Hash new password
    const passwordHash = await hashPassword(password);

    // Update user password
    await prisma.users.update({
      where: { id: decoded.sub },
      data: { passwordHash: passwordHash },
    });

    // Delete reset token from Redis
    await redisClient.del(`password_reset:${decoded.sub}`);

    logger.info(`Password reset successful for user ${decoded.sub}`);

    res.json({
      success: true,
      message: 'Password reset successful',
    });
  } catch (error) {
    next(error);
  }
});

export { router as authRouter };
