import type { HttpClient } from '../client/http';
import type {
  EvaluationOverview,
  BenchmarkRunSummary,
  BenchmarkRunDetail,
  BenchmarkDiff,
  EvalRunMode,
} from '@scholar-ai/types';

export interface EvalApi {
  getOverview(params?: { benchmark?: 'phase6' | 'v3_0_academic' }): Promise<EvaluationOverview>;
  listRuns(params?: { benchmark?: 'phase6' | 'v3_0_academic'; mode?: EvalRunMode; limit?: number; offset?: number }): Promise<{
    items: BenchmarkRunSummary[];
    total: number;
  }>;
  getRunDetail(runId: string, params?: { benchmark?: 'phase6' | 'v3_0_academic' }): Promise<BenchmarkRunDetail>;
  getDiff(baseRunId: string, candidateRunId: string, params?: { benchmark?: 'phase6' | 'v3_0_academic' }): Promise<BenchmarkDiff>;
}

export function createEvalApi(client: HttpClient): EvalApi {
  return {
    async getOverview(params) {
      return client.get<EvaluationOverview>(
        '/api/v1/evals/overview',
        { params: params as Record<string, unknown> }
      );
    },

    async listRuns(params) {
      const res = await client.get<{
        items: BenchmarkRunSummary[];
        total?: number;
      }>('/api/v1/evals/runs', { params: params as Record<string, unknown> });
      return {
        items: Array.isArray(res.items) ? res.items : [],
        total: typeof res.total === 'number' ? res.total : Array.isArray(res.items) ? res.items.length : 0,
      };
    },

    async getRunDetail(runId, params) {
      return client.get<BenchmarkRunDetail>(
        `/api/v1/evals/runs/${runId}`,
        { params: params as Record<string, unknown> }
      );
    },

    async getDiff(baseRunId, candidateRunId, params) {
      return client.get<BenchmarkDiff>(
        '/api/v1/evals/diff',
        {
          params: {
            ...(params as Record<string, unknown> | undefined),
            base_run_id: baseRunId,
            candidate_run_id: candidateRunId,
          },
        }
      );
    },
  };
}
