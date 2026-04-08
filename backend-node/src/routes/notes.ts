import { Router, Request, Response } from 'express';
import { authenticate } from '../middleware/auth';
import { Errors } from '../middleware/errorHandler';
import { AuthRequest } from '../types/auth';
import { logger } from '../utils/logger';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();
const PYTHON_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';

router.use(authenticate);

// POST /api/notes - Create a new note (supports cross-paper association)
router.post('/', async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { title, content, tags, paperIds } = req.body;

    // Validation
    if (!title || !content) {
      throw Errors.validation('title and content are required');
    }

    logger.info('Create note request', { userId, title, paperCount: paperIds?.length || 0 });

    const note = await prisma.notes.create({
      data: {
        userId,
        title,
        content,
        tags: tags || [],
        paperIds: paperIds || [],
      },
    });

    res.status(201).json(note);

  } catch (error) {
    next(error);
  }
});

// GET /api/notes - Get all notes for user with optional filtering
router.get('/', async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { paperId, tag, sortBy = 'createdAt', order = 'desc', limit, offset } = req.query;

    // Build where clause
    const where: any = { userId };

    // Filter by paperId (notes associated with specific paper)
    if (paperId) {
      where.paperIds = { has: paperId };
    }

    // Filter by tag
    if (tag) {
      where.tags = { has: tag };
    }

    // Build orderBy
    const orderBy: any = {};
    orderBy[sortBy as string] = order;

    // Execute query
    const notes = await prisma.notes.findMany({
      where,
      orderBy,
      take: limit ? parseInt(limit as string) : undefined,
      skip: offset ? parseInt(offset as string) : undefined,
    });

    logger.info('Get notes request', { userId, count: notes.length, filters: { paperId, tag } });
    res.json(notes);

  } catch (error) {
    next(error);
  }
});

// GET /api/notes/:id - Get a specific note
router.get('/:id', async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { id } = req.params;

    const note = await prisma.notes.findFirst({
      where: {
        id,
        userId,
      },
    });

    if (!note) {
      throw Errors.notFound('Note not found');
    }

    logger.info('Get note request', { userId, noteId: id });
    res.json(note);

  } catch (error) {
    next(error);
  }
});

// PUT /api/notes/:id - Update a note
router.put('/:id', async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { id } = req.params;
    const { title, content, tags, paperIds } = req.body;

    // Check if note exists and belongs to user
    const existingNote = await prisma.notes.findFirst({
      where: {
        id,
        userId,
      },
    });

    if (!existingNote) {
      throw Errors.notFound('Note not found');
    }

    // Update note
    const note = await prisma.notes.update({
      where: { id },
      data: {
        title: title ?? existingNote.title,
        content: content ?? existingNote.content,
        tags: tags ?? existingNote.tags,
        paperIds: paperIds ?? existingNote.paperIds,
      },
    });

    logger.info('Update note request', { userId, noteId: id });
    res.json(note);

  } catch (error) {
    next(error);
  }
});

// DELETE /api/notes/:id - Delete a note
router.delete('/:id', async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { id } = req.params;

    // Check if note exists and belongs to user
    const existingNote = await prisma.notes.findFirst({
      where: {
        id,
        userId,
      },
    });

    if (!existingNote) {
      throw Errors.notFound('Note not found');
    }

    // Delete note
    await prisma.notes.delete({
      where: { id },
    });

    logger.info('Delete note request', { userId, noteId: id });
    res.status(204).send();

  } catch (error) {
    next(error);
  }
});

// POST /api/notes/generate - Generate reading notes (proxy to Python service)
router.post('/generate', async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { paperId } = req.body;

    if (!paperId) {
      throw Errors.validation('paperId is required');
    }

    logger.info('Generate notes request', { userId, paperId });

    const response = await fetch(`${PYTHON_SERVICE_URL}/api/notes/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId || '',
      },
      body: JSON.stringify({ paperId }),
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

// POST /api/notes/regenerate - Regenerate notes with modification request (proxy)
router.post('/regenerate', async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { paperId, modification_request } = req.body;

    if (!paperId || !modification_request) {
      throw Errors.validation('paperId and modification_request are required');
    }

    logger.info('Regenerate notes request', { userId, paperId });

    const response = await fetch(`${PYTHON_SERVICE_URL}/api/notes/regenerate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId || '',
      },
      body: JSON.stringify({ paperId, modification_request }),
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

// GET /api/notes/paper/:paperId - Get notes for a specific paper (legacy endpoint)
router.get('/paper/:paperId', async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { paperId } = req.params;

    const notes = await prisma.notes.findMany({
      where: {
        userId,
        paperIds: {
          has: paperId,
        },
      },
      orderBy: { createdAt: 'desc' },
    });

    logger.info('Get notes by paper request', { userId, paperId, count: notes.length });
    res.json(notes);

  } catch (error) {
    next(error);
  }
});

export { router as notesRouter };
