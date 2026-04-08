import { Response, NextFunction } from 'express';
import { AuthRequest, ErrorTypes } from '../types/auth';
import { prisma } from '../config/database';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';

/**
 * Require specific role middleware factory
 * Returns middleware that checks if user has the specified role
 */
export const requireRole = (roleName: string) => {
  return async (
    req: AuthRequest,
    res: Response,
    next: NextFunction
  ): Promise<void> => {
    const requestId = uuidv4();

    try {
      // Check if user is authenticated
      if (!req.user) {
        res.status(401).json({
          success: false,
          error: {
            type: ErrorTypes.UNAUTHORIZED,
            title: 'Unauthorized',
            status: 401,
            detail: 'Authentication required',
            instance: req.path,
            requestId,
            timestamp: new Date().toISOString(),
          },
        });
        return;
      }

      // Check if user has the required role
      const userRoles = await prisma.user_roles.findMany({
        where: { userId: req.user.sub },
        include: { roles: true },
      });

      const hasRole = userRoles.some((ur) => ur.roles.name === roleName);

      if (!hasRole) {
        logger.warn({
          message: 'Role access denied',
          userId: req.user.sub,
          requiredRole: roleName,
          path: req.path,
        });

        res.status(403).json({
          success: false,
          error: {
            type: ErrorTypes.FORBIDDEN,
            title: 'Forbidden',
            status: 403,
            detail: `Access denied. Required role: ${roleName}`,
            instance: req.path,
            requestId,
            timestamp: new Date().toISOString(),
          },
        });
        return;
      }

      next();
    } catch (error) {
      logger.error({
        message: 'Role check failed',
        error: error instanceof Error ? error.message : 'Unknown error',
        path: req.path,
        requestId,
      });

      res.status(500).json({
        success: false,
        error: {
          type: ErrorTypes.INTERNAL_ERROR,
          title: 'Internal Server Error',
          status: 500,
          detail: 'Failed to check user role',
          instance: req.path,
          requestId,
          timestamp: new Date().toISOString(),
        },
      });
    }
  };
};

/**
 * Require specific permission middleware factory
 * Returns middleware that checks if user has the specified resource:action permission
 */
export const requirePermission = (resource: string, action: string) => {
  return async (
    req: AuthRequest,
    res: Response,
    next: NextFunction
  ): Promise<void> => {
    const requestId = uuidv4();

    try {
      // Check if user is authenticated
      if (!req.user) {
        res.status(401).json({
          success: false,
          error: {
            type: ErrorTypes.UNAUTHORIZED,
            title: 'Unauthorized',
            status: 401,
            detail: 'Authentication required',
            instance: req.path,
            requestId,
            timestamp: new Date().toISOString(),
          },
        });
        return;
      }

      // Admin role bypass - admin has all permissions
      const userRoles = await prisma.user_roles.findMany({
        where: { userId: req.user.sub },
        include: { roles: true },
      });

      const isAdmin = userRoles.some((ur) => ur.roles.name === 'admin');

      if (isAdmin) {
        next();
        return;
      }

      // Check if user has the required permission
      // Query: Find any role that has this permission AND has the user assigned
      const rolesWithPermission = await prisma.roles.findMany({
        where: {
          permissions: {
            some: {
              resource,
              action,
            },
          },
          user_roles: {
            some: {
              userId: req.user.sub,
            },
          },
        },
      });

      if (rolesWithPermission.length === 0) {
        logger.warn({
          message: 'Permission denied',
          userId: req.user.sub,
          resource,
          action,
          path: req.path,
        });

        res.status(403).json({
          success: false,
          error: {
            type: ErrorTypes.FORBIDDEN,
            title: 'Forbidden',
            status: 403,
            detail: `Access denied. Required permission: ${resource}:${action}`,
            instance: req.path,
            requestId,
            timestamp: new Date().toISOString(),
          },
        });
        return;
      }

      next();
    } catch (error) {
      logger.error({
        message: 'Permission check failed',
        error: error instanceof Error ? error.message : 'Unknown error',
        path: req.path,
        requestId,
      });

      res.status(500).json({
        success: false,
        error: {
          type: ErrorTypes.INTERNAL_ERROR,
          title: 'Internal Server Error',
          status: 500,
          detail: 'Failed to check user permission',
          instance: req.path,
          requestId,
          timestamp: new Date().toISOString(),
        },
      });
    }
  };
};

/**
 * Get user permissions
 * Returns array of permission strings in format "resource:action"
 */
export const getUserPermissions = async (
  userId: string
): Promise<string[]> => {
  // Query: Find all permissions associated with roles that the user has
  const permissions = await prisma.permissions.findMany({
    where: {
      roles: {
        user_roles: {
          some: {
            userId: userId,
          },
        },
      },
    },
  });

  return permissions.map((p) => `${p.resource}:${p.action}`);
};

/**
 * Get user roles
 * Returns array of role names
 */
export const getUserRoles = async (userId: string): Promise<string[]> => {
  const userRoles = await prisma.user_roles.findMany({
    where: { userId: userId },
    include: { roles: true },
  });

  return userRoles.map((ur) => ur.roles.name);
};
