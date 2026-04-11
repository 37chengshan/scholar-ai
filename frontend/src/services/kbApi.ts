/**
 * Knowledge Base API Service
 *
 * Provides all KB CRUD, paper management, import, and search operations.
 *
 * Endpoints (all require authentication):
 * - CRUD: list, create, get, update, delete, batchDelete
 * - Paper Management: listPapers, addPaper, removePaper
 * - Import: uploadPdf, importFromUrl, importFromArxiv
 * - Search & Chat: search
 */
import apiClient from '@/utils/apiClient';
import { ApiResponse } from '@/utils/apiClient';

// KB Types
export interface KnowledgeBase {
  id: string;
  userId: string;
  name: string;
  description: string;
  category: string;
  paperCount: number;
  chunkCount: number;
  entityCount: number;
  embeddingModel: string;
  parseEngine: string;
  chunkStrategy: string;
  enableGraph: boolean;
  enableImrad: boolean;
  enableChartUnderstanding: boolean;
  enableMultimodalSearch: boolean;
  enableComparison: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface KBCreateData {
  name: string;
  description?: string;
  category?: string;
  embeddingModel?: string;
  parseEngine?: string;
  chunkStrategy?: string;
  enableGraph?: boolean;
  enableImrad?: boolean;
  enableChartUnderstanding?: boolean;
  enableMultimodalSearch?: boolean;
  enableComparison?: boolean;
}

export interface KBListParams {
  search?: string;
  category?: string;
  sortBy?: 'updated' | 'papers' | 'name';
  limit?: number;
  offset?: number;
}

export interface KBListResponse {
  knowledgeBases: KnowledgeBase[];
  total: number;
  limit: number;
}

export interface KBSearchResult {
  id: string;
  paperId: string;
  content: string;
  section?: string;
  page?: number;
  score: number;
}

export const kbApi = {
  // === CRUD ===

  /** List knowledge bases with filters */
  list: async (params?: KBListParams): Promise<ApiResponse<KBListResponse>> => {
    const response = await apiClient.get('/api/v1/knowledge-bases', { params });
    return response.data;
  },

  /** Create a new knowledge base */
  create: async (data: KBCreateData): Promise<ApiResponse<KnowledgeBase>> => {
    const response = await apiClient.post('/api/v1/knowledge-bases', data);
    return response.data;
  },

  /** Get knowledge base by ID */
  get: async (id: string): Promise<ApiResponse<KnowledgeBase>> => {
    const response = await apiClient.get(`/api/v1/knowledge-bases/${id}`);
    return response.data;
  },

  /** Update knowledge base */
  update: async (id: string, data: Partial<KBCreateData>): Promise<ApiResponse<KnowledgeBase>> => {
    const response = await apiClient.patch(`/api/v1/knowledge-bases/${id}`, data);
    return response.data;
  },

  /** Delete knowledge base */
  delete: async (id: string): Promise<ApiResponse<{ deleted: boolean }>> => {
    const response = await apiClient.delete(`/api/v1/knowledge-bases/${id}`);
    return response.data;
  },

  /** Batch delete knowledge bases */
  batchDelete: async (ids: string[]): Promise<ApiResponse<{ deleted: number }>> => {
    const response = await apiClient.post('/api/v1/knowledge-bases/batch-delete', { ids });
    return response.data;
  },

  // === Paper Management ===

  /** List papers in a KB */
  listPapers: async (kbId: string): Promise<ApiResponse<{ papers: any[], total: number }>> => {
    const response = await apiClient.get(`/api/v1/knowledge-bases/${kbId}/papers`);
    return response.data;
  },

  /** Add paper to KB */
  addPaper: async (kbId: string, paperId: string): Promise<ApiResponse<any>> => {
    const response = await apiClient.post(`/api/v1/knowledge-bases/${kbId}/papers`, { paperId });
    return response.data;
  },

  /** Remove paper from KB */
  removePaper: async (kbId: string, paperId: string): Promise<ApiResponse<{ removed: boolean }>> => {
    const response = await apiClient.delete(`/api/v1/knowledge-bases/${kbId}/papers/${paperId}`);
    return response.data;
  },

  // === Import ===

  /** Upload PDF to KB */
  uploadPdf: async (kbId: string, file: File): Promise<ApiResponse<{ paperId: string, taskId: string }>> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post(`/api/v1/knowledge-bases/${kbId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  /** Import from URL/DOI */
  importFromUrl: async (kbId: string, url: string): Promise<ApiResponse<{ paperId: string, taskId: string }>> => {
    const response = await apiClient.post(`/api/v1/knowledge-bases/${kbId}/import-url`, { url });
    return response.data;
  },

  /** Import from arXiv */
  importFromArxiv: async (kbId: string, arxivId: string): Promise<ApiResponse<{ paperId: string, taskId: string }>> => {
    const response = await apiClient.post(`/api/v1/knowledge-bases/${kbId}/import-arxiv`, { arxivId });
    return response.data;
  },

  // === Search & Chat ===

  /** Vector search in KB */
  search: async (kbId: string, query: string, limit?: number): Promise<ApiResponse<{ results: KBSearchResult[], total: number }>> => {
    const response = await apiClient.post(`/api/v1/knowledge-bases/${kbId}/search`, { query, limit });
    return response.data;
  },
};

export default kbApi;