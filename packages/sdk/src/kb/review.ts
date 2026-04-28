import type { HttpClient } from '../client/http';
import type {
  CreateReviewDraftRequestDto,
  ReviewDraftDto,
  ReviewRunDetailDto,
  ReviewRunSummaryDto,
} from '@scholar-ai/types';

interface ListEnvelope<T> {
  success: boolean;
  data: { items: T[] };
  meta?: { limit: number; offset: number; total: number };
}

interface ItemEnvelope<T> {
  success: boolean;
  data: T;
}

export interface KnowledgeReviewApi {
  createDraft: (kbId: string, request: CreateReviewDraftRequestDto) => Promise<ReviewDraftDto>;
  listDrafts: (kbId: string, params?: { limit?: number; offset?: number }) => Promise<{ items: ReviewDraftDto[]; total: number; limit: number; offset: number }>;
  getDraft: (kbId: string, draftId: string) => Promise<ReviewDraftDto>;
  retryDraft: (kbId: string, draftId: string) => Promise<ReviewDraftDto>;
  listRuns: (kbId: string, params?: { limit?: number; offset?: number }) => Promise<{ items: ReviewRunSummaryDto[]; total: number; limit: number; offset: number }>;
  getRunDetail: (runId: string) => Promise<ReviewRunDetailDto>;
}

export function createKnowledgeReviewApi(client: HttpClient): KnowledgeReviewApi {
  return {
    async createDraft(kbId, request) {
      const response = await client.post<ItemEnvelope<ReviewDraftDto>>(
        `/api/v1/knowledge-bases/${kbId}/review-drafts`,
        request,
      );
      return response.data;
    },

    async listDrafts(kbId, params) {
      const response = await client.get<ListEnvelope<ReviewDraftDto>>(
        `/api/v1/knowledge-bases/${kbId}/review-drafts`,
        { params: params as Record<string, unknown> | undefined },
      );
      return {
        items: response.data.items,
        total: response.meta?.total ?? response.data.items.length,
        limit: response.meta?.limit ?? (params?.limit ?? 20),
        offset: response.meta?.offset ?? (params?.offset ?? 0),
      };
    },

    async getDraft(kbId, draftId) {
      const response = await client.get<ItemEnvelope<ReviewDraftDto>>(
        `/api/v1/knowledge-bases/${kbId}/review-drafts/${draftId}`,
      );
      return response.data;
    },

    async retryDraft(kbId, draftId) {
      const response = await client.post<ItemEnvelope<ReviewDraftDto>>(
        `/api/v1/knowledge-bases/${kbId}/review-drafts/${draftId}/retry`,
        { force: false },
      );
      return response.data;
    },

    async listRuns(kbId, params) {
      const response = await client.get<ListEnvelope<ReviewRunSummaryDto>>(
        `/api/v1/knowledge-bases/${kbId}/runs`,
        { params: params as Record<string, unknown> | undefined },
      );
      return {
        items: response.data.items,
        total: response.meta?.total ?? response.data.items.length,
        limit: response.meta?.limit ?? (params?.limit ?? 20),
        offset: response.meta?.offset ?? (params?.offset ?? 0),
      };
    },

    async getRunDetail(runId) {
      const response = await client.get<ItemEnvelope<ReviewRunDetailDto>>(`/api/v1/runs/${runId}`);
      return response.data;
    },
  };
}
