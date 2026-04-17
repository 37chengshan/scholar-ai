/**
 * Import Job API Service
 *
 * Provides ImportJob CRUD, source resolution, retry, cancel operations.
 * Wave 4: Core ImportJob API methods
 * Wave 5: Added submitDedupeDecision and SSE streaming
 *
 * Endpoints:
 * - Create: POST /api/v1/knowledge-bases/{kbId}/imports
 * - Upload File: PUT /api/v1/import-jobs/{jobId}/file
 * - Get: GET /api/v1/import-jobs/{jobId}
 * - List: GET /api/v1/import-jobs?knowledgeBaseId={kbId}
 * - Resolve: POST /api/v1/imports/sources/resolve
 * - Resolve Batch: POST /api/v1/imports/sources/resolve-batch
 * - Batch Import: POST /api/v1/knowledge-bases/{kbId}/imports/batch
 * - Retry: POST /api/v1/import-jobs/{jobId}/retry
 * - Cancel: POST /api/v1/import-jobs/{jobId}/cancel
 * - Dedupe Decision: POST /api/v1/import-jobs/{jobId}/dedupe-decision (Wave 5)
 * - SSE Stream: GET /api/v1/import-jobs/{jobId}/stream (Wave 5)
 */
import apiClient from '@/utils/apiClient';
import { ApiResponse } from '@/utils/apiClient';
import {
  createImportApi,
} from '@scholar-ai/sdk';
import type {
  ImportJobDto,
  ImportJobStatus as SharedImportJobStatus,
  SourceType as SharedSourceType,
} from '@scholar-ai/types';
import { sdkHttpClient } from './sdkHttpClient';

// === Types ===

export type SourceType = SharedSourceType;

export type ImportJobStatus = SharedImportJobStatus;

export interface ImportJobSource {
  rawInput: string;
  normalizedRef?: string | null;
  externalIds: Record<string, string>;
}

export interface ImportJobPreview {
  title: string | null;
  authors: string[];
  year: number | null;
  venue: string | null;
}

export interface ImportJobDedupe {
  status: 'unchecked' | 'checking' | 'hit' | 'resolved' | 'awaiting_decision';
  matchedPaperId: string | null;
  matchType: string | null;
  decision: string | null;
}

export interface ImportJobFile {
  storageKey: string | null;
  sha256: string | null;
  sizeBytes: number | null;
}

export interface ImportJobError {
  code: string | null;
  message: string | null;
  detail?: Record<string, unknown> | null;
}

export interface ImportJobPaper {
  paperId: string | null;
  title: string | null;
}

export interface ImportJobTask {
  processingTaskId: string | null;
  status: string | null;
  checkpointStage?: string | null;
}

export interface ImportJob {
  importJobId: string;
  knowledgeBaseId: string;
  sourceType: SourceType;
  status: ImportJobStatus;
  stage: string;
  progress: number;
  nextAction: Record<string, unknown> | null;
  retryCount?: number;
  version?: string | null;
  externalIds?: Record<string, string>;
  createdAt: string;
  updatedAt: string;
  startedAt?: string | null;
  completedAt: string | null;
  cancelledAt: string | null;
  source: ImportJobSource;
  preview: ImportJobPreview;
  dedupe: ImportJobDedupe;
  file: ImportJobFile;
  paper: ImportJobPaper | null;
  task: ImportJobTask | null;
  error: ImportJobError | null;
  actions?: { type: string; enabled: boolean }[];
}

const importSdk = createImportApi(sdkHttpClient);

function toImportJob(dto: ImportJobDto): ImportJob {
  const raw = dto as ImportJobDto & Record<string, unknown>;
  const source = (raw.source ?? {}) as Record<string, unknown>;
  const preview = (raw.preview ?? {}) as Record<string, unknown>;
  const dedupe = (raw.dedupe ?? {}) as Record<string, unknown>;
  const file = (raw.file ?? {}) as Record<string, unknown>;
  const paper = (raw.paper ?? null) as Record<string, unknown> | null;
  const task = (raw.task ?? null) as Record<string, unknown> | null;

  return {
    importJobId: dto.importJobId,
    knowledgeBaseId: dto.knowledgeBaseId,
    sourceType: dto.sourceType,
    status: dto.status,
    stage: dto.stage,
    progress: dto.progress ?? 0,
    nextAction: (raw.nextAction as Record<string, unknown> | null) ?? null,
    retryCount: dto.retryCount,
    version: (raw.version as string | null) ?? null,
    externalIds: (raw.externalIds as Record<string, string> | undefined) ?? undefined,
    createdAt: dto.createdAt,
    updatedAt: dto.updatedAt,
    startedAt: dto.startedAt ?? null,
    completedAt: dto.completedAt,
    cancelledAt: dto.cancelledAt,
    source: {
      rawInput: (source.rawInput as string) ?? '',
      normalizedRef: (source.normalizedRef as string | null) ?? null,
      externalIds: (source.externalIds as Record<string, string>) ?? {},
    },
    preview: {
      title: (preview.title as string | null) ?? null,
      authors: (preview.authors as string[]) ?? [],
      year: (preview.year as number | null) ?? null,
      venue: (preview.venue as string | null) ?? null,
    },
    dedupe: {
      status: (dedupe.status as ImportJobDedupe['status']) ?? 'unchecked',
      matchedPaperId: (dedupe.matchedPaperId as string | null) ?? null,
      matchType: (dedupe.matchType as string | null) ?? null,
      decision: (dedupe.decision as string | null) ?? null,
    },
    file: {
      storageKey: (file.storageKey as string | null) ?? null,
      sha256: (file.sha256 as string | null) ?? null,
      sizeBytes: (file.sizeBytes as number | null) ?? null,
    },
    paper: paper
      ? {
          paperId: (paper.paperId as string | null) ?? null,
          title: (paper.title as string | null) ?? null,
        }
      : null,
    task: task
      ? {
          processingTaskId: (task.processingTaskId as string | null) ?? null,
          status: (task.status as string | null) ?? null,
          checkpointStage: (task.checkpointStage as string | null) ?? null,
        }
      : null,
    error: dto.error
      ? {
          code: dto.error.code,
          message: dto.error.message,
          detail: dto.error.detail ?? null,
        }
      : null,
    actions: [],
  };
}

export interface CreateImportRequest {
  sourceType: SourceType;
  payload: Record<string, unknown>;
  options?: {
    dedupePolicy?: 'prompt' | 'reuse' | 'force';
    autoAttachToKb?: boolean;
    versionPolicy?: 'latest_if_unspecified' | 'specific';
    parsePriority?: 'normal' | 'high' | 'low';
  };
}

export interface SourceResolution {
  resolved: boolean;
  errorCode?: string;
  errorMessage?: string;
  normalizedSource?: {
    sourceType: SourceType;
    canonicalId: string;
    version?: string | null;
    externalIds?: Record<string, string>;
    canonicalAbsUrl?: string;
    canonicalPdfUrl?: string;
  };
  preview?: {
    title: string;
    authors: string[];
    year: number | null;
    abstract?: string;
    venue?: string;
    pdfAvailable: boolean;
    pdfSource?: string;
    citationCount?: number;
  };
  availability?: {
    pdfAvailable: boolean;
    pdfSource?: string;
  };
}

export interface BatchResolutionItem {
  input: string;
  resolved: boolean;
  sourceType?: SourceType;
  errorCode?: string;
  errorMessage?: string;
  normalized?: SourceResolution['normalizedSource'];
  preview?: SourceResolution['preview'];
}

// Wave 5: Dedupe decision types
export type DedupeDecisionType = 'reuse_existing' | 'import_as_new_version' | 'force_new_paper' | 'cancel';

export interface DedupeDecisionRequest {
  decision: DedupeDecisionType;
  matchedPaperId?: string;
}

export interface BatchFileUploadItem {
  importJobId: string;
  filename: string;
  file: File;
}

export interface BatchImportItemResponse {
  importJobId: string;
  sourceType: SourceType;
  status: string;
  nextAction: Record<string, unknown> | null;
}

// === API Methods ===

export const importApi = {
  /**
   * Create a single import job
   */
  create: async (
    kbId: string,
    request: CreateImportRequest
  ): Promise<ApiResponse<ImportJob>> => {
    const data = await importSdk.create(kbId, request);
    return { success: true, data: toImportJob(data) };
  },

  /**
   * Upload file to import job (for local_file type)
   */
  uploadFile: async (
    jobId: string,
    file: File
  ): Promise<ApiResponse<{ storageKey: string; sha256: string; sizeBytes: number; importJobId: string; status: string; stage: string }>> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.put(
      `/api/v1/import-jobs/${jobId}/file`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' }
      }
    );
    return { success: true, data: response.data };
  },

  /**
   * Get single import job status
   */
  get: async (jobId: string): Promise<ApiResponse<ImportJob>> => {
    const data = await importSdk.get(jobId);
    return { success: true, data: toImportJob(data) };
  },

  /**
   * List import jobs for a KB
   */
  list: async (
    kbId: string,
    params?: { status?: ImportJobStatus; limit?: number; offset?: number }
  ): Promise<ApiResponse<{ jobs: ImportJob[]; total: number; limit: number; offset: number }>> => {
    const data = await importSdk.list(kbId, params);
    return {
      success: true,
      data: {
        jobs: data.jobs.map(toImportJob),
        total: data.total,
        limit: data.limit,
        offset: data.offset,
      },
    };
  },

  /**
   * Resolve source (preview before import)
   */
  resolve: async (
    sourceType: SourceType,
    input: string
  ): Promise<ApiResponse<SourceResolution>> => {
    const response = await apiClient.post(`/api/v1/imports/sources/resolve`, {
      sourceType,
      input
    });
    return { success: true, data: response.data };
  },

  /**
   * Batch resolve multiple sources
   */
  resolveBatch: async (
    items: string[]
  ): Promise<ApiResponse<{ items: BatchResolutionItem[] }>> => {
    const response = await apiClient.post(`/api/v1/imports/sources/resolve-batch`, {
      items
    });
    return { success: true, data: response.data };
  },

  /**
   * Create batch import jobs
   */
  createBatch: async (
    kbId: string,
    items: CreateImportRequest[]
  ): Promise<ApiResponse<{ batchJobId: string; status: string; totalItems: number; items: BatchImportItemResponse[] }>> => {
    const response = await apiClient.post(
      `/api/v1/knowledge-bases/${kbId}/imports/batch`,
      { items }
    );
    return { success: true, data: response.data };
  },

  /**
   * Upload local files for a batch import job using manifest mapping.
   */
  uploadBatchFiles: async (
    batchJobId: string,
    items: BatchFileUploadItem[]
  ): Promise<
    ApiResponse<{
      batchJobId: string;
      totalItems: number;
      acceptedCount: number;
      rejectedCount: number;
      accepted: Array<{ importJobId: string; filename: string; status: string }>;
      rejected: Array<{ importJobId: string; filename: string; reason: string }>;
    }>
  > => {
    const formData = new FormData();
    formData.append(
      'manifest',
      JSON.stringify(
        items.map((item) => ({
          importJobId: item.importJobId,
          filename: item.filename,
        }))
      )
    );

    for (const item of items) {
      formData.append('files', item.file, item.filename);
    }

    const response = await apiClient.post(
      `/api/v1/import-batches/${batchJobId}/files`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );
    return { success: true, data: response.data };
  },

  /**
   * Retry failed job
   */
  retry: async (
    jobId: string,
    options?: { retryFromStage?: string }
  ): Promise<ApiResponse<ImportJob>> => {
    const data = await importSdk.retry(jobId, options);
    return { success: true, data: toImportJob(data) };
  },

  /**
   * Cancel running job
   */
  cancel: async (
    jobId: string
  ): Promise<ApiResponse<{ importJobId: string; status: 'cancelled' }>> => {
    const data = await importSdk.cancel(jobId);
    return { success: true, data };
  },

  /**
   * Submit dedupe decision (Wave 5)
   * Per gpt意见.md Section 2.5: 4 decision options
   */
  submitDedupeDecision: async (
    jobId: string,
    request: DedupeDecisionRequest
  ): Promise<ApiResponse<{ importJobId: string; status: string }>> => {
    const response = await apiClient.post(
      `/api/v1/import-jobs/${jobId}/dedupe-decision`,
      request
    );
    return { success: true, data: response.data };
  },

  /**
   * SSE stream for progress updates (Wave 5)
   * Returns EventSource URL for real-time updates
   */
  getStreamUrl: (jobId: string): string => {
    return `/api/v1/import-jobs/${jobId}/stream`;
  },
};

export default importApi;