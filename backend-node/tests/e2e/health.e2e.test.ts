import request from 'supertest';
import app from '../../src/index';

describe('Health Check E2E Tests', () => {
  describe('GET /api/health', () => {
    it('should return 200 with status "healthy"', async () => {
      const response = await request(app)
        .get('/api/health')
        .expect(200);

      expect(response.body).toMatchObject({
        success: true,
        data: {
          status: 'healthy',
          service: 'scholarai-api',
        },
      });
      expect(response.body.data.timestamp).toBeDefined();
      expect(response.body.data.uptime).toBeGreaterThanOrEqual(0);
    });
  });

  describe('GET /api/health/ai', () => {
    it('should return AI service status', async () => {
      const response = await request(app)
        .get('/api/health/ai')
        .expect(200);

      expect(response.body).toMatchObject({
        success: true,
        data: {
          service: 'ai-service',
        },
      });
      // Status could be 'connected' or 'degraded' depending on AI service availability
      expect(['connected', 'degraded', 'error']).toContain(response.body.data.status);
    });
  });
});
