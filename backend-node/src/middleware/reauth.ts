import { Request, Response, NextFunction } from 'express';
import { prisma } from '../config/database';
import { verifyPassword } from '../utils/crypto';
import { Errors } from './errorHandler';
import { logger } from '../utils/logger';

export interface ReauthRequest extends Request {
  user?: { sub: string; email: string; roles: string[]; jti: string };
  reauthVerified?: boolean;
}

/**
 * Middleware: Require password re-authentication for sensitive operations
 *
 * Used for:
 * - DELETE /api/papers/:id (delete paper)
 * - PATCH /api/users/me/password (change password)
 * - DELETE /api/users/me/api-keys/:keyId (delete API key)
 * - DELETE /api/users/me (delete account)
 *
 * Request body must include: { currentPassword: string }
 */
export const requireReauth = async (
  req: ReauthRequest,
  res: Response,
  next: NextFunction
): Promise<void> => {
  try {
    const userId = req.user?.sub;
    const { currentPassword } = req.body;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

    if (!currentPassword) {
      throw Errors.validation('Current password required for this operation');
    }

    // Fetch user's password hash
    const user = await prisma.users.findUnique({
      where: { id: userId },
      select: { passwordHash: true },
    });

    if (!user) {
      throw Errors.notFound('User not found');
    }

    const isValid = await verifyPassword(user.passwordHash, currentPassword);

    if (!isValid) {
      throw Errors.invalidCredentials('Invalid password');
    }

    // Mark request as re-auth verified
    req.reauthVerified = true;
    logger.info('Re-auth successful', {
      userId,
      operation: req.method + ' ' + req.path,
    });

    next();
  } catch (error) {
    next(error);
  }
};