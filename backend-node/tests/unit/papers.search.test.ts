import request from 'supertest';
import app from '../../src/index';
import { prisma } from '../../src/config/database';
import { createAuthenticatedUser } from '../helpers/server';
import { cleanupTestData } from '../helpers/db';

/**
 * Paper Search Feature Tests
 *
 * Tests for GET /api/papers/search endpoint:
 * - Multi-field search (title, authors, abstract)
 * - Pagination
 * - User isolation
 * - Query validation
 */
describe('Paper Search Feature', () => {
  afterAll(async () => {
    await cleanupTestData();
  });

  // ===========================================================================
  // GET /api/papers/search Tests
  // ===========================================================================

  describe('GET /api/papers/search', () => {
    it('should search papers by title', async () => {
      const { agent, userId } = await createAuthenticatedUser();

      // Create papers with different titles
      await agent
        .post('/api/papers')
        .send({ filename: 'Machine Learning Basics.pdf' })
        .expect(201);

      await agent
        .post('/api/papers')
        .send({ filename: 'Deep Neural Networks.pdf' })
        .expect(201);

      // Search for "Machine"
      const response = await agent
        .get('/api/papers/search?q=Machine')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toMatchObject({
        papers: expect.any(Array),
        total: expect.any(Number),
        page: expect.any(Number),
        limit: expect.any(Number),
        query: 'Machine',
      });
      
      // Should find "Machine Learning Basics"
      const titles = response.body.data.papers.map((p: { title: string }) => p.title);
      expect(titles.some((t: string) => t.includes('Machine'))).toBe(true);
    });

    it('should search papers case-insensitively', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create paper
      await agent
        .post('/api/papers')
        .send({ filename: 'Neural Networks.pdf' })
        .expect(201);

      // Search with different case
      const response = await agent
        .get('/api/papers/search?q=NEURAL')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.total).toBeGreaterThanOrEqual(1);
    });

    it('should return empty results for non-matching query', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create paper
      await agent
        .post('/api/papers')
        .send({ filename: 'Quantum Computing.pdf' })
        .expect(201);

      // Search for something that doesn't match
      const response = await agent
        .get('/api/papers/search?q=baking')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.papers).toHaveLength(0);
      expect(response.body.data.total).toBe(0);
    });

    it('should require query parameter q', async () => {
      const { agent } = await createAuthenticatedUser();

      // Missing q parameter
      const response = await agent
        .get('/api/papers/search')
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error.detail).toContain('required');
    });

    it('should validate query length (1-100 chars)', async () => {
      const { agent } = await createAuthenticatedUser();

      // Empty query
      const emptyResponse = await agent
        .get('/api/papers/search?q=')
        .expect(400);

      expect(emptyResponse.body.success).toBe(false);

      // Too long query
      const longQuery = 'a'.repeat(101);
      const longResponse = await agent
        .get(`/api/papers/search?q=${longQuery}`)
        .expect(400);

      expect(longResponse.body.success).toBe(false);
    });

    it('should support pagination parameters', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create multiple papers
      for (let i = 0; i < 5; i++) {
        await agent
          .post('/api/papers')
          .send({ filename: `Research Paper ${i}.pdf` })
          .expect(201);
      }

      // Search with pagination
      const response = await agent
        .get('/api/papers/search?q=Research&page=1&limit=2')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.page).toBe(1);
      expect(response.body.data.limit).toBe(2);
      expect(response.body.data.papers.length).toBeLessThanOrEqual(2);
    });

    it('should require authentication', async () => {
      const agent = request.agent(app);

      const response = await agent
        .get('/api/papers/search?q=test')
        .expect(401);

      expect(response.body.success).toBe(false);
    });

    it('should only search user own papers', async () => {
      // Create two users
      const user1 = await createAuthenticatedUser();
      const user2 = await createAuthenticatedUser();

      // User1 creates paper
      await user1.agent
        .post('/api/papers')
        .send({ filename: 'User1 Private Paper.pdf' })
        .expect(201);

      // User2 searches - should not find User1's paper
      const response = await user2.agent
        .get('/api/papers/search?q=User1')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.total).toBe(0);
      expect(response.body.data.papers).toHaveLength(0);
    });

    it('should include processing status in results', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create paper
      await agent
        .post('/api/papers')
        .send({ filename: 'Status Test Paper.pdf' })
        .expect(201);

      // Search
      const response = await agent
        .get('/api/papers/search?q=Status')
        .expect(200);

      expect(response.body.success).toBe(true);
      
      if (response.body.data.papers.length > 0) {
        const paper = response.body.data.papers[0];
        expect(paper).toHaveProperty('processingStatus');
        expect(paper).toHaveProperty('progress');
        expect(typeof paper.progress).toBe('number');
      }
    });

    it('should search by partial title match', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create paper with long title
      await agent
        .post('/api/papers')
        .send({ filename: 'Advanced Methods for Natural Language Processing.pdf' })
        .expect(201);

      // Search for partial word
      const response = await agent
        .get('/api/papers/search?q=Language')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.total).toBeGreaterThanOrEqual(1);
    });
  });
});