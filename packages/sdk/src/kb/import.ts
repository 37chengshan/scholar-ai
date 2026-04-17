import type { HttpClient } from '../client/http';
import type { ImportJobDto, ImportJobStatus, SourceType } from '@scholar-ai/types';

export interface ImportApi {
  list: (kbId: string, params?: { status?: ImportJobStatus; limit?: number; offset?: number }) => Promise<{ jobs: ImportJobDto[]; total: number; limit: number; offset: number }>;
  get: (jobId: string) => Promise<ImportJobDto>;
  create: (kbId: string, request: { sourceType: SourceType; payload: Record<string, unknown> }) => Promise<ImportJobDto>;
  retry: (jobId: string, options?: { retryFromStage?: string }) => Promise<ImportJobDto>;
  cancel: (jobId: string) => Promise<{ importJobId: string; status: 'cancelled' }>;
}

export function createImportApi(client: HttpClient): ImportApi {
  return {
    list: (kbId, params) =>
      client.get<{ jobs: ImportJobDto[]; total: number; limit: number; offset: number }>('/api/v1/import-jobs', {
        params: { knowledgeBaseId: kbId, ...params },
      }),
    get: (jobId) => client.get<ImportJobDto>(`/api/v1/import-jobs/${jobId}`),
    create: (kbId, request) => client.post<ImportJobDto>(`/api/v1/knowledge-bases/${kbId}/imports`, request),
    retry: (jobId, options) => client.post<ImportJobDto>(`/api/v1/import-jobs/${jobId}/retry`, options),
    cancel: (jobId) => client.post<{ importJobId: string; status: 'cancelled' }>(`/api/v1/import-jobs/${jobId}/cancel`),
  };
}
