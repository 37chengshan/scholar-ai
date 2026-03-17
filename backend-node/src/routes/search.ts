import { Router } from 'express';
import { authenticate } from '../middleware/auth';
import { requirePermission } from '../middleware/rbac';
import { AuthRequest } from '../types/auth';
import { v4 as uuidv4 } from 'uuid';
import { prisma } from '../config/database';
import { logger } from '../utils/logger';
import { generateInternalToken } from '../utils/jwt';

const router = Router();

// Apply authentication to all search routes
router.use(authenticate);

// GET /api/search - 搜索论文（多源聚合）
router.get('/', async (req: AuthRequest, res, next) => {
  try {
    const { q, source = 'arxiv' } = req.query;

    if (!q) {
      return res.status(400).json({
        success: false,
        error: {
          type: '/errors/validation-error',
          title: 'Validation Error',
          status: 400,
          detail: 'Search query is required',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        }
      });
    }

    // Call Python AI service for search
    const aiServiceUrl = process.env.AI_SERVICE_URL || 'http://localhost:8000';
    const response = await fetch(
      `${aiServiceUrl}/search/${source}?query=${encodeURIComponent(q as string)}&limit=10`
    );

    if (!response.ok) {
      throw new Error(`AI service returned ${response.status}`);
    }

    const data = await response.json() as { results?: any[] };

    res.json({
      success: true,
      data: {
        query: q,
        source,
        results: data.results || [],
        total: data.results?.length || 0
      }
    });
  } catch (error) {
    logger.error('Search failed:', error);
    next(error);
  }
});

// GET /api/search/arxiv - Search arXiv specifically
router.get('/arxiv', authenticate, async (req: AuthRequest, res, next) => {
  try {
    const { query, limit = 10 } = req.query;

    if (!query) {
      return res.status(400).json({
        success: false,
        error: {
          type: '/errors/validation-error',
          title: 'Validation Error',
          status: 400,
          detail: 'Query parameter is required',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        }
      });
    }

    // Call Python AI service for arXiv search
    const aiServiceUrl = process.env.AI_SERVICE_URL || 'http://localhost:8000';
    const response = await fetch(
      `${aiServiceUrl}/search/arxiv?query=${encodeURIComponent(query as string)}&limit=${limit}`
    );

    if (!response.ok) {
      throw new Error(`AI service returned ${response.status}`);
    }

    const data = await response.json();

    res.json({
      success: true,
      data
    });
  } catch (error) {
    logger.error('arXiv search failed:', error);
    next(error);
  }
});

// GET /api/search/semantic-scholar - Search Semantic Scholar specifically
router.get('/semantic-scholar', authenticate, async (req: AuthRequest, res, next) => {
  try {
    const { query, limit = 10 } = req.query;

    if (!query) {
      return res.status(400).json({
        success: false,
        error: {
          type: '/errors/validation-error',
          title: 'Validation Error',
          status: 400,
          detail: 'Query parameter is required',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        }
      });
    }

    // Call Python AI service for Semantic Scholar search
    const aiServiceUrl = process.env.AI_SERVICE_URL || 'http://localhost:8000';
    const response = await fetch(
      `${aiServiceUrl}/search/semantic-scholar?query=${encodeURIComponent(query as string)}&limit=${limit}`
    );

    if (!response.ok) {
      throw new Error(`AI service returned ${response.status}`);
    }

    const data = await response.json();

    res.json({
      success: true,
      data
    });
  } catch (error) {
    logger.error('Semantic Scholar search failed:', error);
    next(error);
  }
});

// GET /api/search/unified - Unified search (arXiv + Semantic Scholar)
router.get('/unified', authenticate, async (req: AuthRequest, res, next) => {
  try {
    const { query, limit = 10, year_from, year_to } = req.query;

    if (!query) {
      return res.status(400).json({
        success: false,
        error: {
          type: '/errors/validation-error',
          title: 'Validation Error',
          status: 400,
          detail: 'Query parameter is required',
          requestId: uuidv4(),
          timestamp: new Date().toISOString(),
        }
      });
    }

    // Build query parameters for Python service
    const params = new URLSearchParams();
    params.append('query', query as string);
    params.append('limit', (limit as string) || '10');
    if (year_from) params.append('year_from', year_from as string);
    if (year_to) params.append('year_to', year_to as string);

    // Call Python AI service for unified search
    const aiServiceUrl = process.env.AI_SERVICE_URL || 'http://localhost:8000';
    const response = await fetch(
      `${aiServiceUrl}/search/unified?${params.toString()}`
    );

    if (!response.ok) {
      throw new Error(`AI service returned ${response.status}`);
    }

    const data = await response.json() as { results?: any[] };

    res.json({
      success: true,
      data: {
        query: query,
        results: data.results || [],
        total: data.results?.length || 0,
        filters: {
          year_from: year_from || null,
          year_to: year_to || null,
        }
      }
    });
  } catch (error) {
    logger.error('Unified search failed:', error);
    next(error);
  }
});

// GET /api/search/suggest - 搜索建议
router.get('/suggest', async (req: AuthRequest, res, next) => {
  try {
    const { q } = req.query;

    // TODO: 实现搜索建议
    res.json({
      success: true,
      data: {
        query: q,
        suggestions: []
      }
    });
  } catch (error) {
    next(error);
  }
});

// POST /api/papers/external - Add external paper to library
router.post(
  '/external',
  authenticate,
  requirePermission('papers', 'create'),
  async (req: AuthRequest, res, next) => {
    try {
      const { source, externalId, title, authors, year, abstract, pdfUrl } = req.body;
      const userId = req.user?.sub;

      if (!userId) {
        return res.status(401).json({
          success: false,
          error: {
            type: '/errors/unauthorized',
            title: 'Unauthorized',
            status: 401,
            detail: 'User not authenticated',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Validate required fields
      if (!title || !source || !externalId) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'title, source, and externalId are required',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Check for duplicate by arXiv ID (if source is arxiv)
      if (source === 'arxiv' && externalId) {
        const existingPaper = await prisma.paper.findFirst({
          where: {
            arxivId: externalId,
            userId: userId,
          },
        });

        if (existingPaper) {
          return res.status(409).json({
            success: false,
            error: {
              type: '/errors/duplicate-paper',
              title: 'Duplicate Paper',
              status: 409,
              detail: `Paper with arXiv ID ${externalId} already exists in your library`,
              requestId: uuidv4(),
              timestamp: new Date().toISOString(),
              existingPaperId: existingPaper.id,
            },
          });
        }
      }

      // Also check by title similarity (optional enhancement)
      const existingByTitle = await prisma.paper.findFirst({
        where: {
          title: {
            equals: title,
            mode: 'insensitive',
          },
          userId: userId,
        },
      });

      if (existingByTitle) {
        return res.status(409).json({
          success: false,
          error: {
            type: '/errors/duplicate-paper',
            title: 'Duplicate Paper',
            status: 409,
            detail: `Paper with title "${title}" already exists in your library`,
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
            existingPaperId: existingByTitle.id,
          },
        });
      }

      // Create paper record
      const paper = await prisma.paper.create({
        data: {
          title,
          authors: authors || [],
          year: year || null,
          abstract: abstract || null,
          pdfUrl: pdfUrl || null,
          status: 'pending',
          userId,
          // Set arxivId or other external IDs based on source
          ...(source === 'arxiv' ? { arxivId: externalId } : {}),
        }
      });

      logger.info(`Created external paper ${paper.id} from ${source}:${externalId}`);

      // Trigger processing via Python service if PDF URL available
      let downloadTriggered = false;
      if (pdfUrl) {
        try {
          const aiServiceUrl = process.env.AI_SERVICE_URL || 'http://localhost:8000';
          const { token } = generateInternalToken();
          const response = await fetch(`${aiServiceUrl}/internal/process-external`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({
              paperId: paper.id,
              pdfUrl,
              source,
              externalId,
            }),
          });

          if (response.ok) {
            downloadTriggered = true;
            logger.info(`Triggered PDF download for external paper ${paper.id}`);
          } else {
            logger.warn(`Failed to trigger processing for external paper ${paper.id}: ${response.status}`);
          }
        } catch (processError) {
          logger.warn(`Failed to trigger processing for external paper ${paper.id}:`, processError);
        }
      }

      res.status(201).json({
        success: true,
        data: {
          paperId: paper.id,
          status: paper.status,
          downloadTriggered,
          message: downloadTriggered
            ? 'Paper added to library. PDF download in progress.'
            : 'Paper added to library without PDF. You can upload PDF manually.',
        }
      });
    } catch (error) {
      logger.error('Failed to add external paper:', error);
      next(error);
    }
  }
);

export { router as searchRouter };
