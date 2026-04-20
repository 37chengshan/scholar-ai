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
import {
  createKnowledgeBaseApi,
} from '@scholar-ai/sdk';
import type {
  KnowledgeBaseDto,
  KnowledgeBaseCreateDto,
  KnowledgeBaseListParams,
  KnowledgeBaseListResponse,
  KnowledgeBaseSearchHitDto,
  KnowledgeBasePaperDto,
  StorageStatsDto,
} from '@scholar-ai/types';
import { sdkHttpClient } from './sdkHttpClient';
import { importApi } from './importApi';

// Export importApi for ImportJob operations
export { importApi } from './importApi';
export type { ImportJob, SourceType, SourceResolution } from './importApi';

const kbSdk = createKnowledgeBaseApi(sdkHttpClient);

export type KnowledgeBase = KnowledgeBaseDto;
export type KBCreateData = KnowledgeBaseCreateDto;
export type KBListParams = KnowledgeBaseListParams;
export type KBListResponse = KnowledgeBaseListResponse;
export type KBSearchResult = KnowledgeBaseSearchHitDto;
export type KBPaperListItem = KnowledgeBasePaperDto;

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

export interface KBLegacyImportResponse {
  importJobId: string;
  paperId?: string | null;
  taskId: string;
  status: string;
  message: string;
}

export type KBStorageStats = StorageStatsDto;

export const kbApi = {
  // === CRUD ===

  /** List knowledge bases with filters */
  list: async (params?: KBListParams): Promise<KBListResponse> => {
    return kbSdk.list(params);
  },

  /** Create a new knowledge base */
  create: async (data: KBCreateData): Promise<KnowledgeBase> => {
    return kbSdk.create(data);
  },

  /** Get knowledge base by ID */
  get: async (id: string): Promise<KnowledgeBase> => {
    return kbSdk.get(id);
  },

  /** Update knowledge base */
  update: async (id: string, data: Partial<KBCreateData>): Promise<KnowledgeBase> => {
    return kbSdk.update(id, data);
  },

  /** Delete knowledge base */
  delete: async (id: string): Promise<{ deleted: boolean }> => {
    return kbSdk.delete(id);
  },

  /** Batch delete knowledge bases */
  batchDelete: async (ids: string[]): Promise<{ deleted: number }> => {
    const response = await apiClient.post('/api/v1/knowledge-bases/batch-delete', { ids });
    return response.data as { deleted: number };
  },

  // === Paper Management ===

  /** List papers in a KB */
  listPapers: async (kbId: string): Promise<{ papers: KBPaperListItem[]; total: number; limit: number; offset: number }> => {
    return kbSdk.listPapers(kbId);
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
  uploadPdf: async (kbId: string, file: File): Promise<KBLegacyImportResponse> => {
    const created = await importApi.create(kbId, {
      sourceType: 'local_file',
      payload: { filename: file.name },
    });
    if (!created.success || !created.data) {
      throw new Error('Failed to create import job');
    }

    const importJobId = created.data.importJobId;
    await importApi.uploadFile(importJobId, file);

    return {
      importJobId,
      paperId: null,
      taskId: importJobId,
      status: 'queued',
      message: 'Import job created and queued',
    };
  },

  /** Import from URL/DOI */
  importFromUrl: async (kbId: string, url: string): Promise<KBLegacyImportResponse> => {
    const created = await importApi.create(kbId, {
      sourceType: 'pdf_url',
      payload: { input: url },
    });
    if (!created.success || !created.data) {
      throw new Error('Failed to create URL import job');
    }

    return {
      importJobId: created.data.importJobId,
      paperId: null,
      taskId: created.data.importJobId,
      status: created.data.status,
      message: 'Import job queued',
    };
  },

  /** Import from arXiv */
  importFromArxiv: async (kbId: string, arxivId: string): Promise<KBLegacyImportResponse> => {
    const created = await importApi.create(kbId, {
      sourceType: 'arxiv',
      payload: { input: arxivId },
    });
    if (!created.success || !created.data) {
      throw new Error('Failed to create arXiv import job');
    }

    return {
      importJobId: created.data.importJobId,
      paperId: null,
      taskId: created.data.importJobId,
      status: created.data.status,
      message: 'Import job queued',
    };
  },

  // === Search & Query ===

  /** Vector search in KB - returns top-K chunks matching query */
  search: async (kbId: string, query: string, topK?: number): Promise<{ results: KBSearchResult[], total: number }> => {
    const result = await kbSdk.search(kbId, query, topK);
    return result;
  },

  /** Query KB for Q&A - returns answer with citations */
  query: async (kbId: string, query: string, topK?: number): Promise<{ answer: string, citations?: any[], sources?: any[], confidence: number }> => {
    const response = await apiClient.post(`/api/v1/knowledge-bases/${kbId}/query`, { query, topK });
    return response.data as { answer: string, citations?: any[], sources?: any[], confidence: number };
  },

  // === Storage Stats ===

  /** Get storage statistics for user's knowledge bases */
  getStorageStats: async (): Promise<KBStorageStats> => {
    return kbSdk.getStorageStats();
  },
};

export default kbApi;
