import request from 'supertest';
import { generateTestUserData } from '../helpers/db';

// 动态导入 app 和 prisma，确保环境变量先加载
let app: any;
let prisma: any;

/**
 * E2E Tests for External Paper Add Flow
 *
 * Tests: POST /api/search/external
 *        GET /api/papers/:id/status
 */

describe('External Paper Add E2E Tests', () => {
  const testUser = { id: '', email: '', password: 'Test123!', name: '' };
  let authToken: string;
  let agent: request.Agent;

  beforeAll(async () => {
    // 动态导入，确保 setup.ts 先执行
    const { default: importedApp } = await import('../../src/index');
    const { prisma: importedPrisma } = await import('../../src/config/database');
    app = importedApp;
    prisma = importedPrisma;

    agent = request.agent(app);

    // Create test user and login
    const userData = generateTestUserData();
    testUser.email = userData.email;
    testUser.password = userData.password;
    testUser.name = userData.name;

    // Register
    const registerRes = await agent
      .post('/api/auth/register')
      .send({
        email: testUser.email,
        password: testUser.password,
        name: testUser.name,
      });

    if (registerRes.body.data?.id) {
      testUser.id = registerRes.body.data.id;
    }

    // Login
    const loginRes = await agent
      .post('/api/auth/login')
      .send({
        email: testUser.email,
        password: testUser.password,
      });

    if (loginRes.body.data?.user?.id) {
      testUser.id = loginRes.body.data.user.id;
    }

    // Get auth token from cookies
    const cookies = loginRes.headers['set-cookie'];
    if (cookies && Array.isArray(cookies)) {
      const accessTokenCookie = cookies.find((c: string) => c.includes('accessToken'));
      if (accessTokenCookie) {
        const match = accessTokenCookie.match(/accessToken=([^;]+)/);
        if (match) authToken = match[1];
      }
    }
  });

  afterEach(async () => {
    // Clean up test papers for this user
    if (testUser.id) {
      await prisma.paper.deleteMany({
        where: { userId: testUser.id },
      });
    }
  });

  afterAll(async () => {
    // Clean up test user
    if (testUser.id) {
      await prisma.paper.deleteMany({
        where: { userId: testUser.id },
      });
      await prisma.user.deleteMany({
        where: { id: testUser.id },
      });
    }
  });

  describe('POST /api/search/external', () => {
    it('should add external paper with PDF URL and trigger download', async () => {
      const response = await agent
        .post('/api/search/external')
        .send({
          source: 'arxiv',
          externalId: '2401.12345',
          title: 'Test Paper with PDF',
          authors: ['Test Author'],
          year: 2024,
          abstract: 'Test abstract',
          pdfUrl: 'https://arxiv.org/pdf/2401.12345.pdf',
        })
        .expect(201);

      expect(response.body.success).toBe(true);
      expect(response.body.data.paperId).toBeDefined();
      expect(response.body.data.status).toBe('pending');
      expect(response.body.data.downloadTriggered).toBeDefined();
      expect(response.body.data.message).toContain('PDF download');
    });

    it('should add external paper without PDF URL and skip download', async () => {
      const response = await agent
        .post('/api/search/external')
        .send({
          source: 'arxiv',
          externalId: '2401.12346',
          title: 'Test Paper without PDF',
          authors: ['Test Author'],
          year: 2024,
          abstract: 'Test abstract',
          // No pdfUrl provided
        })
        .expect(201);

      expect(response.body.success).toBe(true);
      expect(response.body.data.paperId).toBeDefined();
      expect(response.body.data.status).toBe('pending');
      expect(response.body.data.downloadTriggered).toBe(false);
      expect(response.body.data.message).toContain('without PDF');
    });

    it('should return 409 for duplicate arXiv ID', async () => {
      const arxivId = '2401.99999';

      // First add
      const firstResponse = await agent
        .post('/api/search/external')
        .send({
          source: 'arxiv',
          externalId: arxivId,
          title: 'First Paper',
          authors: ['Author'],
          year: 2024,
        })
        .expect(201);

      const existingPaperId = firstResponse.body.data.paperId;

      // Second add with same arXiv ID
      const response = await agent
        .post('/api/search/external')
        .send({
          source: 'arxiv',
          externalId: arxivId,
          title: 'Duplicate Paper',
          authors: ['Author'],
          year: 2024,
        })
        .expect(409);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/duplicate-paper');
      expect(response.body.error.status).toBe(409);
      expect(response.body.error.existingPaperId).toBe(existingPaperId);
    });

    it('should return 409 for duplicate title', async () => {
      const title = 'Unique Title For Duplicate Test';

      // First add
      const firstResponse = await agent
        .post('/api/search/external')
        .send({
          source: 'arxiv',
          externalId: '2401.88888',
          title: title,
          authors: ['Author'],
          year: 2024,
        })
        .expect(201);

      const existingPaperId = firstResponse.body.data.paperId;

      // Second add with same title (different arXiv ID)
      const response = await agent
        .post('/api/search/external')
        .send({
          source: 'arxiv',
          externalId: '2401.88889',
          title: title,
          authors: ['Author'],
          year: 2024,
        })
        .expect(409);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/duplicate-paper');
      expect(response.body.error.status).toBe(409);
      expect(response.body.error.existingPaperId).toBe(existingPaperId);
    });

    it('should return 400 for missing required fields', async () => {
      const response = await agent
        .post('/api/search/external')
        .send({
          // Missing title, source, externalId
          authors: ['Author'],
        })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/validation-error');
      expect(response.body.error.status).toBe(400);
    });

    it('should return 401 for unauthenticated request', async () => {
      const response = await request(app)
        .post('/api/search/external')
        .send({
          source: 'arxiv',
          externalId: '2401.77777',
          title: 'Unauthorized Paper',
        })
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.status).toBe(401);
    });

    it('should handle case-insensitive title matching', async () => {
      const title = 'CASE Insensitive Test';

      // First add
      await agent
        .post('/api/search/external')
        .send({
          source: 'arxiv',
          externalId: '2401.77776',
          title: title,
          authors: ['Author'],
          year: 2024,
        })
        .expect(201);

      // Second add with different case
      const response = await agent
        .post('/api/search/external')
        .send({
          source: 'arxiv',
          externalId: '2401.77775',
          title: title.toLowerCase(),
          authors: ['Author'],
          year: 2024,
        })
        .expect(409);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/duplicate-paper');
    });
  });

  describe('GET /api/papers/:id/status', () => {
    it('should return correct progress for pending status', async () => {
      // Create a paper
      const createResponse = await agent
        .post('/api/search/external')
        .send({
          source: 'arxiv',
          externalId: '2401.66666',
          title: 'Status Test Paper',
          authors: ['Author'],
          year: 2024,
        })
        .expect(201);

      const paperId = createResponse.body.data.paperId;

      // Get status
      const response = await agent
        .get(`/api/papers/${paperId}/status`)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.paperId).toBe(paperId);
      expect(response.body.data.title).toBe('Status Test Paper');
      expect(response.body.data.status).toBe('pending');
      expect(response.body.data.progress).toBe(10);
      expect(response.body.data.errorMessage).toBeNull();
      expect(response.body.data.updatedAt).toBeDefined();
    });

    it('should return 404 for non-existent paper', async () => {
      const response = await agent
        .get('/api/papers/non-existent-paper-id/status')
        .expect(404);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/not-found');
      expect(response.body.error.status).toBe(404);
    });

    it('should return 401 for unauthenticated status request', async () => {
      const response = await request(app)
        .get('/api/papers/some-paper-id/status')
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.status).toBe(401);
    });

    it('should not allow accessing other user paper status', async () => {
      // Create paper with current user
      const createResponse = await agent
        .post('/api/search/external')
        .send({
          source: 'arxiv',
          externalId: '2401.55555',
          title: 'Private Paper',
          authors: ['Author'],
          year: 2024,
        })
        .expect(201);

      const paperId = createResponse.body.data.paperId;

      // Create another user agent
      const otherAgent = request.agent(app);
      const otherUserData = generateTestUserData();

      await otherAgent
        .post('/api/auth/register')
        .send({
          email: otherUserData.email,
          password: otherUserData.password,
          name: otherUserData.name,
        });

      await otherAgent
        .post('/api/auth/login')
        .send({
          email: otherUserData.email,
          password: otherUserData.password,
        });

      // Try to access paper status with other user
      const response = await otherAgent
        .get(`/api/papers/${paperId}/status`)
        .expect(404);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/not-found');

      // Cleanup other user
      const otherUser = await prisma.user.findUnique({
        where: { email: otherUserData.email },
      });
      if (otherUser) {
        await prisma.paper.deleteMany({ where: { userId: otherUser.id } });
        await prisma.user.deleteMany({ where: { id: otherUser.id } });
      }
    });
  });

  describe('Full External Add Flow', () => {
    it('should complete full flow: add paper, check status, verify response structure', async () => {
      // Step 1: Add external paper
      const addResponse = await agent
        .post('/api/search/external')
        .send({
          source: 'arxiv',
          externalId: '2401.44444',
          title: 'Full Flow Test Paper',
          authors: ['John Doe', 'Jane Smith'],
          year: 2024,
          abstract: 'This is a test abstract for the full flow test.',
          pdfUrl: 'https://arxiv.org/pdf/2401.44444.pdf',
        })
        .expect(201);

      expect(addResponse.body.success).toBe(true);
      expect(addResponse.body.data).toMatchObject({
        status: 'pending',
        downloadTriggered: expect.any(Boolean),
        message: expect.any(String),
      });
      expect(addResponse.body.data.paperId).toBeDefined();

      const paperId = addResponse.body.data.paperId;

      // Step 2: Check status
      const statusResponse = await agent
        .get(`/api/papers/${paperId}/status`)
        .expect(200);

      expect(statusResponse.body.success).toBe(true);
      expect(statusResponse.body.data).toMatchObject({
        paperId,
        title: 'Full Flow Test Paper',
        status: 'pending',
        progress: 10,
        errorMessage: null,
      });
      expect(statusResponse.body.data.updatedAt).toBeDefined();

      // Step 3: Verify paper exists in library
      const papersResponse = await agent
        .get('/api/papers')
        .expect(200);

      expect(papersResponse.body.success).toBe(true);
      expect(papersResponse.body.data.papers.some((p: any) => p.id === paperId)).toBe(true);
    });
  });
});
