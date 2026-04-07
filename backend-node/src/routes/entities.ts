import { Router } from 'express';
import { authenticate } from '../middleware/auth';
import { AuthRequest } from '../types/auth';
import { logger } from '../utils/logger';

const router = Router();

// Entity API proxy to Python AI service
const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';

/**
 * POST /api/entities/extract
 * Proxy to Python AI service for entity extraction
 */
router.post('/extract', authenticate, async (req: AuthRequest, res, next) => {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

    const response = await fetch(`${AI_SERVICE_URL}/entities/extract`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req.body),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error) {
    if ((error as Error).name === 'AbortError') {
      logger.error('Entity extraction proxy timeout');
      return res.status(504).json({ error: 'Gateway Timeout', message: 'Entity extraction took too long' });
    }
    logger.error('Entity extraction proxy failed', { error });
    next(error);
  }
});

/**
 * POST /api/entities/{paperId}/build
 * Proxy to Python AI service for building knowledge graph
 */
router.post('/:paperId/build', authenticate, async (req: AuthRequest, res, next) => {
  try {
    const { paperId } = req.params;
    const response = await fetch(`${AI_SERVICE_URL}/entities/${paperId}/build`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req.body),
    });

    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error) {
    logger.error('Build graph proxy failed', { error });
    next(error);
  }
});

/**
 * GET /api/entities/{paperId}/status
 * Proxy to Python AI service for entity status
 */
router.get('/:paperId/status', authenticate, async (req: AuthRequest, res, next) => {
  try {
    const { paperId } = req.params;
    const response = await fetch(`${AI_SERVICE_URL}/entities/${paperId}/status`);

    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error) {
    logger.error('Entity status proxy failed', { error });
    next(error);
  }
});

export default router;
