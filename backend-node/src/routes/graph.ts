import { Router } from 'express';
import { authenticate } from '../middleware/auth';
import { AuthRequest } from '../types/auth';
import { logger } from '../utils/logger';

const router = Router();

// Graph API proxy to Python AI service
const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';

/**
 * GET /api/graph/nodes
 * Proxy to Python AI service for graph nodes
 * NOTE: Temporarily public for MVP testing
 */
router.get('/nodes', async (req: AuthRequest, res, next) => {
  try {
    const { limit = '20', node_type, min_pagerank, search, offset } = req.query;

    // Build query params
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit as string);
    if (node_type) params.append('node_type', node_type as string);
    if (min_pagerank) params.append('min_pagerank', min_pagerank as string);
    if (search) params.append('search', search as string);
    if (offset) params.append('offset', offset as string);

    const response = await fetch(`${AI_SERVICE_URL}/api/graph/nodes?${params.toString()}`);

    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error) {
    logger.error('Graph nodes proxy failed', { error });
    next(error);
  }
});

/**
 * GET /api/graph/neighbors/:nodeId
 * Proxy to Python AI service for node neighbors
 */
router.get('/neighbors/:nodeId', authenticate, async (req: AuthRequest, res, next) => {
  try {
    const { nodeId } = req.params;
    const { hops = '1', relationship_type } = req.query;

    const params = new URLSearchParams();
    if (hops) params.append('hops', hops as string);
    if (relationship_type) params.append('relationship_type', relationship_type as string);

    const response = await fetch(
      `${AI_SERVICE_URL}/api/graph/neighbors/${encodeURIComponent(nodeId)}?${params.toString()}`
    );

    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error) {
    logger.error('Graph neighbors proxy failed', { error });
    next(error);
  }
});

/**
 * GET /api/graph/pagerank
 * Proxy to Python AI service for PageRank
 */
router.get('/pagerank', authenticate, async (req: AuthRequest, res, next) => {
  try {
    const { limit = '10', min_year, max_year, recalculate } = req.query;

    const params = new URLSearchParams();
    if (limit) params.append('limit', limit as string);
    if (min_year) params.append('min_year', min_year as string);
    if (max_year) params.append('max_year', max_year as string);
    if (recalculate) params.append('recalculate', recalculate as string);

    const response = await fetch(`${AI_SERVICE_URL}/api/graph/pagerank?${params.toString()}`);

    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error) {
    logger.error('PageRank proxy failed', { error });
    next(error);
  }
});

/**
 * GET /api/graph/subgraph
 * Proxy to Python AI service for subgraph
 */
router.get('/subgraph', authenticate, async (req: AuthRequest, res, next) => {
  try {
    const { paper_ids, depth = '1' } = req.query;

    const params = new URLSearchParams();
    if (paper_ids) params.append('paper_ids', paper_ids as string);
    if (depth) params.append('depth', depth as string);

    const response = await fetch(`${AI_SERVICE_URL}/api/graph/subgraph?${params.toString()}`);

    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error) {
    logger.error('Subgraph proxy failed', { error });
    next(error);
  }
});

export default router;
