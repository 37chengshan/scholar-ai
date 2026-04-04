/**
 * Tests for Semantic Scholar API routes.
 *
 * Tests cover:
 * - Batch operations endpoint
 * - Citations endpoint
 * - References endpoint
 * - Paper details endpoint
 * - Zod validation
 */

import request from 'supertest';
import app from '../index';

// Mock fetch globally
global.fetch = jest.fn();

describe('Semantic Scholar API Routes', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('POST /api/semantic-scholar/batch', () => {
    it('should batch get papers by IDs', async () => {
      const mockPapers = [
        { paperId: 'id1', title: 'Paper 1' },
        { paperId: 'id2', title: 'Paper 2' }
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockPapers
      });

      const response = await request(app)
        .post('/api/semantic-scholar/batch')
        .set('Authorization', 'Bearer test-token')
        .send({ ids: ['id1', 'id2'] });

      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
      expect(response.body.data).toEqual(mockPapers);
      expect(response.body.count).toBe(2);
    });

    it('should reject empty ids array', async () => {
      const response = await request(app)
        .post('/api/semantic-scholar/batch')
        .set('Authorization', 'Bearer test-token')
        .send({ ids: [] });

      expect(response.status).toBe(400);
    });

    it('should reject ids array > 1000', async () => {
      const ids = Array(1001).fill('id');

      const response = await request(app)
        .post('/api/semantic-scholar/batch')
        .set('Authorization', 'Bearer test-token')
        .send({ ids });

      expect(response.status).toBe(400);
    });
  });

  describe('GET /api/semantic-scholar/paper/:paperId/citations', () => {
    it('should return citations for a paper', async () => {
      const mockCitations = [
        { paperId: 'citing1', title: 'Citing Paper 1' },
        { paperId: 'citing2', title: 'Citing Paper 2' }
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockCitations
      });

      const response = await request(app)
        .get('/api/semantic-scholar/paper/test-id/citations')
        .set('Authorization', 'Bearer test-token');

      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
      expect(response.body.data).toEqual(mockCitations);
      expect(Array.isArray(response.body.data)).toBe(true);
    });
  });

  describe('GET /api/semantic-scholar/paper/:paperId/references', () => {
    it('should return references for a paper', async () => {
      const mockReferences = [
        { paperId: 'ref1', title: 'Reference Paper 1' },
        { paperId: 'ref2', title: 'Reference Paper 2' }
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockReferences
      });

      const response = await request(app)
        .get('/api/semantic-scholar/paper/test-id/references')
        .set('Authorization', 'Bearer test-token');

      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
      expect(response.body.data).toEqual(mockReferences);
      expect(Array.isArray(response.body.data)).toBe(true);
    });
  });

  describe('GET /api/semantic-scholar/paper/:paperId', () => {
    it('should return paper details', async () => {
      const mockPaper = {
        paperId: 'test-id',
        title: 'Test Paper',
        year: 2023,
        authors: [{ name: 'Author 1' }]
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockPaper
      });

      const response = await request(app)
        .get('/api/semantic-scholar/paper/test-id')
        .set('Authorization', 'Bearer test-token');

      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
      expect(response.body.data).toEqual(mockPaper);
    });
  });
});