import type { HttpClient } from '../client/http';
import type {
  EvaluationOverview,
  BenchmarkRunSummary,
  BenchmarkRunDetail,
  BenchmarkDiff,
  EvalRunMode,
} from '@scholar-ai/types';

export interface EvalApi {
  getOverview(): Promise<EvaluationOverview>;
  listRuns(params?: { mode?: EvalRunMode; limit?: number; offset?: number }): Promise<{
    items: BenchmarkRunSummary[];
    total: number;
  }>;
  getRunDetail(runId: string): Promise<BenchmarkRunDetail>;
  getDiff(baseRunId: string, candidateRunId: string): Promise<BenchmarkDiff>;
}

export function createEvalApi(client: HttpClient): EvalApi {
  return {
    async getOverview() {
      return client.get<EvaluationOverview>(
        '/api/v1/evals/overview'
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

    async getRunDetail(runId) {
      return client.get<BenchmarkRunDetail>(
        `/api/v1/evals/runs/${runId}`
      );
    },

    async getDiff(baseRunId, candidateRunId) {
      return client.get<BenchmarkDiff>(
        '/api/v1/evals/diff',
        { params: { base_run_id: baseRunId, candidate_run_id: candidateRunId } }
      );
    },
  };
}
