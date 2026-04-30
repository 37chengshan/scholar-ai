import { createKnowledgeReviewApi } from '@scholar-ai/sdk';
import type {
  CreateReviewDraftRequestDto,
  ReviewClaimRepairRequestDto,
  ReviewDraftDto,
  ReviewRunDetailDto,
  ReviewRunSummaryDto,
} from '@scholar-ai/types';
import { sdkHttpClient } from './sdkHttpClient';

const reviewSdk = createKnowledgeReviewApi(sdkHttpClient);

export const kbReviewApi = {
  createDraft: (kbId: string, request: CreateReviewDraftRequestDto): Promise<ReviewDraftDto> =>
    reviewSdk.createDraft(kbId, request),
  listDrafts: (kbId: string, params?: { limit?: number; offset?: number }) => reviewSdk.listDrafts(kbId, params),
  getDraft: (kbId: string, draftId: string): Promise<ReviewDraftDto> => reviewSdk.getDraft(kbId, draftId),
  retryDraft: (kbId: string, draftId: string): Promise<ReviewDraftDto> => reviewSdk.retryDraft(kbId, draftId),
  repairClaim: (kbId: string, draftId: string, request: ReviewClaimRepairRequestDto): Promise<ReviewDraftDto> =>
    reviewSdk.repairClaim(kbId, draftId, request),
  listRuns: (kbId: string, params?: { limit?: number; offset?: number }): Promise<{ items: ReviewRunSummaryDto[]; total: number; limit: number; offset: number }> =>
    reviewSdk.listRuns(kbId, params),
  getRunDetail: (runId: string): Promise<ReviewRunDetailDto> => reviewSdk.getRunDetail(runId),
};
