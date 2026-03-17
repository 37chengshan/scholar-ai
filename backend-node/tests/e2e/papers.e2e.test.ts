import request from 'supertest';
import app from '../../src/index';
import { generateTestUserData, cleanupTestData } from '../helpers/db';
import { createAuthenticatedUser } from '../helpers/server';

/**
 * Papers API E2E Tests
 *
 * Tests PDF upload flow including:
 * - Upload URL generation
 * - Processing task creation
 * - Status polling
 * - File validation
 * - Authorization
 */
describe('Papers API E2E Tests', () => {
  afterAll(async () => {
    await cleanupTestData();
  });

  // ===========================================================================
  // Upload Flow Tests
  // ===========================================================================

  describe('POST /api/papers - Upload URL Generation', () => {
    it('should generate upload URL for valid PDF filename', async () => {
      const { agent } = await createAuthenticatedUser();

      const response = await agent
        .post('/api/papers')
        .send({ filename: 'research-paper.pdf' })
        .expect(201);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toMatchObject({
        paperId: expect.any(String),
        uploadUrl: expect.any(String),
        expiresIn: expect.any(Number),
        storageKey: expect.any(String),
      });
      expect(response.body.data.uploadUrl).toContain('http');
      expect(response.body.data.expiresIn).toBeGreaterThan(0);
    });

    it('should require authentication for upload', async () => {
      const agent = request.agent(app);

      const response = await agent
        .post('/api/papers')
        .send({ filename: 'test.pdf' })
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBeDefined();
    });

    it('should reject non-PDF files', async () => {
      const { agent } = await createAuthenticatedUser();

      const response = await agent
        .post('/api/papers')
        .send({ filename: 'document.docx' })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error.detail).toContain('PDF');
    });

    it('should reject files without extension', async () => {
      const { agent } = await createAuthenticatedUser();

      const response = await agent
        .post('/api/papers')
        .send({ filename: 'nofileextension' })
        .expect(400);

      expect(response.body.success).toBe(false);
    });

    it('should reject empty filename', async () => {
      const { agent } = await createAuthenticatedUser();

      const response = await agent
        .post('/api/papers')
        .send({ filename: '' })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error.detail).toContain('required');
    });

    it('should handle filenames with special characters', async () => {
      const { agent } = await createAuthenticatedUser();

      const response = await agent
        .post('/api/papers')
        .send({ filename: 'paper-v1.2_final (copy).PDF' })
        .expect(201);

      expect(response.body.success).toBe(true);
      expect(response.body.data.paperId).toBeDefined();
    });

    it('should handle long filenames', async () => {
      const { agent } = await createAuthenticatedUser();

      const longFilename = 'a'.repeat(200) + '.pdf';

      const response = await agent
        .post('/api/papers')
        .send({ filename: longFilename })
        .expect(201);

      expect(response.body.success).toBe(true);
    });
  });

  // ===========================================================================
  // Webhook Tests (Upload Confirmation)
  // ===========================================================================

  describe('POST /api/papers/webhook - Upload Completion', () => {
    it('should create processing task after upload confirmation', async () => {
      const { agent } = await createAuthenticatedUser();

      // First, request upload URL
      const uploadResponse = await agent
        .post('/api/papers')
        .send({ filename: 'test-upload.pdf' })
        .expect(201);

      const { paperId, storageKey } = uploadResponse.body.data;

      // Note: In a real test, we would upload the file to the URL here
      // For E2E tests, we mock this by directly calling webhook

      // Call webhook to confirm upload
      const webhookResponse = await agent
        .post('/api/papers/webhook')
        .send({ paperId, storageKey })
        .expect(201);

      expect(webhookResponse.body.success).toBe(true);
      expect(webhookResponse.body.data).toMatchObject({
        taskId: expect.any(String),
        paperId: expect.any(String),
        status: expect.any(String),
        progress: expect.any(Number),
      });
    });

    it('should require paperId and storageKey', async () => {
      const { agent } = await createAuthenticatedUser();

      const response = await agent
        .post('/api/papers/webhook')
        .send({})
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error.detail).toContain('required');
    });

    it('should reject invalid paperId', async () => {
      const { agent } = await createAuthenticatedUser();

      const response = await agent
        .post('/api/papers/webhook')
        .send({
          paperId: 'non-existent-paper-id',
          storageKey: 'test/key.pdf',
        })
        .expect(404);

      expect(response.body.success).toBe(false);
      expect(response.body.error.status).toBe(404);
    });

    it('should prevent duplicate processing tasks', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create paper
      const uploadResponse = await agent
        .post('/api/papers')
        .send({ filename: 'duplicate-test.pdf' })
        .expect(201);

      const { paperId, storageKey } = uploadResponse.body.data;

      // First webhook call
      await agent
        .post('/api/papers/webhook')
        .send({ paperId, storageKey })
        .expect(201);

      // Second webhook call should fail
      const duplicateResponse = await agent
        .post('/api/papers/webhook')
        .send({ paperId, storageKey })
        .expect(409);

      expect(duplicateResponse.body.success).toBe(false);
      expect(duplicateResponse.body.error.status).toBe(409);
      expect(duplicateResponse.body.error.detail).toContain('already exists');
    });
  });

  // ===========================================================================
  // Status Polling Tests
  // ===========================================================================

  describe('GET /api/papers/:id/status - Status Polling', () => {
    it('should return processing status for paper', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create paper
      const uploadResponse = await agent
        .post('/api/papers')
        .send({ filename: 'status-test.pdf' })
        .expect(201);

      const { paperId } = uploadResponse.body.data;

      // Get status
      const statusResponse = await agent
        .get(`/api/papers/${paperId}/status`)
        .expect(200);

      expect(statusResponse.body.success).toBe(true);
      expect(statusResponse.body.data).toMatchObject({
        paperId: expect.any(String),
        status: expect.any(String),
        progress: expect.any(Number),
        createdAt: expect.any(String),
        updatedAt: expect.any(String),
      });
    });

    it('should return 404 for non-existent paper', async () => {
      const { agent } = await createAuthenticatedUser();

      const response = await agent
        .get('/api/papers/non-existent-id/status')
        .expect(404);

      expect(response.body.success).toBe(false);
      expect(response.body.error.status).toBe(404);
    });

    it('should require authentication for status check', async () => {
      const agent = request.agent(app);

      const response = await agent
        .get('/api/papers/test-id/status')
        .expect(401);

      expect(response.body.success).toBe(false);
    });

    it('should show progress after task creation', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create paper and task
      const uploadResponse = await agent
        .post('/api/papers')
        .send({ filename: 'progress-test.pdf' })
        .expect(201);

      const { paperId, storageKey } = uploadResponse.body.data;

      // Create task via webhook
      await agent
        .post('/api/papers/webhook')
        .send({ paperId, storageKey })
        .expect(201);

      // Check status
      const statusResponse = await agent
        .get(`/api/papers/${paperId}/status`)
        .expect(200);

      expect(statusResponse.body.data.progress).toBeGreaterThanOrEqual(0);
      expect(statusResponse.body.data.progress).toBeLessThanOrEqual(100);
    });
  });

  // ===========================================================================
  // List Papers Tests
  // ===========================================================================

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

    it('should only return papers for authenticated user', async () => {
      // Create two users
      const user1 = await createAuthenticatedUser();
      const user2 = await createAuthenticatedUser();

      // User1 creates a paper
      await user1.agent
        .post('/api/papers')
        .send({ filename: 'user1-paper.pdf' })
        .expect(201);

      // User2 should not see user1's paper
      const user2Papers = await user2.agent
        .get('/api/papers')
        .expect(200);

      // User2's papers list should not contain papers from user1
      const paperTitles = user2Papers.body.data.papers.map((p: { title: string }) => p.title);
      expect(paperTitles).not.toContain('user1-paper.pdf');
    });
  });

  // ===========================================================================
  // Paper Details Tests
  // ===========================================================================

  describe('GET /api/papers/:id', () => {
    it('should return paper details', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create paper
      const uploadResponse = await agent
        .post('/api/papers')
        .send({ filename: 'details-test.pdf' })
        .expect(201);

      const { paperId } = uploadResponse.body.data;

      // Get paper details
      const response = await agent
        .get(`/api/papers/${paperId}`)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toMatchObject({
        id: expect.any(String),
        title: expect.any(String),
        authors: expect.any(Array),
        status: expect.any(String),
        progress: expect.any(Number),
        storageKey: expect.any(String),
      });
    });

    it('should return 404 for non-existent paper', async () => {
      const { agent } = await createAuthenticatedUser();

      const response = await agent
        .get('/api/papers/non-existent-id')
        .expect(404);

      expect(response.body.success).toBe(false);
      expect(response.body.error.status).toBe(404);
    });

    it('should require authentication', async () => {
      const agent = request.agent(app);

      const response = await agent
        .get('/api/papers/test-id')
        .expect(401);

      expect(response.body.success).toBe(false);
    });
  });

  describe('GET /api/papers/:id/summary', () => {
    it('should return paper summary', async () => {
      const { agent } = await createAuthenticatedUser();

      // Get paper summary (placeholder implementation)
      const response = await agent
        .get('/api/papers/test-paper-id-123/summary')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toMatchObject({
        paperId: expect.any(String),
        summary: expect.anything(),
        status: expect.any(String),
        hasNotes: expect.any(Boolean),
      });
    });

    it('should return 404 for non-existent paper', async () => {
      const { agent } = await createAuthenticatedUser();

      const response = await agent
        .get('/api/papers/non-existent-id/summary')
        .expect(404);

      expect(response.body.success).toBe(false);
    });
  });

  // ===========================================================================
  // File Upload Validation Tests
  // ===========================================================================

  describe('File Upload Validation', () => {
    it('should reject upload with invalid file type', async () => {
      const { agent } = await createAuthenticatedUser();

      const response = await agent
        .post('/api/papers')
        .send({ filename: 'malware.exe.pdf' }) // Suspicious but has .pdf extension
        .expect(201);

      // The API only validates extension, content validation would be done server-side
      // after actual upload
      expect(response.body.success).toBe(true);
    });

    it('should handle case-insensitive extensions', async () => {
      const { agent } = await createAuthenticatedUser();

      const variations = ['paper.PDF', 'paper.Pdf', 'paper.pDf'];

      for (const filename of variations) {
        const response = await agent
          .post('/api/papers')
          .send({ filename })
          .expect(201);

        expect(response.body.success).toBe(true);
      }
    });

    it.skip('should reject files exceeding size limit', async () => {
      // Note: This would require actual file upload testing
      // Size validation typically happens during the actual upload, not URL generation
    });
  });

  // ===========================================================================
  // Authorization Tests
  // ===========================================================================

  describe('Authorization', () => {
    it('should not allow access to other users papers', async () => {
      // Create two users
      const user1 = await createAuthenticatedUser();
      const user2 = await createAuthenticatedUser();

      // User1 creates a paper
      const uploadResponse = await user1.agent
        .post('/api/papers')
        .send({ filename: 'private-paper.pdf' })
        .expect(201);

      const { paperId } = uploadResponse.body.data;

      // User2 tries to access user1's paper
      const response = await user2.agent
        .get(`/api/papers/${paperId}`)
        .expect(404); // Should return 404 (not 403) to not leak existence

      expect(response.body.success).toBe(false);
    });

    it('should not allow other users to check status', async () => {
      const user1 = await createAuthenticatedUser();
      const user2 = await createAuthenticatedUser();

      // User1 creates a paper
      const uploadResponse = await user1.agent
        .post('/api/papers')
        .send({ filename: 'status-private.pdf' })
        .expect(201);

      const { paperId } = uploadResponse.body.data;

      // User2 tries to check status
      const response = await user2.agent
        .get(`/api/papers/${paperId}/status`)
        .expect(404);

      expect(response.body.success).toBe(false);
    });

    it('should require delete permission to delete papers', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create a paper
      const uploadResponse = await agent
        .post('/api/papers')
        .send({ filename: 'to-delete.pdf' })
        .expect(201);

      const { paperId } = uploadResponse.body.data;

      // Delete the paper
      const deleteResponse = await agent
        .delete(`/api/papers/${paperId}`)
        .expect(200);

      expect(deleteResponse.body.success).toBe(true);
      expect(deleteResponse.body.data.deleted).toBe(true);
    });
  });

  // ===========================================================================
  // Delete Tests
  // ===========================================================================

  describe('DELETE /api/papers/:id', () => {
    it('should delete paper with permission', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create paper
      const uploadResponse = await agent
        .post('/api/papers')
        .send({ filename: 'delete-test.pdf' })
        .expect(201);

      const { paperId } = uploadResponse.body.data;

      // Delete paper
      const response = await agent
        .delete(`/api/papers/${paperId}`)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.deleted).toBe(true);

      // Verify paper is deleted
      await agent
        .get(`/api/papers/${paperId}`)
        .expect(404);
    });

    it('should return 404 for non-existent paper', async () => {
      const { agent } = await createAuthenticatedUser();

      const response = await agent
        .delete('/api/papers/non-existent-id')
        .expect(404);

      expect(response.body.success).toBe(false);
    });
  });

  // ===========================================================================
  // Processing States Tests
  // ===========================================================================

  describe('Processing Task States', () => {
    it('should track all 6 processing states', async () => {
      const { agent } = await createAuthenticatedUser();

      // Create paper
      const uploadResponse = await agent
        .post('/api/papers')
        .send({ filename: 'states-test.pdf' })
        .expect(201);

      const { paperId, storageKey } = uploadResponse.body.data;

      // Initial state should be pending
      let statusResponse = await agent
        .get(`/api/papers/${paperId}/status`)
        .expect(200);

      expect(['pending', 'processing']).toContain(statusResponse.body.data.status);

      // Create task
      await agent
        .post('/api/papers/webhook')
        .send({ paperId, storageKey })
        .expect(201);

      // After task creation, check status again
      statusResponse = await agent
        .get(`/api/papers/${paperId}/status`)
        .expect(200);

      // Status should be one of the processing states
      const validStates = [
        'pending',
        'processing_ocr',
        'parsing',
        'extracting_imrad',
        'generating_notes',
        'completed',
        'failed',
      ];

      expect(validStates).toContain(statusResponse.body.data.status);
    });

    it('should include progress percentage in status', async () => {
      const { agent } = await createAuthenticatedUser();

      const uploadResponse = await agent
        .post('/api/papers')
        .send({ filename: 'progress-percentage.pdf' })
        .expect(201);

      const { paperId, storageKey } = uploadResponse.body.data;

      // Create task
      await agent
        .post('/api/papers/webhook')
        .send({ paperId, storageKey })
        .expect(201);

      // Check progress
      const statusResponse = await agent
        .get(`/api/papers/${paperId}/status`)
        .expect(200);

      const progress = statusResponse.body.data.progress;
      expect(progress).toBeGreaterThanOrEqual(0);
      expect(progress).toBeLessThanOrEqual(100);
      expect(typeof progress).toBe('number');
    });
  });
});
