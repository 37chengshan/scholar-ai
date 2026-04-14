/**
 * Type Definitions for API Responses
 *
 * Centralized type definitions for all API entities.
 * Matches backend Prisma schema and API response formats.
 */

// Import types from sibling modules for local use
import type {
  AgentPhase,
  StreamStatus,
  ToolTimelineItem,
  CitationItem,
} from './chat';

// SSE Event Types
export * from './sse';

// Chat Types (re-export for external modules)
export * from './chat';

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
  fontSize?: 'small' | 'medium' | 'large' | 'extra-large';
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
  starred?: boolean; // Requires Plan 15-01 backend endpoint
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
 *
 * Phase 5.1: Extended with thinking-related fields for Agent-Native Chat.
 * Per implementation plan v3 Section 3.1 ChatStreamState.
 * All new fields are optional for backward compatibility.
 */
export interface Message {
  id: string;
  sessionId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tokensUsed?: number | null;
  createdAt: string;

  // === Phase 5.1: Thinking-related fields ===

  /** Reasoning process content for Think block display */
  reasoningBuffer?: string;

  /** Current agent processing phase */
  currentPhase?: AgentPhase;

  /** Human-readable phase label for UI */
  phaseLabel?: string;

  /** Tool call timeline for real-time tracking */
  toolTimeline?: ToolTimelineItem[];

  /** Citations/references for this message */
  citations?: CitationItem[];

  /** Stream status state machine (HARD RULE 0.3) */
  streamStatus?: StreamStatus;

  /** Cost in currency units */
  cost?: number;

  /** Processing duration in milliseconds */
  duration?: number;

  /** Error info if streamStatus is 'error' */
  error?: { code: string; message: string };

  /** Timestamp when streaming started */
  startedAt?: number;

  /** Timestamp when streaming ended */
  endedAt?: number;
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
  starred?: boolean;
  readStatus?: 'unread' | 'in-progress' | 'completed';
  dateFrom?: string;
  dateTo?: string;
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