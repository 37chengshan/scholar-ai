import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import { authenticate } from '../middleware/auth';
import { requirePermission } from '../middleware/rbac';
import { aiService, RAGQueryRequest } from '../services/aiService';
import { Errors } from '../middleware/errorHandler';
import { AuthRequest } from '../types/auth';
import { logger } from '../utils/logger';

const router = Router();
const prisma = new PrismaClient();

// Apply authentication to all routes
router.use(authenticate);

/**
 * POST /api/queries - Submit RAG query
 *
 * Per D-07: Implement queries endpoint connecting Node.js → Python RAG
 *
 * Flow:
 * 1. Create Query record with status 'processing'
 * 2. Call Python RAG service (semantic cache in Plan 02)
 * 3. Update Query record with answer and sources
 * 4. Return response
 */
router.post('/', requirePermission('queries', 'create'), async (req: AuthRequest, res, next) => {
  const startTime = Date.now();

  try {
    const { question, paperIds, queryType = 'single', conversationId } = req.body;
    const userId = req.user?.sub;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

    if (!question || typeof question !== 'string') {
      throw Errors.validation('Question is required and must be a string');
    }

    if (!paperIds || !Array.isArray(paperIds) || paperIds.length === 0) {
      throw Errors.validation('paperIds must be a non-empty array');
    }

    logger.info('Creating query', { userId, question: question.substring(0, 50), paperCount: paperIds.length });

    // 1. Create Query record
    const query = await prisma.query.create({
      data: {
        question,
        queryType,
        userId,
        paperIds,
        status: 'processing',
      },
    });

    // 2. Call Python RAG service
    // Semantic cache (Plan 02) will return cached response for similar queries
    const ragRequest: RAGQueryRequest = {
      question,
      paper_ids: paperIds,
      query_type: queryType,
      conversation_id: conversationId,
    };

    const ragResponse = await aiService.ragQuery(ragRequest);

    // 3. Update Query record with response
    const durationMs = Date.now() - startTime;
    await prisma.query.update({
      where: { id: query.id },
      data: {
        answer: ragResponse.answer,
        sources: ragResponse.sources,
        status: 'completed',
        durationMs,
      },
    });

    logger.info('Query completed', {
      queryId: query.id,
      durationMs,
      cached: ragResponse.cached,
      confidence: ragResponse.confidence,
    });

    // 4. Return response
    res.json({
      success: true,
      data: {
        id: query.id,
        question,
        answer: ragResponse.answer,
        sources: ragResponse.sources,
        confidence: ragResponse.confidence,
        cached: ragResponse.cached,
        status: 'completed',
        durationMs,
        paperIds,
        createdAt: query.createdAt,
      },
    });

  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/queries - Get query history
 *
 * Returns paginated list of user's queries with optional filters.
 */
router.get('/', requirePermission('queries', 'read'), async (req: AuthRequest, res, next) => {
  try {
    const userId = req.user?.sub;
    const { page = 1, limit = 20, status, queryType } = req.query;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

    const skip = (Number(page) - 1) * Number(limit);

    // Build filter
    const where: Record<string, unknown> = { userId };
    if (status) {
      where.status = status;
    }
    if (queryType) {
      where.queryType = queryType;
    }

    // Fetch queries and total count
    const [queries, total] = await Promise.all([
      prisma.query.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip,
        take: Number(limit),
        select: {
          id: true,
          question: true,
          queryType: true,
          status: true,
          durationMs: true,
          paperIds: true,
          createdAt: true,
          // Don't include full answer/sources in list
        },
      }),
      prisma.query.count({ where }),
    ]);

    res.json({
      success: true,
      data: {
        queries,
        pagination: {
          page: Number(page),
          limit: Number(limit),
          total,
          totalPages: Math.ceil(total / Number(limit)),
        },
      },
    });

  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/queries/:id - Get query details
 *
 * Returns full query details including answer and sources.
 */
router.get('/:id', requirePermission('queries', 'read'), async (req: AuthRequest, res, next) => {
  try {
    const { id } = req.params;
    const userId = req.user?.sub;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

    const query = await prisma.query.findFirst({
      where: { id, userId },
    });

    if (!query) {
      throw Errors.notFound('Query not found');
    }

    res.json({
      success: true,
      data: query,
    });

  } catch (error) {
    next(error);
  }
});

/**
 * DELETE /api/queries/:id - Delete query
 */
router.delete('/:id', requirePermission('queries', 'delete'), async (req: AuthRequest, res, next) => {
  try {
    const { id } = req.params;
    const userId = req.user?.sub;

    if (!userId) {
      throw Errors.unauthorized('User not authenticated');
    }

    const query = await prisma.query.findFirst({
      where: { id, userId },
    });

    if (!query) {
      throw Errors.notFound('Query not found');
    }

    await prisma.query.delete({
      where: { id },
    });

    res.json({
      success: true,
      data: { message: 'Query deleted' },
    });

  } catch (error) {
    next(error);
  }
});

export { router as queriesRouter };