export type SourceType = 'local_file' | 'arxiv' | 'pdf_url' | 'doi' | 'semantic_scholar';

export type ImportJobStatus =
  | 'created'
  | 'queued'
  | 'running'
  | 'awaiting_user_action'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface ImportJobDto {
  importJobId: string;
  knowledgeBaseId: string;
  sourceType: SourceType;
  status: ImportJobStatus;
  stage: string;
  progress: number;
  createdAt: string;
  updatedAt: string;
  startedAt?: string | null;
  completedAt: string | null;
  cancelledAt: string | null;
  retryCount?: number;
  error?: {
    code: string | null;
    message: string | null;
    detail?: Record<string, unknown> | null;
  } | null;
}

export interface UploadHistoryRecordDto {
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
}
