/**
 * Semantic Scholar API routes.
 *
 * Per D-05: New routes at /api/semantic-scholar/*.
 * Per D-06: Existing /search/semantic-scholar unchanged.
 */

import { Router } from 'express';
import { z } from 'zod';
import { authenticate } from '../middleware/auth';
import { AuthRequest } from '../types/auth';
import { semanticScholarService } from '../services/semantic-scholar';
import { logger } from '../utils/logger';

const router = Router();

// All routes require authentication
router.use(authenticate);

// Validation schemas
const BatchSchema = z.object({
  ids: z.array(z.string()).min(1, 'At least 1 ID required').max(1000, 'Max 1000 IDs'),
  fields: z.string().optional()
});

/**
 * @route POST /api/semantic-scholar/batch
 * @desc Batch get papers by IDs
 * @access Private
 *
 * Per D-01: Batch up to 1000 IDs.
 */
router.post('/batch', async (req: AuthRequest, res, next) => {
  try {
    const { ids, fields } = BatchSchema.parse(req.body);

    logger.info('S2 batch request', { userId: req.user?.sub, count: ids.length });

    const papers = await semanticScholarService.batchGetPapers(ids, fields);

    res.json({
      success: true,
      data: papers,
      count: papers.length
    });
  } catch (error) {
    next(error);
  }
});

/**
 * @route GET /api/semantic-scholar/paper/:paperId
 * @desc Get paper details
 * @access Private
 */
router.get('/paper/:paperId', async (req: AuthRequest, res, next) => {
  try {
    const { paperId } = req.params;
    const { fields } = req.query;

    const paper = await semanticScholarService.getPaperDetails(
      paperId,
      fields as string | undefined
    );

    res.json({
      success: true,
      data: paper
    });
  } catch (error) {
    next(error);
  }
});

/**
 * @route GET /api/semantic-scholar/paper/:paperId/citations
 * @desc Get paper citations (who cited this paper)
 * @access Private
 *
 * Per D-02: Single depth, paginated.
 */
router.get('/paper/:paperId/citations', async (req: AuthRequest, res, next) => {
  try {
    const { paperId } = req.params;
    const { fields, limit } = req.query;

    logger.info('S2 citations request', { userId: req.user?.sub, paperId });

    const citations = await semanticScholarService.getCitations(
      paperId,
      fields as string | undefined,
      limit ? parseInt(limit as string) : undefined
    );

    res.json({
      success: true,
      data: citations,
      count: citations.length
    });
  } catch (error) {
    next(error);
  }
});

/**
 * @route GET /api/semantic-scholar/paper/:paperId/references
 * @desc Get paper references (what this paper cited)
 * @access Private
 *
 * Per D-02: Single depth, paginated.
 */
router.get('/paper/:paperId/references', async (req: AuthRequest, res, next) => {
  try {
    const { paperId } = req.params;
    const { fields, limit } = req.query;

    logger.info('S2 references request', { userId: req.user?.sub, paperId });

    const references = await semanticScholarService.getReferences(
      paperId,
      fields as string | undefined,
      limit ? parseInt(limit as string) : undefined
    );

    res.json({
      success: true,
      data: references,
      count: references.length
    });
  } catch (error) {
    next(error);
  }
});

export default router;