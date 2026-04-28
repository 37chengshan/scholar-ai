/**
 * Papers API Service
 *
 * Normalizes backend paper payloads so pages can consistently use camelCase.
 */

import apiClient from '@/utils/apiClient';
import type {
  PapersListResponse,
  Paper,
  PaperWithProgress,
  PapersQueryParams,
  ProcessingTaskStatus,
} from '@/types';
import type { ReadingCardDoc } from '@/features/read/readingCard';

interface RawPaper {
  id: string;
  title: string;
  authors: string[];
  year?: number | null;
  abstract?: string | null;
  doi?: string | null;
  arxiv_id?: string | null;
  arxivId?: string | null;
  status: string;
  processingStatus?: string;
  progress?: number;
  storage_key?: string | null;
  storageKey?: string | null;
  file_size?: number | null;
  fileSize?: number | null;
  page_count?: number | null;
  pageCount?: number | null;
  keywords?: string[];
  venue?: string | null;
  citations?: number | null;
  starred?: boolean;
  created_at?: string;
  createdAt?: string;
  updated_at?: string;
  updatedAt?: string;
  processingError?: string | null;
  reading_notes?: string | null;
  readingNotes?: string | null;
  reading_card_doc?: ReadingCardDoc | null;
  readingCardDoc?: ReadingCardDoc | null;
  imrad_json?: unknown;
  imradJson?: unknown;
  knowledge_base_id?: string | null;
  knowledgeBaseId?: string | null;
}

function normalizePaper(raw: RawPaper): PaperWithProgress {
  return {
    id: raw.id,
    title: raw.title,
    authors: raw.authors ?? [],
    year: raw.year ?? null,
    abstract: raw.abstract ?? null,
    doi: raw.doi ?? null,
    arxivId: raw.arxivId ?? raw.arxiv_id ?? null,
    status: raw.status as Paper['status'],
    processingStatus: raw.processingStatus,
    progress: raw.progress ?? 0,
    storageKey: raw.storageKey ?? raw.storage_key ?? null,
    fileSize: raw.fileSize ?? raw.file_size ?? null,
    pageCount: raw.pageCount ?? raw.page_count ?? null,
    keywords: raw.keywords ?? [],
    venue: raw.venue ?? null,
    citations: raw.citations ?? null,
    starred: raw.starred ?? false,
    createdAt: raw.createdAt ?? raw.created_at ?? '',
    updatedAt: raw.updatedAt ?? raw.updated_at ?? '',
    processingError: raw.processingError ?? null,
    lastUpdated: raw.updatedAt ?? raw.updated_at ?? '',
    readingNotes: raw.readingNotes ?? raw.reading_notes ?? null,
    readingCardDoc: raw.readingCardDoc ?? raw.reading_card_doc ?? null,
    imradJson: raw.imradJson ?? raw.imrad_json ?? null,
    knowledgeBaseId: raw.knowledgeBaseId ?? raw.knowledge_base_id ?? null,
  } as PaperWithProgress & { readingNotes?: string | null };
}

/**
 * Get paginated papers list
 */
export async function list(params?: PapersQueryParams): Promise<PapersListResponse> {
  const response = await apiClient.get<{
    papers: RawPaper[];
    total: number;
    page: number;
    limit: number;
    totalPages?: number;
  }>('/api/v1/papers', {
    params: {
      page: params?.page || 1,
      limit: params?.limit || 20,
      search: params?.search,
      sortBy: params?.sortBy || 'createdAt',
      sortOrder: params?.sortOrder || 'desc',
      starred: params?.starred !== undefined ? String(params.starred) : undefined,
      readStatus: params?.readStatus,
      dateFrom: params?.dateFrom,
      dateTo: params?.dateTo,
    },
  });

  return {
    success: true,
    data: {
      papers: (response.data.papers || []).map(normalizePaper),
      total: response.data.total || 0,
      page: response.data.page || 1,
      limit: response.data.limit || params?.limit || 20,
      totalPages:
        response.data.totalPages ||
        Math.max(1, Math.ceil((response.data.total || 0) / (response.data.limit || params?.limit || 20))),
    },
  } as PapersListResponse;
}

/** Get paper details */
export async function get(id: string): Promise<Paper> {
  const response = await apiClient.get<RawPaper>(`/api/v1/papers/${id}`);
  return normalizePaper(response.data) as Paper;
}

/** Delete paper */
export async function deletePaper(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/papers/${id}`);
}

export async function remove(id: string): Promise<void> {
  return deletePaper(id);
}

export async function batchDelete(paperIds: string[]): Promise<{
  deletedCount: number;
  requestedCount: number;
  message: string;
}> {
  const response = await apiClient.post<{
    deletedCount: number;
    requestedCount: number;
    message: string;
  }>('/api/v1/papers/batch-delete', {
    paperIds,
  });

  return response.data;
}

/** Batch star/unstar papers */
export async function batchStar(
  paperIds: string[],
  starred: boolean
): Promise<{
  updatedCount: number;
  requestedCount: number;
  starred: boolean;
  message: string;
}> {
  const response = await apiClient.post<{
    updatedCount: number;
    requestedCount: number;
    starred: boolean;
    message: string;
  }>('/api/v1/papers/batch/star', {
    paperIds,
    starred,
  });

  return response.data;
}

/** Get paper processing status */
export async function getStatus(id: string): Promise<{
  paperId: string;
  title?: string;
  status: ProcessingTaskStatus | string;
  progress: number;
  errorMessage?: string | null;
  updatedAt: string;
  completedAt?: string | null;
}> {
  const response = await apiClient.get<{
    paperId: string;
    status: ProcessingTaskStatus | string;
    progress: number;
    errorMessage?: string | null;
    updatedAt?: string;
    completedAt?: string | null;
  }>(`/api/v1/papers/${id}/status`);

  return {
    paperId: response.data.paperId,
    status: response.data.status,
    progress: response.data.progress,
    errorMessage: response.data.errorMessage ?? null,
    updatedAt: response.data.updatedAt || '',
    completedAt: response.data.completedAt ?? null,
  };
}

/** Get paper reading notes */
export async function getSummary(id: string): Promise<{
  paperId: string;
  summary?: string | null;
  readingCardDoc?: ReadingCardDoc | null;
  imrad?: any | null;
  status: string;
  hasNotes: boolean;
}> {
  const response = await apiClient.get<{
    paperId: string;
    summary?: string | null;
    readingCardDoc?: ReadingCardDoc | null;
    imrad?: any | null;
    status: string;
    hasNotes: boolean;
  }>(`/api/v1/papers/${id}/summary`);

  return response.data;
}

/** Regenerate paper reading notes */
export async function regenerateNotes(
  id: string,
  modificationRequest?: string
): Promise<{
  paperId: string;
  status: string;
  message: string;
}> {
  const response = await apiClient.post<{
    paperId: string;
    status: string;
    message: string;
  }>(`/api/v1/papers/${id}/regenerate-notes`, {
    modificationRequest,
  });

  return response.data;
}

/** Export paper notes as Markdown */
export async function exportNotes(id: string): Promise<string> {
  const response = await apiClient.get(`/api/v1/papers/${id}/notes/export`, {
    responseType: 'text',
  });

  return response.data as string;
}

/** Toggle paper starred status */
export async function toggleStar(id: string, starred: boolean): Promise<Paper> {
  const response = await apiClient.patch<RawPaper>(`/api/v1/papers/${id}/starred`, {
    starred: String(starred),
  });

  return normalizePaper(response.data) as Paper;
}

/** Update paper fields */
export async function update(id: string, data: { readingNotes?: string }): Promise<Paper> {
  const response = await apiClient.patch<RawPaper>(`/api/v1/papers/${id}`, data);
  return normalizePaper(response.data) as Paper;
}

/** Download paper PDF as blob */
export async function downloadPdfBlob(id: string): Promise<Blob> {
  const response = await apiClient.get(`/api/v1/papers/${id}/download`, {
    responseType: 'blob',
  });

  return response.data as Blob;
}

/** Save paper reading progress */
export async function saveReadingProgress(id: string, currentPage: number): Promise<void> {
  await apiClient.post(`/api/v1/reading-progress/${id}`, {
    currentPage,
  });
}

/** Get PDF download URL */
export function getPdfUrl(id: string): string {
  return `${apiClient.defaults.baseURL || ''}/api/v1/papers/${id}/download`;
}
