import { Router } from 'express';

const router = Router();

// GET /api/health - 健康检查
router.get('/', (_req, res) => {
  res.json({
    success: true,
    data: {
      status: 'healthy',
      service: 'scholarai-api',
      timestamp: new Date().toISOString()
    }
  });
});

// GET /api/health/ai - AI服务健康检查
router.get('/ai', async (_req, res) => {
  try {
    const aiServiceUrl = process.env.AI_SERVICE_URL || 'http://localhost:8000';
    const response = await fetch(`${aiServiceUrl}/health`);
    const aiHealth = await response.json() as { status?: string };

    res.json({
      success: true,
      data: {
        api: 'healthy',
        ai: aiHealth.status === 'ok' ? 'healthy' : 'unhealthy',
        timestamp: new Date().toISOString()
      }
    });
  } catch (error) {
    res.json({
      success: true,
      data: {
        api: 'healthy',
        ai: 'unreachable',
        timestamp: new Date().toISOString()
      }
    });
  }
});

export { router as healthRouter };
