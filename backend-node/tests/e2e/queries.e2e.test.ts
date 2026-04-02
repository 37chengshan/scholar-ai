import request from 'supertest';
import app from '../../src/index';
import { generateTestUserData, cleanupTestData } from '../helpers/db';
import { generateTestAccessToken } from '../helpers/auth';

describe('Queries API E2E Tests', () => {
  let accessToken: string;
  let testUserId: string;
  let testPaperId: string;

  beforeAll(async () => {
    // Create test user
    const userData = generateTestUserData();

    const registerResponse = await request(app)
      .post('/api/auth/register')
      .send(userData)
      .expect(201);

    testUserId = registerResponse.body.data.id;

    // Login to get access token
    const loginResponse = await request(app)
      .post('/api/auth/login')
      .send({
        email: userData.email,
        password: userData.password,
      })
      .expect(200);

    accessToken = loginResponse.body.meta.accessToken;

    // Create test paper
    const paperResponse = await request(app)
      .post('/api/papers')
      .set('Authorization', `Bearer ${accessToken}`)
      .send({
        title: 'Test Paper for Queries',
        authors: ['Test Author'],
        sourceUrl: 'https://example.com/test.pdf',
      })
      .expect(201);

    testPaperId = paperResponse.body.data.id;
  });

  afterAll(async () => {
    await cleanupTestData();
  });

  describe('POST /api/queries', () => {
    it('should create query and return RAG response', async () => {
      const response = await request(app)
        .post('/api/queries')
        .set('Authorization', `Bearer ${accessToken}`)
        .send({
          question: 'What is the main contribution of this paper?',
          paperIds: [testPaperId],
          queryType: 'single',
        })
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toMatchObject({
        question: 'What is the main contribution of this paper?',
        status: 'completed',
        paperIds: [testPaperId],
      });
      expect(response.body.data.id).toBeDefined();
      expect(response.body.data.answer).toBeDefined();
      expect(response.body.data.sources).toBeDefined();
      expect(response.body.data.confidence).toBeGreaterThanOrEqual(0);
      expect(response.body.data.cached).toBeDefined();
    });

    it('should reject missing question', async () => {
      const response = await request(app)
        .post('/api/queries')
        .set('Authorization', `Bearer ${accessToken}`)
        .send({
          paperIds: [testPaperId],
        })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/validation-error');
    });

    it('should reject missing paperIds', async () => {
      const response = await request(app)
        .post('/api/queries')
        .set('Authorization', `Bearer ${accessToken}`)
        .send({
          question: 'Test question',
        })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/validation-error');
    });

    it('should reject unauthenticated requests', async () => {
      const response = await request(app)
        .post('/api/queries')
        .send({
          question: 'Test question',
          paperIds: [testPaperId],
        })
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/unauthorized');
    });

    it('should reject empty paperIds array', async () => {
      const response = await request(app)
        .post('/api/queries')
        .set('Authorization', `Bearer ${accessToken}`)
        .send({
          question: 'Test question',
          paperIds: [],
        })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/validation-error');
    });
  });

  describe('GET /api/queries', () => {
    let createdQueryId: string;

    beforeAll(async () => {
      // Create a query for listing tests
      const response = await request(app)
        .post('/api/queries')
        .set('Authorization', `Bearer ${accessToken}`)
        .send({
          question: 'List test query',
          paperIds: [testPaperId],
        })
        .expect(200);

      createdQueryId = response.body.data.id;
    });

    it('should return paginated query list', async () => {
      const response = await request(app)
        .get('/api/queries')
        .set('Authorization', `Bearer ${accessToken}`)
        .query({ page: 1, limit: 10 })
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.queries).toBeInstanceOf(Array);
      expect(response.body.data.queries.length).toBeGreaterThan(0);
      expect(response.body.data.pagination).toMatchObject({
        page: 1,
        limit: 10,
      });
      expect(response.body.data.pagination.total).toBeGreaterThan(0);
    });

    it('should filter by status', async () => {
      const response = await request(app)
        .get('/api/queries')
        .set('Authorization', `Bearer ${accessToken}`)
        .query({ status: 'completed' })
        .expect(200);

      expect(response.body.success).toBe(true);
      response.body.data.queries.forEach((q: { status: string }) => {
        expect(q.status).toBe('completed');
      });
    });

    it('should filter by queryType', async () => {
      const response = await request(app)
        .get('/api/queries')
        .set('Authorization', `Bearer ${accessToken}`)
        .query({ queryType: 'single' })
        .expect(200);

      expect(response.body.success).toBe(true);
      response.body.data.queries.forEach((q: { queryType: string }) => {
        expect(q.queryType).toBe('single');
      });
    });

    it('should reject unauthenticated requests', async () => {
      const response = await request(app)
        .get('/api/queries')
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/unauthorized');
    });

    it('should return empty list for page beyond total', async () => {
      const response = await request(app)
        .get('/api/queries')
        .set('Authorization', `Bearer ${accessToken}`)
        .query({ page: 999, limit: 10 })
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.queries.length).toBe(0);
    });
  });

  describe('GET /api/queries/:id', () => {
    let queryId: string;

    beforeAll(async () => {
      const response = await request(app)
        .post('/api/queries')
        .set('Authorization', `Bearer ${accessToken}`)
        .send({
          question: 'Detail test query',
          paperIds: [testPaperId],
        })
        .expect(200);

      queryId = response.body.data.id;
    });

    it('should return query details', async () => {
      const response = await request(app)
        .get(`/api/queries/${queryId}`)
        .set('Authorization', `Bearer ${accessToken}`)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toMatchObject({
        id: queryId,
        question: 'Detail test query',
        status: 'completed',
      });
      expect(response.body.data.answer).toBeDefined();
      expect(response.body.data.sources).toBeDefined();
    });

    it('should return 404 for non-existent query', async () => {
      const response = await request(app)
        .get('/api/queries/non-existent-id')
        .set('Authorization', `Bearer ${accessToken}`)
        .expect(404);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/not-found');
    });

    it('should reject unauthenticated requests', async () => {
      const response = await request(app)
        .get(`/api/queries/${queryId}`)
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/unauthorized');
    });

    it('should not return other user\'s query', async () => {
      // Create another user
      const otherUserData = generateTestUserData();
      await request(app)
        .post('/api/auth/register')
        .send(otherUserData)
        .expect(201);

      const otherLoginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: otherUserData.email,
          password: otherUserData.password,
        })
        .expect(200);

      const otherAccessToken = otherLoginResponse.body.meta.accessToken;

      // Try to access first user's query
      const response = await request(app)
        .get(`/api/queries/${queryId}`)
        .set('Authorization', `Bearer ${otherAccessToken}`)
        .expect(404);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/not-found');
    });
  });

  describe('DELETE /api/queries/:id', () => {
    let queryId: string;

    beforeEach(async () => {
      const response = await request(app)
        .post('/api/queries')
        .set('Authorization', `Bearer ${accessToken}`)
        .send({
          question: 'Delete test query',
          paperIds: [testPaperId],
        })
        .expect(200);

      queryId = response.body.data.id;
    });

    it('should delete query', async () => {
      const response = await request(app)
        .delete(`/api/queries/${queryId}`)
        .set('Authorization', `Bearer ${accessToken}`)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.message).toBe('Query deleted');

      // Verify deleted
      const getResponse = await request(app)
        .get(`/api/queries/${queryId}`)
        .set('Authorization', `Bearer ${accessToken}`)
        .expect(404);

      expect(getResponse.body.success).toBe(false);
    });

    it('should return 404 for non-existent query', async () => {
      const response = await request(app)
        .delete('/api/queries/non-existent-id')
        .set('Authorization', `Bearer ${accessToken}`)
        .expect(404);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/not-found');
    });

    it('should reject unauthenticated requests', async () => {
      const response = await request(app)
        .delete(`/api/queries/${queryId}`)
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/unauthorized');
    });
  });

  describe('Performance and Integration', () => {
    it('should track durationMs for queries', async () => {
      const response = await request(app)
        .post('/api/queries')
        .set('Authorization', `Bearer ${accessToken}`)
        .send({
          question: 'Performance test query',
          paperIds: [testPaperId],
        })
        .expect(200);

      expect(response.body.data.durationMs).toBeDefined();
      expect(response.body.data.durationMs).toBeGreaterThan(0);
    });

    it('should handle multiple queries concurrently', async () => {
      const promises = Array.from({ length: 5 }, (_, i) =>
        request(app)
          .post('/api/queries')
          .set('Authorization', `Bearer ${accessToken}`)
          .send({
            question: `Concurrent query ${i}`,
            paperIds: [testPaperId],
          })
      );

      const responses = await Promise.all(promises);

      responses.forEach((response) => {
        expect(response.status).toBe(200);
        expect(response.body.success).toBe(true);
        expect(response.body.data.id).toBeDefined();
      });
    });
  });
});