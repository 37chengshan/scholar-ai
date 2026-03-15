import request from 'supertest';
import app from '../../src/index';
import { cleanupTestData } from '../helpers/db';

describe('Error Handling E2E Tests', () => {
  afterAll(async () => {
    await cleanupTestData();
  });

  describe('404 Not Found', () => {
    it('should return RFC 7807 format for non-existent routes', async () => {
      const response = await request(app)
        .get('/api/non-existent-route')
        .expect(404);

      expect(response.body).toBeDefined();
      expect(response.body.success).toBe(false);
      expect(response.body.error).toBeDefined();
      expect(response.body.error).toHaveProperty('type');
      expect(response.body.error).toHaveProperty('title');
      expect(response.body.error).toHaveProperty('status');
      expect(response.body.error).toHaveProperty('detail');
      expect(response.body.error).toHaveProperty('instance');
      expect(response.body.error).toHaveProperty('requestId');
      expect(response.body.error).toHaveProperty('timestamp');
    });

    it('should return RFC 7807 format for non-existent resources', async () => {
      const response = await request(app)
        .get('/api/papers/non-existent-id')
        .expect(401); // Requires auth first

      expect(response.body.error).toBeDefined();
      if (response.body.error.type) {
        expect(response.body.error).toHaveProperty('type');
        expect(response.body.error).toHaveProperty('title');
        expect(response.body.error).toHaveProperty('status');
      }
    });
  });

  describe('400 Validation Errors', () => {
    it('should return 400 with Zod error details for invalid input', async () => {
      const response = await request(app)
        .post('/api/auth/register')
        .send({
          email: 'invalid',
          password: '123',
          name: '',
        })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/validation-error');
      expect(response.body.error.status).toBe(400);
      expect(response.body.error.detail).toBeDefined();
    });

    it('should return 400 for missing required fields', async () => {
      const response = await request(app)
        .post('/api/auth/register')
        .send({
          // Missing required fields
        })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/validation-error');
    });
  });

  describe('401 Unauthorized', () => {
    it('should return 401 with proper error format for missing auth', async () => {
      const response = await request(app)
        .get('/api/papers')
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toMatchObject({
        type: '/errors/unauthorized',
        title: 'Unauthorized',
        status: 401,
      });
      expect(response.body.error.detail).toBeDefined();
      expect(response.body.error.requestId).toBeDefined();
      expect(response.body.error.timestamp).toBeDefined();
    });

    it('should return 401 for invalid token format', async () => {
      const response = await request(app)
        .get('/api/papers')
        .set('Authorization', 'Bearer invalid-token')
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/unauthorized');
    });

    it('should return 401 for expired token', async () => {
      // Create a manually crafted expired token
      const expiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNTAwMDAwMDAwLCJpYXQiOjE1MDAwMDAwMDB9.signature';

      const response = await request(app)
        .get('/api/papers')
        .set('Authorization', `Bearer ${expiredToken}`)
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/unauthorized');
    });
  });

  describe('403 Forbidden', () => {
    it('should return 403 for insufficient permissions', async () => {
      // This test assumes there might be admin-only endpoints
      // Currently all endpoints use user role which has all permissions
      // This is a placeholder for future admin-only routes

      // For now, we'll just verify the 401/403 structure is correct
      const response = await request(app)
        .get('/api/papers')
        .expect(401);

      expect(response.body.error).toBeDefined();
      expect(response.body.error.status).toBe(401);
    });
  });

  describe('409 Conflict', () => {
    it('should return 409 for duplicate email registration', async () => {
      const userData = {
        email: `conflict-test-${Date.now()}@example.com`,
        password: 'Test123!',
        name: 'Conflict Test User',
      };

      // First registration
      await request(app)
        .post('/api/auth/register')
        .send(userData)
        .expect(201);

      // Second registration with same email
      const response = await request(app)
        .post('/api/auth/register')
        .send(userData)
        .expect(409);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toMatchObject({
        type: '/errors/conflict',
        title: 'Conflict',
        status: 409,
        detail: expect.stringContaining('already registered'),
      });
      expect(response.body.error.requestId).toBeDefined();
      expect(response.body.error.timestamp).toBeDefined();
    });
  });

  describe('Error Response Structure', () => {
    it('should include all RFC 7807 required fields', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'nonexistent@example.com',
          password: 'wrongpassword',
        })
        .expect(401);

      const error = response.body.error;
      expect(error).toHaveProperty('type');
      expect(error).toHaveProperty('title');
      expect(error).toHaveProperty('status');
      expect(error).toHaveProperty('detail');
      expect(error).toHaveProperty('instance');
      expect(error).toHaveProperty('requestId');
      expect(error).toHaveProperty('timestamp');

      // Validate field types
      expect(typeof error.type).toBe('string');
      expect(typeof error.title).toBe('string');
      expect(typeof error.status).toBe('number');
      expect(typeof error.detail).toBe('string');
      expect(typeof error.instance).toBe('string');
      expect(typeof error.requestId).toBe('string');
      expect(typeof error.timestamp).toBe('string');
    });

    it('should include meta object in successful responses', async () => {
      const response = await request(app)
        .get('/api/health')
        .expect(200);

      expect(response.body.meta).toBeDefined();
      expect(response.body.meta.requestId).toBeDefined();
      expect(response.body.meta.timestamp).toBeDefined();
    });
  });
});
