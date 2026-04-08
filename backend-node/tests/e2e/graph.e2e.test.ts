/**
 * E2E tests for Graph API endpoints
 *
 * Tests:
 * - /api/graph/nodes endpoint
 * - /api/graph/neighbors/{id} endpoint
 * - /api/graph/pagerank endpoint
 * - /api/entities/extract endpoint
 */

import request from 'supertest';
import app from '../../src/index';
import { createAuthenticatedUser } from '../helpers/server';

describe('Graph API E2E', () => {
  let agent: any;

  beforeAll(async () => {
    const { agent: authAgent } = await createAuthenticatedUser();
    agent = authAgent;
  });
  describe('GET /api/graph/nodes', () => {
    it('should return nodes with G6-compatible format', async () => {
      const response = await agent
        .get('/api/graph/nodes?limit=10')
        .expect(200);

      expect(response.body).toHaveProperty('nodes');
      expect(response.body).toHaveProperty('edges');
      expect(Array.isArray(response.body.nodes)).toBe(true);
      expect(Array.isArray(response.body.edges)).toBe(true);

      // Verify node structure
      if (response.body.nodes.length > 0) {
        const node = response.body.nodes[0];
        expect(node).toHaveProperty('id');
        expect(node).toHaveProperty('name');
        expect(node).toHaveProperty('type');
        expect(['Paper', 'Method', 'Dataset', 'Metric', 'Venue', 'Author']).toContain(node.type);
      }
    });

    it('should filter by node type', async () => {
      const response = await agent
        .get('/api/graph/nodes?node_type=Paper&limit=5')
        .expect(200);

      expect(response.body.nodes.every((n: any) => n.type === 'Paper')).toBe(true);
    });

    it('should filter by min_pagerank', async () => {
      const response = await agent
        .get('/api/graph/nodes?min_pagerank=0.01&limit=10')
        .expect(200);

      // All papers should have pagerank >= 0.01
      const papers = response.body.nodes.filter((n: any) => n.type === 'Paper');
      for (const paper of papers) {
        expect(paper.pagerank).toBeGreaterThanOrEqual(0.01);
      }
    });
  });

  describe('GET /api/graph/pagerank', () => {
    it('should return top papers by PageRank', async () => {
      const response = await agent
        .get('/api/graph/pagerank?limit=5')
        .expect(200);

      expect(response.body).toHaveProperty('papers');
      expect(response.body).toHaveProperty('total');
      expect(Array.isArray(response.body.papers)).toBe(true);
      expect(response.body.papers.length).toBeLessThanOrEqual(5);

      // Verify paper structure
      if (response.body.papers.length > 0) {
        const paper = response.body.papers[0];
        expect(paper).toHaveProperty('paperId');
        expect(paper).toHaveProperty('title');
        expect(paper).toHaveProperty('score');
        expect(typeof paper.score).toBe('number');
      }
    });

    it('should support year filtering', async () => {
      const response = await agent
        .get('/api/graph/pagerank?limit=10&min_year=2020&max_year=2024')
        .expect(200);

      for (const paper of response.body.papers) {
        expect(paper.year).toBeGreaterThanOrEqual(2020);
        expect(paper.year).toBeLessThanOrEqual(2024);
      }
    });
  });

  describe('GET /api/graph/neighbors/:id', () => {
    it('should return neighbors of a node', async () => {
      // First get a paper node
      const nodesResponse = await agent
        .get('/api/graph/nodes?node_type=Paper&limit=1');

      if (nodesResponse.body.nodes.length === 0) {
        console.log('Skipping neighbors test - no papers in graph');
        return;
      }

      const paperId = nodesResponse.body.nodes[0].id;

      const response = await agent
        .get(`/api/graph/neighbors/${paperId}?limit=10`)
        .expect(200);

      expect(response.body).toHaveProperty('nodes');
      expect(response.body).toHaveProperty('edges');
    });

    it('should return 404 for non-existent node', async () => {
      await agent
        .get('/api/graph/neighbors/non-existent-id-12345')
        .expect(404);
    });
  });

  describe('POST /api/entities/extract', () => {
    it('should extract entities from text', async () => {
      // This test calls actual LLM service, may take longer
      const response = await agent
        .post('/api/entities/extract')
        .send({
          text: 'We use the Transformer architecture trained on ImageNet dataset. Achieved 95% accuracy.'
        })
        .expect(200);

      expect(response.body).toHaveProperty('methods');
      expect(response.body).toHaveProperty('datasets');
      expect(response.body).toHaveProperty('metrics');
      expect(response.body).toHaveProperty('total_count');
      expect(typeof response.body.total_count).toBe('number');
    }, 60000); // 60 second timeout for LLM call

    it('should validate text length', async () => {
      await agent
        .post('/api/entities/extract')
        .send({ text: 'Short' })
        .expect(422);
    });
  });

  describe('Integration: Extraction to Graph', () => {
    it('should extract and build graph for a paper', async () => {
      // This is an async test that requires actual LLM and Neo4j
      // Skip if not in proper environment
      if (!process.env.RUN_INTEGRATION_TESTS) {
        console.log('Skipping integration test');
        return;
      }

      const paperId = `test-paper-${Date.now()}`;

      // 1. Extract entities
      const extractResponse = await agent
        .post('/api/entities/extract')
        .send({
          text: 'Vision Transformer (ViT) model trained on ImageNet-1K dataset. Evaluated on COCO dataset using mAP metric.'
        });

      expect(extractResponse.status).toBe(200);
      const entities = extractResponse.body;

      // 2. Build graph
      const buildResponse = await agent
        .post(`/api/entities/${paperId}/build`)
        .send({
          paper_text: 'Vision Transformer (ViT) model trained on ImageNet-1K dataset.',
          authors: ['Test Author'],
          references: []
        });

      expect(buildResponse.status).toBe(200);
      expect(buildResponse.body.status).toBe('success');

      // 3. Verify graph
      const statusResponse = await agent
        .get(`/api/entities/${paperId}/status`);

      if (statusResponse.status === 200) {
        expect(statusResponse.body.has_entities).toBe(true);
      }
    });
  });
});
