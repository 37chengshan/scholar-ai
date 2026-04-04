/**
 * Type Definitions for API Responses
 *
 * Centralized type definitions for all API entities.
 * Matches backend Prisma schema and API response formats.
 */

/**
 * User entity
 */
export interface User {
  id: string;
  email: string;
  name: string;
  emailVerified: boolean;
  avatar?: string | null;
  roles: string[];
  createdAt?: string;
  updatedAt?: string;
}

/**
 * User settings (stored in JSONB)
 */
export interface UserSettings {
  language: 'zh' | 'en';
  defaultModel: string;
  theme: 'light' | 'dark';
}

/**
 * API Key entity
 */
export interface ApiKey {
  id: string;
  name: string;
  prefix: string; // "sk_live_abc..."
  createdAt: string;
  lastUsedAt?: string | null;
}

/**
 * Paper entity
 */
export interface Paper {
  id: string;
  title: string;
  authors: string[];
  year?: number | null;
  abstract?: string | null;
  doi?: string | null;
  arxivId?: string | null;
  status: PaperStatus;
  processingStatus?: string;
  progress?: number; // 0-100
  storageKey?: string | null;
  fileSize?: number | null;
  pageCount?: number | null;
  keywords: string[];
  venue?: string | null;
  citations?: number | null;
  createdAt: string;
  updatedAt: string;
  processingError?: string | null;
  processingStartedAt?: string | null;
  processingCompletedAt?: string | null;
}

/**
 * Paper processing status
 */
export type PaperStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'no_pdf';

/**
 * Processing task status (detailed)
 */
export type ProcessingTaskStatus =
  | 'pending'
  | 'processing_ocr'
  | 'parsing'
  | 'extracting_imrad'
  | 'generating_notes'
  | 'completed'
  | 'failed';

/**
 * Paper with processing progress
 */
export interface PaperWithProgress extends Paper {
  processingStatus: ProcessingTaskStatus | PaperStatus;
  progress: number; // 0-100
  lastUpdated: string;
}

/**
 * Upload result
 */
export interface UploadResult {
  paperId: string;
  uploadUrl?: string;
  storageKey: string;
  expiresIn?: number;
  taskId?: string;
  status?: string;
  progress?: number;
  message?: string;
}

/**
 * Session entity (Chat session)
 */
export interface Session {
  id: string;
  title?: string | null;
  createdAt: string;
  updatedAt: string;
  expiresAt?: string | null;
  lastAccessedAt?: string | null;
  messageCount?: number;
}

/**
 * Chat message entity
 */
export interface Message {
  id: string;
  sessionId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tokensUsed?: number | null;
  createdAt: string;
}

/**
 * Query parameters for papers list
 */
export interface PapersQueryParams {
  page?: number;
  limit?: number;
  search?: string;
  sortBy?: 'createdAt' | 'updatedAt' | 'title' | 'year' | 'citations';
  sortOrder?: 'asc' | 'desc';
}

/**
 * RAG query parameters
 */
export interface QueryParams {
  query: string;
  paperIds?: string[];
  topK?: number;
  queryType?: 'single' | 'cross_paper' | 'evolution';
}

/**
 * RAG query result
 */
export interface QueryResult {
  answer: string;
  sources: Array<{
    paperId: string;
    paperTitle: string;
    chunkId: string;
    content: string;
    pageNumber?: number;
    score: number;
  }>;
  tokensUsed?: number;
}

/**
 * Login response
 */
export interface LoginResponse {
  success: boolean;
  data?: {
    user: User;
  };
  error?: {
    type: string;
    title: string;
    status: number;
    detail: string;
  };
}

/**
 * Papers list response
 */
export interface PapersListResponse {
  success: boolean;
  data: {
    papers: PaperWithProgress[];
    total: number;
    page: number;
    limit: number;
    totalPages: number;
  };
}

/**
 * Dashboard stats
 */
export interface DashboardStats {
  paperCount: number;
  entityCount: number;
  llmTokens: number;
  queryCount: number;
  sessionCount: number;
  weeklyTrend: Array<{
    date: string;
    papers: number;
    queries: number;
    tokens: number;
  }>;
  subjectDistribution: Array<{
    name: string;
    value: number;
  }>;
  storageUsage: {
    vectorDB: { used: number; total: number };
    blobStorage: { used: number; total: number };
  };
}