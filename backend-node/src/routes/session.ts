import { Router } from 'express';
import { authenticate } from '../middleware/auth';
import { requirePermission } from '../middleware/rbac';
import { Errors } from '../middleware/errorHandler';
import { AuthRequest } from '../types/auth';
import { logger } from '../utils/logger';
import fetch from 'node-fetch';

const router = Router();

// Python service URL
const PYTHON_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';

// Apply authentication to all routes
router.use(authenticate);

/**
 * GET /api/sessions - List user's sessions
 *
 * Proxies to Python /api/sessions
 */
router.get('/', requirePermission('sessions', 'read'), async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

    logger.info('List sessions request', { userId });

    // Forward query params
    const queryParams = new URLSearchParams();
    if (req.query.limit) queryParams.append('limit', req.query.limit as string);
    if (req.query.status) queryParams.append('status', req.query.status as string);

    const url = `${PYTHON_SERVICE_URL}/api/sessions?${queryParams.toString()}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'X-User-ID': userId,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      logger.error('Python service error', { status: response.status, error: errorText });
      throw Errors.badGateway('Python service error');
    }

    const data = await response.json();
    res.json(data);

  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/sessions - Create new session
 *
 * Proxies to Python /api/sessions
 */
router.post('/', requirePermission('sessions', 'create'), async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

    logger.info('Create session request', { userId });

    const response = await fetch(`${PYTHON_SERVICE_URL}/api/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId,
      },
      body: JSON.stringify(req.body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      logger.error('Python service error', { status: response.status, error: errorText });
      throw Errors.badGateway('Python service error');
    }

    const data = await response.json();
    res.status(201).json(data);

  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/sessions/:id - Get specific session
 *
 * Proxies to Python /api/sessions/:id
 */
router.get('/:id', requirePermission('sessions', 'read'), async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const sessionId = req.params.id;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

    logger.info('Get session request', { userId, sessionId });

    const response = await fetch(`${PYTHON_SERVICE_URL}/api/sessions/${sessionId}`, {
      method: 'GET',
      headers: {
        'X-User-ID': userId,
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw Errors.notFound('Session not found');
      }
      const errorText = await response.text();
      logger.error('Python service error', { status: response.status, error: errorText });
      throw Errors.badGateway('Python service error');
    }

    const data = await response.json();
    res.json(data);

  } catch (error) {
    next(error);
  }
});

/**
 * PATCH /api/sessions/:id - Update session
 *
 * Proxies to Python /api/sessions/:id
 */
router.patch('/:id', requirePermission('sessions', 'update'), async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const sessionId = req.params.id;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

    logger.info('Update session request', { userId, sessionId });

    const response = await fetch(`${PYTHON_SERVICE_URL}/api/sessions/${sessionId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId,
      },
      body: JSON.stringify(req.body),
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw Errors.notFound('Session not found');
      }
      const errorText = await response.text();
      logger.error('Python service error', { status: response.status, error: errorText });
      throw Errors.badGateway('Python service error');
    }

    const data = await response.json();
    res.json(data);

  } catch (error) {
    next(error);
  }
});

/**
 * DELETE /api/sessions/:id - Delete session
 *
 * Proxies to Python /api/sessions/:id
 */
router.delete('/:id', requirePermission('sessions', 'delete'), async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const sessionId = req.params.id;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

    logger.info('Delete session request', { userId, sessionId });

    const response = await fetch(`${PYTHON_SERVICE_URL}/api/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: {
        'X-User-ID': userId,
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw Errors.notFound('Session not found');
      }
      const errorText = await response.text();
      logger.error('Python service error', { status: response.status, error: errorText });
      throw Errors.badGateway('Python service error');
    }

    res.status(204).send();

  } catch (error) {
    next(error);
  }
});

export { router as sessionRouter };