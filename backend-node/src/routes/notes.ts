import { Router } from 'express';
import { authenticate } from '../middleware/auth';
import { Errors } from '../middleware/errorHandler';
import { AuthRequest } from '../types/auth';
import { logger } from '../utils/logger';
import fetch from 'node-fetch';

const router = Router();
const PYTHON_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';

router.use(authenticate);

// POST /api/notes/generate - Generate reading notes
router.post('/generate', async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { paper_id } = req.body;

    if (!paper_id) {
      throw Errors.validation('paper_id is required');
    }

    logger.info('Generate notes request', { userId, paper_id });

    const response = await fetch(`${PYTHON_SERVICE_URL}/api/notes/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId || '',
      },
      body: JSON.stringify({ paper_id }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      logger.error('Python service error', { status: response.status, error: errorText });
      throw Errors.badGateway('Python notes service error');
    }

    const data = await response.json();
    res.status(201).json(data);

  } catch (error) {
    next(error);
  }
});

// POST /api/notes/regenerate - Regenerate notes with modification request
router.post('/regenerate', async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { paper_id, modification_request } = req.body;

    if (!paper_id || !modification_request) {
      throw Errors.validation('paper_id and modification_request are required');
    }

    logger.info('Regenerate notes request', { userId, paper_id });

    const response = await fetch(`${PYTHON_SERVICE_URL}/api/notes/regenerate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId || '',
      },
      body: JSON.stringify({ paper_id, modification_request }),
    });

    if (!response.ok) {
      throw Errors.badGateway('Python notes service error');
    }

    const data = await response.json();
    res.json(data);

  } catch (error) {
    next(error);
  }
});

// GET /api/notes/:paperId - Get notes for paper
router.get('/:paperId', async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { paperId } = req.params;

    const response = await fetch(`${PYTHON_SERVICE_URL}/api/notes/${paperId}`, {
      headers: { 'X-User-ID': userId || '' },
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw Errors.notFound('Notes not found');
      }
      throw Errors.badGateway('Python notes service error');
    }

    const data = await response.json();
    res.json(data);

  } catch (error) {
    next(error);
  }
});

// GET /api/notes/:paperId/export - Export notes as Markdown
router.get('/:paperId/export', async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { paperId } = req.params;

    const response = await fetch(`${PYTHON_SERVICE_URL}/api/notes/${paperId}/export`, {
      headers: { 'X-User-ID': userId || '' },
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw Errors.notFound('Notes not found');
      }
      throw Errors.badGateway('Python notes service error');
    }

    const data = await response.json();
    res.json(data);

  } catch (error) {
    next(error);
  }
});

export { router as notesRouter };