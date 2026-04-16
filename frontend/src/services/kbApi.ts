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

// Export importApi for ImportJob operations
export { importApi } from './importApi';
export type { ImportJob, SourceType, SourceResolution } from './importApi';

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
  paperTitle?: string | null;
  content: string;
  section?: string;
  page?: number;
  score: number;
}

export interface KBPaperListItem {
  id: string;
  title: string;
  authors: string[];
  year?: number | null;
  venue?: string | null;
  status: 'pending' | 'processing' | 'completed' | 'failed' | string;
  chunkCount: number;
  entityCount: number;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface KBUploadHistoryRecord {
  id: string;
  userId: string;
  paperId?: string | null;
  filename: string;
  status: 'PROCESSING' | 'COMPLETED' | 'FAILED' | string;
  chunksCount?: number | null;
  llmTokens?: number | null;
  pageCount?: number | null;
  imageCount?: number | null;
  tableCount?: number | null;
  errorMessage?: string | null;
  processingTime?: number | null;
  createdAt: string;
  updatedAt?: string | null;
  completedAt?: string | null;
  processingStatus?: string;
  progress?: number;
  paper?: {
    id: string;
    title: string;
    filename: string;
  } | null;
}

export interface KBStorageStats {
  kbCount: number;
  paperCount: number;
  chunkCount: number;
  estimatedStorageMB: number;
  storageLimitMB: number;
}

export const kbApi = {
  // === CRUD ===

  /** List knowledge bases with filters */
  list: async (params?: KBListParams): Promise<KBListResponse> => {
    const response = await apiClient.get('/api/v1/knowledge-bases', { params });
    return response.data as KBListResponse;
  },

  /** Create a new knowledge base */
  create: async (data: KBCreateData): Promise<KnowledgeBase> => {
    const response = await apiClient.post('/api/v1/knowledge-bases', data);
    return response.data as KnowledgeBase;
  },

  /** Get knowledge base by ID */
  get: async (id: string): Promise<KnowledgeBase> => {
    const response = await apiClient.get(`/api/v1/knowledge-bases/${id}`);
    return response.data as KnowledgeBase;
  },

  /** Update knowledge base */
  update: async (id: string, data: Partial<KBCreateData>): Promise<KnowledgeBase> => {
    const response = await apiClient.patch(`/api/v1/knowledge-bases/${id}`, data);
    return response.data as KnowledgeBase;
  },

  /** Delete knowledge base */
  delete: async (id: string): Promise<{ deleted: boolean }> => {
    const response = await apiClient.delete(`/api/v1/knowledge-bases/${id}`);
    return response.data as { deleted: boolean };
  },

  /** Batch delete knowledge bases */
  batchDelete: async (ids: string[]): Promise<{ deleted: number }> => {
    const response = await apiClient.post('/api/v1/knowledge-bases/batch-delete', { ids });
    return response.data as { deleted: number };
  },

  // === Paper Management ===

  /** List papers in a KB */
  listPapers: async (kbId: string): Promise<{ papers: KBPaperListItem[]; total: number; limit: number; offset: number }> => {
    const response = await apiClient.get(`/api/v1/knowledge-bases/${kbId}/papers`);
    return response.data as { papers: KBPaperListItem[]; total: number; limit: number; offset: number };
  },

  /** List upload history for a KB */
  getUploadHistory: async (
    kbId: string,
    params?: { limit?: number; offset?: number }
  ): Promise<{ records: KBUploadHistoryRecord[]; total: number; limit: number; offset: number }> => {
    const response = await apiClient.get(`/api/v1/knowledge-bases/${kbId}/upload-history`, {
      params,
    });
    return response.data as { records: KBUploadHistoryRecord[]; total: number; limit: number; offset: number };
  },

  /** Add paper to KB */
  addPaper: async (kbId: string, paperId: string): Promise<any> => {
    const response = await apiClient.post(`/api/v1/knowledge-bases/${kbId}/papers`, { paperId });
    return response.data;
  },

  /** Remove paper from KB */
  removePaper: async (kbId: string, paperId: string): Promise<{ removed: boolean }> => {
    const response = await apiClient.delete(`/api/v1/knowledge-bases/${kbId}/papers/${paperId}`);
    return response.data as { removed: boolean };
  },

  // === Import ===

  /** Upload PDF to KB */
  uploadPdf: async (kbId: string, file: File): Promise<{ paperId: string, taskId: string, status: string, message: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post(`/api/v1/knowledge-bases/${kbId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    const data = response.data as {
      paperId: string;
      taskId: string;
      status: string;
      message: string;
    };
    return data;
  },

  /** Import from URL/DOI */
  importFromUrl: async (kbId: string, url: string): Promise<{ paperId: string, taskId: string }> => {
    const response = await apiClient.post(`/api/v1/knowledge-bases/${kbId}/import-url`, { url });
    return response.data as { paperId: string, taskId: string };
  },

  /** Import from arXiv */
  importFromArxiv: async (kbId: string, arxivId: string): Promise<{ paperId: string, taskId: string }> => {
    const response = await apiClient.post(`/api/v1/knowledge-bases/${kbId}/import-arxiv`, { arxivId });
    return response.data as { paperId: string, taskId: string };
  },

  // === Search & Query ===

  /** Vector search in KB - returns top-K chunks matching query */
  search: async (kbId: string, query: string, topK?: number): Promise<{ results: KBSearchResult[], total: number }> => {
    const response = await apiClient.post(`/api/v1/knowledge-bases/${kbId}/search`, { query, topK });
    return response.data as { results: KBSearchResult[], total: number };
  },

  /** Query KB for Q&A - returns answer with citations */
  query: async (kbId: string, query: string, topK?: number): Promise<{ answer: string, citations?: any[], sources?: any[], confidence: number }> => {
    const response = await apiClient.post(`/api/v1/knowledge-bases/${kbId}/query`, { query, topK });
    return response.data as { answer: string, citations?: any[], sources?: any[], confidence: number };
  },

  // === Storage Stats ===

  /** Get storage statistics for user's knowledge bases */
  getStorageStats: async (): Promise<KBStorageStats> => {
    const response = await apiClient.get('/api/v1/knowledge-bases/storage-stats');
    return response.data as KBStorageStats;
  },
};

export default kbApi;
