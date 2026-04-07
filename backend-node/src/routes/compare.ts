import { Router } from 'express';
import { authenticate } from '../middleware/auth';
import { requirePermission } from '../middleware/rbac';
import { AuthRequest } from '../types/auth';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';

const router = Router();

// POST /api/compare - Compare multiple papers
router.post(
  '/',
  authenticate,
  requirePermission('papers', 'read'),
  async (req: AuthRequest, res, next) => {
    try {
      const { paperIds, dimensions, include_abstract } = req.body;
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

      // Validate paperIds
      if (!Array.isArray(paperIds) || paperIds.length < 2 || paperIds.length > 10) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'paperIds must be an array with 2-10 items',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Call Python AI service for comparison
      const aiServiceUrl = process.env.AI_SERVICE_URL || 'http://localhost:8000';
      const response = await fetch(`${aiServiceUrl}/compare`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': req.headers.authorization || '',
        },
        body: JSON.stringify({
          paperIds,
          dimensions: dimensions || ['method', 'results', 'dataset', 'metrics'],
          include_abstract: include_abstract !== false,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({})) as { detail?: string };
        throw new Error(errorData.detail || `AI service returned ${response.status}`);
      }

      const data = await response.json() as {
        paperIds: string[];
        dimensions: string[];
        markdown_table: string;
        structured_data: any[];
        summary: string;
      };

      res.json({
        success: true,
        data: {
          paperIds: data.paperIds,
          dimensions: data.dimensions,
          markdown_table: data.markdown_table,
          structured_data: data.structured_data,
          summary: data.summary,
        }
      });
    } catch (error) {
      logger.error('Comparison failed:', error);
      next(error);
    }
  }
);

// POST /api/compare/evolution - Generate evolution timeline
router.post(
  '/evolution',
  authenticate,
  requirePermission('papers', 'read'),
  async (req: AuthRequest, res, next) => {
    try {
      const { paperIds, method_name } = req.body;
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

      // Validate request
      if (!Array.isArray(paperIds) || paperIds.length < 2 || paperIds.length > 20) {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'paperIds must be an array with 2-20 items',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      if (!method_name || typeof method_name !== 'string') {
        return res.status(400).json({
          success: false,
          error: {
            type: '/errors/validation-error',
            title: 'Validation Error',
            status: 400,
            detail: 'method_name is required',
            requestId: uuidv4(),
            timestamp: new Date().toISOString(),
          },
        });
      }

      // Call Python AI service
      const aiServiceUrl = process.env.AI_SERVICE_URL || 'http://localhost:8000';
      const response = await fetch(`${aiServiceUrl}/compare/evolution`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': req.headers.authorization || '',
        },
        body: JSON.stringify({
          paperIds,
          method_name,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({})) as { detail?: string };
        throw new Error(errorData.detail || `AI service returned ${response.status}`);
      }

      const data = await response.json() as {
        method: string;
        paperCount: number;
        timeline: Array<{
          year: number;
          version: string;
          paperId: string;
          paper_title: string;
          key_changes: string;
        }>;
        summary: string;
      };

      res.json({
        success: true,
        data: {
          method: data.method,
          paperCount: data.paperCount,
          timeline: data.timeline,
          summary: data.summary,
        }
      });
    } catch (error) {
      logger.error('Evolution timeline generation failed:', error);
      next(error);
    }
  }
);

export { router as compareRouter };
