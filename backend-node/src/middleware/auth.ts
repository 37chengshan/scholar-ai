import { Response, NextFunction } from 'express';
import { AuthRequest, ErrorTypes } from '../types/auth';
import { verifyAccessToken } from '../utils/jwt';
import { redisClient } from '../config/redis';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';

/**
 * Authentication middleware
 * Validates JWT access token from cookies or Authorization header
 * Checks Redis blacklist for revoked tokens
 */
export const authenticate = async (
  req: AuthRequest,
  res: Response,
  next: NextFunction
): Promise<void> => {
  const requestId = uuidv4();

  try {
    // Extract token from cookies or Authorization header
    let token: string | undefined;

    // Check cookies first (preferred method)
    if (req.cookies?.accessToken) {
      token = req.cookies.accessToken;
    }
    // Fallback to Authorization header
    else if (req.headers.authorization?.startsWith('Bearer ')) {
      token = req.headers.authorization.substring(7);
    }

    // No token found
    if (!token) {
      res.status(401).json({
        success: false,
        error: {
          type: ErrorTypes.UNAUTHORIZED,
          title: 'Unauthorized',
          status: 401,
          detail: 'Authentication required. Please log in.',
          instance: req.path,
          requestId,
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    // Verify token with explicit algorithm whitelist
    const payload = verifyAccessToken(token);

    // Check if token is blacklisted in Redis
    const isBlacklisted = await redisClient.exists(`blacklist:${payload.jti}`);
    if (isBlacklisted) {
      logger.warn({
        message: 'Blacklisted token used',
        jti: payload.jti,
        userId: payload.sub,
        path: req.path,
      });

      res.status(401).json({
        success: false,
        error: {
          type: ErrorTypes.UNAUTHORIZED,
          title: 'Unauthorized',
          status: 401,
          detail: 'Token has been revoked. Please log in again.',
          instance: req.path,
          requestId,
          timestamp: new Date().toISOString(),
        },
      });
      return;
    }

    // Attach user to request
    req.user = {
      sub: payload.sub,
      email: payload.email,
      roles: payload.roles,
      jti: payload.jti,
    };

    next();
  } catch (error) {
    logger.error({
      message: 'Authentication failed',
      error: error instanceof Error ? error.message : 'Unknown error',
      path: req.path,
      requestId,
    });

    // Handle JWT-specific errors
    let errorDetail = 'Invalid token. Please log in again.';
    if (error instanceof Error) {
      if (error.name === 'TokenExpiredError') {
        errorDetail = 'Token has expired. Please log in again.';
      } else if (error.name === 'JsonWebTokenError') {
        errorDetail = 'Invalid token format. Please log in again.';
      }
    }

    res.status(401).json({
      success: false,
      error: {
        type: ErrorTypes.UNAUTHORIZED,
        title: 'Unauthorized',
        status: 401,
        detail: errorDetail,
        instance: req.path,
        requestId,
        timestamp: new Date().toISOString(),
      },
    });
  }
};

/**
 * Optional authentication middleware
 * Attaches user if token is present and valid, but doesn't require it
 */
export const optionalAuth = async (
  req: AuthRequest,
  res: Response,
  next: NextFunction
): Promise<void> => {
  try {
    let token: string | undefined;

    if (req.cookies?.accessToken) {
      token = req.cookies.accessToken;
    } else if (req.headers.authorization?.startsWith('Bearer ')) {
      token = req.headers.authorization.substring(7);
    }

    if (token) {
      const payload = verifyAccessToken(token);
      const isBlacklisted = await redisClient.exists(`blacklist:${payload.jti}`);

      if (!isBlacklisted) {
        req.user = {
          sub: payload.sub,
          email: payload.email,
          roles: payload.roles,
          jti: payload.jti,
        };
      }
    }
  } catch {
    // Ignore errors in optional auth - user just won't be attached
  }

  next();
};
