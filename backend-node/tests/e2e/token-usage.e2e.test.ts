import request from 'supertest';
import app from '../../src/index';
import { generateTestUserData, cleanupTestData } from '../helpers/db';

describe('Token Usage E2E Tests', () => {
  let accessToken: string;
  let userId: string;

  beforeAll(async () => {
    const testData = generateTestUserData();

    const response = await request(app)
      .post('/api/auth/register')
      .send(testData)
      .expect(201);

    accessToken = response.body.meta.accessToken;
    userId = response.body.data.id;
  });

  afterAll(async () => {
    await cleanupTestData();
  });

  describe('GET /api/users/me/token-usage/monthly', () => {
    it('should return 401 without authentication', async () => {
      const response = await request(app)
        .get('/api/users/me/token-usage/monthly')
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/unauthorized');
    });

    it('should return monthly token usage for authenticated user', async () => {
      const response = await request(app)
        .get('/api/users/me/token-usage/monthly')
        .set('Authorization', `Bearer ${accessToken}`)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toHaveProperty('total_tokens');
      expect(response.body.data).toHaveProperty('input_tokens');
      expect(response.body.data).toHaveProperty('output_tokens');
      expect(response.body.data).toHaveProperty('total_cost_cny');
      expect(response.body.data).toHaveProperty('request_count');
      expect(response.body.data).toHaveProperty('daily_breakdown');
      expect(Array.isArray(response.body.data.daily_breakdown)).toBe(true);
    });

    it('should accept year and month query parameters', async () => {
      const currentYear = new Date().getFullYear();
      const currentMonth = new Date().getMonth() + 1;

      const response = await request(app)
        .get(`/api/users/me/token-usage/monthly?year=${currentYear}&month=${currentMonth}`)
        .set('Authorization', `Bearer ${accessToken}`)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toBeDefined();
    });

    it('should return zero usage for new user', async () => {
      const response = await request(app)
        .get('/api/users/me/token-usage/monthly')
        .set('Authorization', `Bearer ${accessToken}`)
        .expect(200);

      expect(response.body.data.total_tokens).toBe(0);
      expect(response.body.data.total_cost_cny).toBe(0);
      expect(response.body.data.request_count).toBe(0);
      expect(response.body.data.daily_breakdown).toEqual([]);
    });
  });

  describe('Token usage persistence', () => {
    it('should persist token usage data across requests', async () => {
      const response1 = await request(app)
        .get('/api/users/me/token-usage/monthly')
        .set('Authorization', `Bearer ${accessToken}`)
        .expect(200);

      const response2 = await request(app)
        .get('/api/users/me/token-usage/monthly')
        .set('Authorization', `Bearer ${accessToken}`)
        .expect(200);

      expect(response1.body.data).toEqual(response2.body.data);
    });
  });
});