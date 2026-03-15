import request from 'supertest';
import app from '../../src/index';
import { generateTestUserData, cleanupTestData } from '../helpers/db';

describe('RBAC E2E Tests', () => {
  afterAll(async () => {
    await cleanupTestData();
  });

  describe('Protected Routes - Authentication Required', () => {
    it('should return 401 for GET /api/papers without auth', async () => {
      const response = await request(app)
        .get('/api/papers')
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.status).toBe(401);
      expect(response.body.error.type).toBe('/errors/unauthorized');
    });

    it('should return 401 for GET /api/users/me without auth', async () => {
      const response = await request(app)
        .get('/api/users/me')
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.status).toBe(401);
    });

    it('should return 401 for GET /api/queries without auth', async () => {
      const response = await request(app)
        .get('/api/queries')
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.status).toBe(401);
    });
  });

  describe('Protected Routes - With Valid Auth', () => {
    it('should access GET /api/papers with valid token', async () => {
      const testData = generateTestUserData();
      const agent = request.agent(app);

      // Register and login
      await agent
        .post('/api/auth/register')
        .send(testData)
        .expect(201);

      await agent
        .post('/api/auth/login')
        .send({
          email: testData.email,
          password: testData.password,
        })
        .expect(200);

      // Access protected route
      const response = await agent
        .get('/api/papers')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toBeDefined();
    });

    it('should access GET /api/users/me with valid token', async () => {
      const testData = generateTestUserData();
      const agent = request.agent(app);

      // Register and login
      await agent
        .post('/api/auth/register')
        .send(testData)
        .expect(201);

      await agent
        .post('/api/auth/login')
        .send({
          email: testData.email,
          password: testData.password,
        })
        .expect(200);

      // Access protected route
      const response = await agent
        .get('/api/users/me')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.email).toBe(testData.email);
    });
  });

  describe('Token Blacklist', () => {
    it('should reject requests after logout', async () => {
      const testData = generateTestUserData();
      const agent = request.agent(app);

      // Register and login
      await agent
        .post('/api/auth/register')
        .send(testData)
        .expect(201);

      await agent
        .post('/api/auth/login')
        .send({
          email: testData.email,
          password: testData.password,
        })
        .expect(200);

      // Verify we can access protected route
      await agent
        .get('/api/papers')
        .expect(200);

      // Logout
      await agent
        .post('/api/auth/logout')
        .expect(200);

      // Try to access protected route again - should fail
      const response = await agent
        .get('/api/papers')
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/unauthorized');
    });
  });

  describe('Permission-based Access Control', () => {
    it('should check papers:read permission for GET /api/papers', async () => {
      const testData = generateTestUserData();
      const agent = request.agent(app);

      // Register and login (default 'user' role has papers:read permission)
      await agent
        .post('/api/auth/register')
        .send(testData)
        .expect(201);

      await agent
        .post('/api/auth/login')
        .send({
          email: testData.email,
          password: testData.password,
        })
        .expect(200);

      // Should be able to read papers
      const response = await agent
        .get('/api/papers')
        .expect(200);

      expect(response.body.success).toBe(true);
    });

    it('should check papers:create permission for POST /api/papers', async () => {
      const testData = generateTestUserData();
      const agent = request.agent(app);

      // Register and login (default 'user' role has papers:create permission)
      await agent
        .post('/api/auth/register')
        .send(testData)
        .expect(201);

      await agent
        .post('/api/auth/login')
        .send({
          email: testData.email,
          password: testData.password,
        })
        .expect(200);

      // Should be able to access POST /api/papers endpoint
      // (Note: This will fail with 400 because no file is uploaded, not 403)
      const response = await agent
        .post('/api/papers')
        .expect(400);

      // Should not be 403 (forbidden) - we have the permission
      expect(response.body.error?.status).not.toBe(403);
    });

    it('should check papers:delete permission for DELETE /api/papers/:id', async () => {
      const testData = generateTestUserData();
      const agent = request.agent(app);

      // Register and login
      await agent
        .post('/api/auth/register')
        .send(testData)
        .expect(201);

      await agent
        .post('/api/auth/login')
        .send({
          email: testData.email,
          password: testData.password,
        })
        .expect(200);

      // Should be able to access DELETE endpoint (user role has papers:delete)
      const response = await agent
        .delete('/api/papers/test-paper-id')
        .expect(200);

      expect(response.body.success).toBe(true);
    });
  });
});
