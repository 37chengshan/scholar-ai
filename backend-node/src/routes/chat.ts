import { Router, Request, Response } from 'express';
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
 * POST /api/chat - Proxy to Python /api/chat (blocking, non-streaming)
 *
 * Forwards chat requests to Python service and returns blocking response.
 */
router.post('/', requirePermission('chat', 'create'), async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

    logger.info('Chat request (blocking)', { userId });

    // Forward request to Python service
    const response = await fetch(`${PYTHON_SERVICE_URL}/api/chat`, {
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
    res.json(data);

  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/chat/stream - Proxy SSE stream from Python
 *
 * Pipes SSE events from Python service to client.
 * Handles connection errors and forwards all headers.
 */
router.post('/stream', requirePermission('chat', 'create'), async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

    logger.info('Chat stream request', { userId });

    // Forward request to Python service
    const response = await fetch(`${PYTHON_SERVICE_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId,
        'Authorization': req.headers.authorization || '',
      },
      body: JSON.stringify(req.body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      logger.error('Python service error', { status: response.status, error: errorText });
      throw Errors.badGateway('Python service error');
    }

    // Set SSE headers
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('X-Accel-Buffering', 'no');

    // Forward session ID header if present
    const sessionId = response.headers.get('X-Session-ID');
    if (sessionId) {
      res.setHeader('X-Session-ID', sessionId);
    }

    // Pipe SSE stream from Python to client
    response.body?.on('data', (chunk) => {
      res.write(chunk);
    });

    response.body?.on('end', () => {
      res.end();
    });

    response.body?.on('error', (error) => {
      logger.error('SSE stream error', { error: error.message });
      res.end();
    });

    // Handle client disconnect
    req.on('close', () => {
      logger.info('Client disconnected from SSE stream');
      response.body?.destroy();
    });

  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/chat/confirm - Proxy to Python /api/chat/confirm
 *
 * Forwards user confirmation for dangerous operations.
 */
router.post('/confirm', requirePermission('chat', 'create'), async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

    logger.info('Chat confirm request', { userId, confirmationId: req.body.confirmation_id });

    // Forward request to Python service
    const response = await fetch(`${PYTHON_SERVICE_URL}/api/chat/confirm`, {
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
    res.json(data);

  } catch (error) {
    next(error);
  }
});

export { router as chatRouter };