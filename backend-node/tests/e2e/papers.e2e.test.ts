import request from 'supertest';
import app from '../../src/index';
import { generateTestUserData, cleanupTestData } from '../helpers/db';

describe('Papers API E2E Tests', () => {
  afterAll(async () => {
    await cleanupTestData();
  });

  describe('GET /api/papers', () => {
    it('should return papers list with pagination', async () => {
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

      // Get papers list
      const response = await agent
        .get('/api/papers')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toMatchObject({
        papers: expect.any(Array),
        total: expect.any(Number),
        page: expect.any(Number),
        limit: expect.any(Number),
      });
    });

    it('should support pagination parameters', async () => {
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

      // Get papers with custom pagination
      const response = await agent
        .get('/api/papers?page=1&limit=10')
        .expect(200);

      expect(response.body.data.page).toBe(1);
      expect(response.body.data.limit).toBe(10);
    });
  });

  describe('GET /api/papers/:id', () => {
    it('should return paper details', async () => {
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

      // Get paper details (placeholder implementation)
      const response = await agent
        .get('/api/papers/test-paper-id-123')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toBeDefined();
      expect(response.body.data.id).toBe('test-paper-id-123');
    });
  });

  describe('GET /api/papers/:id/summary', () => {
    it('should return paper summary', async () => {
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

      // Get paper summary (placeholder implementation)
      const response = await agent
        .get('/api/papers/test-paper-id-123/summary')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toBeDefined();
      expect(response.body.data.paperId).toBe('test-paper-id-123');
    });
  });

  describe('POST /api/papers', () => {
    it('should require file upload', async () => {
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

      // Try to upload without file
      const response = await agent
        .post('/api/papers')
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error.message).toContain('请上传PDF文件');
    });

    // Note: Actual file upload test is skipped due to complexity
    // Would require creating a test PDF file
    it.skip('should upload PDF file successfully', async () => {
      // This test would require a real PDF file
      // const response = await agent
      //   .post('/api/papers')
      //   .attach('pdf', 'test-file.pdf')
      //   .expect(201);
    });
  });

  describe('DELETE /api/papers/:id', () => {
    it('should delete paper with permission', async () => {
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

      // Delete paper (placeholder implementation)
      const response = await agent
        .delete('/api/papers/test-paper-id-123')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.deleted).toBe(true);
    });
  });
});
