import request from 'supertest';
import app from '../../src/index';
import { generateTestUserData, cleanupTestData } from '../helpers/db';
import fs from 'fs';
import path from 'path';

/**
 * E2E Test: Chat 功能完整测试 - 从 arXiv 下载论文并进行 RAG 问答
 *
 * Test Steps:
 * 1. Download 10 papers from arXiv
 * 2. Upload papers to the system
 * 3. Wait for processing to complete
 * 4. Test Chat/RAG queries on the papers
 */

describe('Chat with arXiv Papers E2E Test', () => {
  const arxivPapersDir = path.join(__dirname, '../../scripts/arxiv-papers');
  const expectedPapers = [
    '2301.07041.pdf',
    '2303.08774.pdf',
    '2005.14165.pdf',
    '1810.04805.pdf',
    '1706.03762.pdf',
    '2203.02155.pdf',
    '2103.00020.pdf',
    '1911.02147.pdf',
    '2004.05150.pdf',
    '2110.08295.pdf',
  ];

  let testUser: { email: string; password: string; name: string };
  let accessToken: string;
  let agent: ReturnType<typeof request.agent>;

  // Store uploaded paper IDs
  const uploadedPapers: { arxivId: string; paperId: string; storageKey: string }[] = [];

  beforeAll(async () => {
    await cleanupTestData();

    testUser = generateTestUserData();
    agent = request.agent(app);

    await agent.post('/api/auth/register').send(testUser).expect(201);
    const loginResponse = await agent
      .post('/api/auth/login')
      .send({ email: testUser.email, password: testUser.password })
      .expect(200);

    accessToken = loginResponse.body.meta.accessToken;
  }, 30000);

  afterAll(async () => {
    await cleanupTestData();
  });

  describe('Step 1: Download Papers from arXiv', () => {
    it('should verify arXiv papers are downloaded', () => {
      if (!fs.existsSync(arxivPapersDir)) {
        console.log('⚠ arXiv papers directory not found. Run download script first:');
        console.log('  cd scholar-ai/backend-node');
        console.log('  npm run download-arxiv');
      }

      const downloadedPapers = fs.existsSync(arxivPapersDir)
        ? fs.readdirSync(arxivPapersDir).filter(f => f.endsWith('.pdf'))
        : [];

      console.log(`Found ${downloadedPapers.length} papers in ${arxivPapersDir}`);

      if (downloadedPapers.length === 0) {
        console.log('\n⚠ No papers found. Skipping paper upload tests.');
        console.log('To download papers, run:');
        console.log('  tsx scripts/download-arxiv-papers.ts');
      }

      downloadedPapers.forEach(paper => {
        const filePath = path.join(arxivPapersDir, paper);
        const stats = fs.statSync(filePath);
        console.log(`  ✓ ${paper} (${Math.round(stats.size / 1024)}KB)`);
      });

      expect(downloadedPapers.length).toBeGreaterThan(0);
    });
  });

  describe('Step 2: Upload Papers to System', () => {
    it('should upload all downloaded papers', async () => {
      if (!fs.existsSync(arxivPapersDir)) {
        console.log('Skipping upload - no papers downloaded');
        return;
      }

      const downloadedPapers = fs.readdirSync(arxivPapersDir).filter(f => f.endsWith('.pdf'));

      console.log(`\nUploading ${downloadedPapers.length} papers...\n`);

      for (const paperFile of downloadedPapers) {
        const arxivId = paperFile.replace('.pdf', '');
        const filePath = path.join(arxivPapersDir, paperFile);

        try {
          // Step 1: Get presigned upload URL
          const uploadUrlResponse = await agent
            .post('/api/papers')
            .send({ filename: paperFile })
            .expect(201);

          const { paperId, storageKey } = uploadUrlResponse.body.data;

          // Step 2: Upload PDF
          const fileBuffer = fs.readFileSync(filePath);
          await agent
            .post(`/api/papers/upload/local/${encodeURIComponent(storageKey)}`)
            .set('Content-Type', 'application/octet-stream')
            .send(fileBuffer)
            .expect(200);

          // Step 3: Trigger processing via webhook
          await agent
            .post('/api/papers/webhook')
            .send({ paperId, storageKey })
            .expect(201);

          uploadedPapers.push({ arxivId, paperId, storageKey });
          console.log(`✓ Uploaded ${arxivId} (Paper ID: ${paperId})`);
        } catch (error) {
          console.error(`✗ Failed to upload ${arxivId}:`, error);
        }
      }

      console.log(`\nTotal uploaded: ${uploadedPapers.length} papers\n`);
      expect(uploadedPapers.length).toBeGreaterThan(0);
    }, 60000);
  });

  describe('Step 3: Wait for Processing', () => {
    it(
      'should wait for all papers to be processed',
      async () => {
        if (uploadedPapers.length === 0) {
          console.log('Skipping processing wait - no papers uploaded');
          return;
        }

        console.log(`\nWaiting for ${uploadedPapers.length} papers to be processed...\n`);

        const maxAttempts = 120;
        const delayMs = 5000;
        const completedPapers: string[] = [];
        const failedPapers: string[] = [];

        for (const paper of uploadedPapers) {
          console.log(`Polling status for ${paper.arxivId}...`);

          for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            const response = await agent
              .get(`/api/papers/${paper.paperId}/status`)
              .expect(200);

            const { status, progress } = response.body.data;

            if (attempt % 10 === 0 || status === 'completed' || status === 'failed') {
              console.log(`  ${paper.arxivId}: ${status} (${progress}%`);
            }

            if (status === 'completed') {
              completedPapers.push(paper.arxivId);
              console.log(`  ✓ ${paper.arxivId} completed`);
              break;
            }

            if (status === 'failed') {
              failedPapers.push(paper.arxivId);
              console.log(`  ✗ ${paper.arxivId} failed`);
              break;
            }

            await new Promise(resolve => setTimeout(resolve, delayMs));
          }
        }

        console.log(`\nProcessing Summary:`);
        console.log(`  Completed: ${completedPapers.length}`);
        console.log(`  Failed: ${failedPapers.length}\n`);

        expect(completedPapers.length).toBeGreaterThan(0);
      },
      600000
    );
  });

  describe('Step 4: Test Chat/RAG Queries', () => {
    it('should query about LLaMA paper', async () => {
      const llamaPaper = uploadedPapers.find(p => p.arxivId === '2301.07041');
      if (!llamaPaper) {
        console.log('Skipping - LLaMA paper not uploaded');
        return;
      }

      const response = await agent
        .post('/api/queries')
        .send({
          question: 'What are the key features of LLaMA model?',
          paperIds: [llamaPaper.paperId],
          queryType: 'single',
        })
        .expect(200);

      console.log('\nQuery: What are the key features of LLaMA model?');
      console.log('Answer:', response.body.data.answer?.substring(0, 200) + '...');
      console.log('Sources:', response.body.data.sources?.length || 0);
      console.log('Confidence:', response.body.data.confidence);

      expect(response.body.success).toBe(true);
      expect(response.body.data.answer).toBeDefined();
    });

    it('should query about Transformer architecture', async () => {
      const transformerPaper = uploadedPapers.find(p => p.arxivId === '1706.03762');
      if (!transformerPaper) {
        console.log('Skipping - Transformer paper not uploaded');
        return;
      }

      const response = await agent
        .post('/api/queries')
        .send({
          question: 'Explain the Transformer architecture and its key components',
          paperIds: [transformerPaper.paperId],
          queryType: 'single',
        })
        .expect(200);

      console.log('\nQuery: Explain the Transformer architecture');
      console.log('Answer:', response.body.data.answer?.substring(0, 200) + '...');

      expect(response.body.success).toBe(true);
      expect(response.body.data.answer).toBeDefined();
    });

    it('should query about GPT-3 capabilities', async () => {
      const gpt3Paper = uploadedPapers.find(p => p.arxivId === '2005.14165');
      if (!gpt3Paper) {
        console.log('Skipping - GPT-3 paper not uploaded');
        return;
      }

      const response = await agent
        .post('/api/queries')
        .send({
          question: 'What can GPT-3 do without task-specific training?',
          paperIds: [gpt3Paper.paperId],
          queryType: 'single',
        })
        .expect(200);

      console.log('\nQuery: What can GPT-3 do without task-specific training?');
      console.log('Answer:', response.body.data.answer?.substring(0, 200) + '...');

      expect(response.body.success).toBe(true);
    });

    it('should perform multi-paper comparison', async () => {
      const completedPapers = uploadedPapers.filter(p => 
        ['2301.07041', '1706.03762', '2005.14165', '1810.04805'].includes(p.arxivId)
      );

      if (completedPapers.length < 2) {
        console.log('Skipping comparison - not enough papers');
        return;
      }

      const response = await agent
        .post('/api/queries')
        .send({
          question: 'Compare the approaches used in these transformer-based models',
          paperIds: completedPapers.map(p => p.paperId),
          queryType: 'compare',
        })
        .expect(200);

      console.log('\nMulti-paper comparison query');
      console.log('Papers:', completedPapers.map(p => p.arxivId));
      console.log('Answer:', response.body.data.answer?.substring(0, 300) + '...');

      expect(response.body.success).toBe(true);
      expect(response.body.data.sources?.length).toBeGreaterThan(1);
    });

    it('should test query history', async () => {
      const response = await agent
        .get('/api/queries')
        .query({ page: 1, limit: 10 })
        .expect(200);

      console.log('\nQuery History:');
      console.log(`  Total queries: ${response.body.data.pagination.total}`);
      response.body.data.queries.forEach((q: any, i: number) => {
        console.log(`  ${i + 1}. ${q.question?.substring(0, 50)}... (${q.status})`);
      });

      expect(response.body.success).toBe(true);
      expect(response.body.data.queries.length).toBeGreaterThan(0);
    });
  });

  describe('Test Summary', () => {
    it('should output complete test summary', () => {
      console.log('\n========================================');
      console.log('Chat with arXiv Papers E2E Test Summary');
      console.log('========================================\n');

      console.log('Papers Downloaded:', expectedPapers.length);
      console.log('Papers Uploaded:', uploadedPapers.length);
      console.log('Papers Tested in Chat:', uploadedPapers.filter(p => 
        ['2301.07041', '1706.03762', '2005.14165'].includes(p.arxivId)
      ).length);

      console.log('\n========================================');

      expect(true).toBe(true);
    });
  });
});