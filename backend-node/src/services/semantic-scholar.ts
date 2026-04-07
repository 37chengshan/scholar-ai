/**
 * Semantic Scholar API service - proxies to Python AI service.
 *
 * Per D-05: Node.js routes proxy to Python backend.
 */

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';

export class SemanticScholarService {
  /**
   * Batch get papers by IDs.
   * Per D-01: Max 1000 IDs.
   */
  async batchGetPapers(ids: string[], fields?: string): Promise<any[]> {
    const params = new URLSearchParams();
    if (fields) params.append('fields', fields);

    const response = await fetch(`${AI_SERVICE_URL}/semantic-scholar/batch?${params}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids })
    });

    if (!response.ok) {
      throw new Error(`Semantic Scholar batch failed: ${response.status}`);
    }

    return response.json() as Promise<any[]>;
  }

  /**
   * Get paper citations.
   * Per D-02: Returns citing papers.
   */
  async getCitations(paperId: string, fields?: string, limit?: number): Promise<any[]> {
    const params = new URLSearchParams();
    if (fields) params.append('fields', fields);
    if (limit) params.append('limit', String(limit));

    const response = await fetch(
      `${AI_SERVICE_URL}/semantic-scholar/paper/${paperId}/citations?${params}`
    );

    if (!response.ok) {
      throw new Error(`Get citations failed: ${response.status}`);
    }

    return response.json() as Promise<any[]>;
  }

  /**
   * Get paper references.
   * Per D-02: Returns referenced papers.
   */
  async getReferences(paperId: string, fields?: string, limit?: number): Promise<any[]> {
    const params = new URLSearchParams();
    if (fields) params.append('fields', fields);
    if (limit) params.append('limit', String(limit));

    const response = await fetch(
      `${AI_SERVICE_URL}/semantic-scholar/paper/${paperId}/references?${params}`
    );

    if (!response.ok) {
      throw new Error(`Get references failed: ${response.status}`);
    }

    return response.json() as Promise<any[]>;
  }

  /**
   * Get paper details.
   */
  async getPaperDetails(paperId: string, fields?: string): Promise<any> {
    const params = new URLSearchParams();
    if (fields) params.append('fields', fields);

    const response = await fetch(
      `${AI_SERVICE_URL}/semantic-scholar/paper/${paperId}?${params}`
    );

    if (!response.ok) {
      throw new Error(`Get paper details failed: ${response.status}`);
    }

    return response.json() as Promise<any[]>;
  }
}

export const semanticScholarService = new SemanticScholarService();