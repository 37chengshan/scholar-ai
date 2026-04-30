import type { HttpClient } from '../client/http';
import type {
  CreateReviewDraftRequestDto,
  ReviewClaimRepairRequestDto,
  ReviewDraftDto,
  ReviewRunDetailDto,
  ReviewRunSummaryDto,
} from '@scholar-ai/types';

interface ListResponse<T> {
  items: T[];
  meta?: { limit: number; offset: number; total: number };
}

export interface KnowledgeReviewApi {
  createDraft: (kbId: string, request: CreateReviewDraftRequestDto) => Promise<ReviewDraftDto>;
  listDrafts: (kbId: string, params?: { limit?: number; offset?: number }) => Promise<{ items: ReviewDraftDto[]; total: number; limit: number; offset: number }>;
  getDraft: (kbId: string, draftId: string) => Promise<ReviewDraftDto>;
  retryDraft: (kbId: string, draftId: string) => Promise<ReviewDraftDto>;
  repairClaim: (kbId: string, draftId: string, request: ReviewClaimRepairRequestDto) => Promise<ReviewDraftDto>;
  listRuns: (kbId: string, params?: { limit?: number; offset?: number }) => Promise<{ items: ReviewRunSummaryDto[]; total: number; limit: number; offset: number }>;
  getRunDetail: (runId: string) => Promise<ReviewRunDetailDto>;
}

export function createKnowledgeReviewApi(client: HttpClient): KnowledgeReviewApi {
  return {
    async createDraft(kbId, request) {
      const response = await client.post<ReviewDraftDto>(
        `/api/v1/knowledge-bases/${kbId}/review-drafts`,
        request,
      );
      return response;
    },

    async listDrafts(kbId, params) {
      const response = await client.get<ListResponse<ReviewDraftDto>>(
        `/api/v1/knowledge-bases/${kbId}/review-drafts`,
        { params: params as Record<string, unknown> | undefined },
      );
      const items = Array.isArray(response.items) ? response.items : [];
      return {
        items,
        total: response.meta?.total ?? items.length,
        limit: response.meta?.limit ?? (params?.limit ?? 20),
        offset: response.meta?.offset ?? (params?.offset ?? 0),
      };
    },

    async getDraft(kbId, draftId) {
      const response = await client.get<ReviewDraftDto>(
        `/api/v1/knowledge-bases/${kbId}/review-drafts/${draftId}`,
      );
      return response;
    },

    async retryDraft(kbId, draftId) {
      const response = await client.post<ReviewDraftDto>(
        `/api/v1/knowledge-bases/${kbId}/review-drafts/${draftId}/retry`,
        { force: false },
      );
      return response;
    },

    async repairClaim(kbId, draftId, request) {
      const response = await client.post<ReviewDraftDto>(
        `/api/v1/knowledge-bases/${kbId}/review-drafts/${draftId}/claims/repair`,
        request,
      );
      return response;
    },

    async listRuns(kbId, params) {
      const response = await client.get<ListResponse<ReviewRunSummaryDto>>(
        `/api/v1/knowledge-bases/${kbId}/runs`,
        { params: params as Record<string, unknown> | undefined },
      );
      const items = Array.isArray(response.items) ? response.items : [];
      return {
        items,
        total: response.meta?.total ?? items.length,
        limit: response.meta?.limit ?? (params?.limit ?? 20),
        offset: response.meta?.offset ?? (params?.offset ?? 0),
      };
    },

    async getRunDetail(runId) {
      const response = await client.get<ReviewRunDetailDto>(`/api/v1/runs/${runId}`);
      return response;
    },
  };
}
