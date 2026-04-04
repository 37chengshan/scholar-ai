import request from 'supertest';
import app from '../../src/index';
import { prisma } from '../../src/config/database';
import { createAuthenticatedUser } from '../helpers/server';
import { cleanupTestData } from '../helpers/db';

/**
 * Paper Starred Feature Tests
 * 
 * Tests for:
 * - PATCH /api/papers/:id/starred - Toggle starred status
 * - GET /api/papers?starred=true - Filter starred papers
 */
describe('Paper Starred Feature', () => {
  afterAll(async () => {
    await cleanupTestData();
  });

  // ===========================================================================
  // PATCH /api/papers/:id/starred Tests
  // ===========================================================================

  describe('PATCH /api/papers/:id/starred', () => {
    it('should star a paper', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create a paper first
      const uploadResponse = await agent
        .post('/api/papers')
        .send({ filename: 'star-test.pdf' })
        .expect(201);

      const { paperId } = uploadResponse.body.data;

      // Star the paper
      const response = await agent
        .patch(`/api/papers/${paperId}/starred`)
        .send({ starred: true })
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.starred).toBe(true);
    });

    it('should unstar a paper', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create a paper
      const uploadResponse = await agent
        .post('/api/papers')
        .send({ filename: 'unstar-test.pdf' })
        .expect(201);

      const { paperId } = uploadResponse.body.data;

      // Star it first
      await agent
        .patch(`/api/papers/${paperId}/starred`)
        .send({ starred: true })
        .expect(200);

      // Then unstar it
      const response = await agent
        .patch(`/api/papers/${paperId}/starred`)
        .send({ starred: false })
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.starred).toBe(false);
    });

    it('should return 404 for non-existent paper', async () => {
      const { agent } = await createAuthenticatedUser();

      const response = await agent
        .patch('/api/papers/non-existent-id/starred')
        .send({ starred: true })
        .expect(404);

      expect(response.body.success).toBe(false);
      expect(response.body.error.status).toBe(404);
    });

    it('should require authentication', async () => {
      const agent = request.agent(app);

      const response = await agent
        .patch('/api/papers/test-id/starred')
        .send({ starred: true })
        .expect(401);

      expect(response.body.success).toBe(false);
    });

    it('should not allow starring other users papers', async () => {
      // Create two users
      const user1 = await createAuthenticatedUser();
      const user2 = await createAuthenticatedUser();

      // User1 creates a paper
      const uploadResponse = await user1.agent
        .post('/api/papers')
        .send({ filename: 'private-paper.pdf' })
        .expect(201);

      const { paperId } = uploadResponse.body.data;

      // User2 tries to star User1's paper
      const response = await user2.agent
        .patch(`/api/papers/${paperId}/starred`)
        .send({ starred: true })
        .expect(404); // Should return 404 to not leak existence

      expect(response.body.success).toBe(false);
    });

    it('should require starred boolean in request body', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create a paper
      const uploadResponse = await agent
        .post('/api/papers')
        .send({ filename: 'validation-test.pdf' })
        .expect(201);

      const { paperId } = uploadResponse.body.data;

      // Try to patch without starred field
      const response = await agent
        .patch(`/api/papers/${paperId}/starred`)
        .send({})
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error.detail).toContain('starred');
    });
  });

  // ===========================================================================
  // GET /api/papers?starred=true Tests
  // ===========================================================================

  describe('GET /api/papers?starred=true', () => {
    it('should return only starred papers when starred=true', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create multiple papers
      const paper1 = await agent
        .post('/api/papers')
        .send({ filename: 'starred-paper.pdf' })
        .expect(201);

      const paper2 = await agent
        .post('/api/papers')
        .send({ filename: 'unstarred-paper.pdf' })
        .expect(201);

      // Star only paper1
      await agent
        .patch(`/api/papers/${paper1.body.data.paperId}/starred`)
        .send({ starred: true })
        .expect(200);

      // Get starred papers
      const response = await agent
        .get('/api/papers?starred=true')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.papers).toHaveLength(1);
      expect(response.body.data.papers[0].id).toBe(paper1.body.data.paperId);
    });

    it('should return only unstarred papers when starred=false', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create multiple papers
      const paper1 = await agent
        .post('/api/papers')
        .send({ filename: 'starred-paper2.pdf' })
        .expect(201);

      const paper2 = await agent
        .post('/api/papers')
        .send({ filename: 'unstarred-paper2.pdf' })
        .expect(201);

      // Star only paper1
      await agent
        .patch(`/api/papers/${paper1.body.data.paperId}/starred`)
        .send({ starred: true })
        .expect(200);

      // Get unstarred papers
      const response = await agent
        .get('/api/papers?starred=false')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.papers.length).toBeGreaterThanOrEqual(1);
      
      // Check that paper2 is in the results and paper1 is not
      const paperIds = response.body.data.papers.map((p: { id: string }) => p.id);
      expect(paperIds).toContain(paper2.body.data.paperId);
      expect(paperIds).not.toContain(paper1.body.data.paperId);
    });

    it('should return all papers when starred parameter not provided', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create papers
      await agent
        .post('/api/papers')
        .send({ filename: 'paper-a.pdf' })
        .expect(201);

      await agent
        .post('/api/papers')
        .send({ filename: 'paper-b.pdf' })
        .expect(201);

      // Get all papers (no starred filter)
      const response = await agent
        .get('/api/papers')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.papers.length).toBeGreaterThanOrEqual(2);
    });

    it('should include starred field in paper response', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create a paper
      const uploadResponse = await agent
        .post('/api/papers')
        .send({ filename: 'check-field.pdf' })
        .expect(201);

      const { paperId } = uploadResponse.body.data;

      // Get paper details
      const response = await agent
        .get(`/api/papers/${paperId}`)
        .expect(200);

      expect(response.body.data).toHaveProperty('starred');
      expect(typeof response.body.data.starred).toBe('boolean');
    });
  });
});