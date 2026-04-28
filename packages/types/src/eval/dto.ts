// Phase 6 Evaluation DTO types

export type EvalRunMode = 'offline' | 'online';
export type EvalRunVerdict = 'PASS' | 'FAIL' | 'UNKNOWN';
export type MetricDeltaStatus = 'improved' | 'regressed' | 'unchanged';

export interface TopKRecall {
  recall_at_5: number;
  recall_at_10: number;
}

export interface NormalizedMetrics {
  retrieval_hit_rate: number;
  top_k_recall: TopKRecall;
  rerank_gain: number;
  citation_jump_valid_rate: number;
  answer_supported_rate: number;
  groundedness: number;
  abstain_precision: number;
  fallback_used_count: number;
  latency_p50: number;
  latency_p95: number;
  cost_per_answer: number;
  overall_verdict: EvalRunVerdict;
  gate_failures: string[];
}

export interface BenchmarkRunMeta {
  run_id: string;
  git_sha: string;
  dataset_version: string;
  mode: EvalRunMode;
  reranker: 'on' | 'off';
  baseline_for?: string | null;
  overall_verdict: EvalRunVerdict;
  created_at: string;
  query_count?: number;
  family_counts?: Record<string, number>;
}

export interface FamilyRetrievalBreakdown {
  recall_at_5: number;
  recall_at_10: number;
}

export interface FamilyQualityBreakdown {
  answer_supported_rate: number;
  groundedness: number;
}

export interface BenchmarkRunByFamily {
  retrieval: Record<string, FamilyRetrievalBreakdown>;
  answer_quality: Record<string, FamilyQualityBreakdown>;
}

export interface CitationJumpDetail {
  total_checked: number;
  valid: number;
  invalid: number;
  invalid_reasons: Record<string, number>;
}

export interface BenchmarkRunSummary {
  run_id: string;
  git_sha: string;
  dataset_version: string;
  mode: EvalRunMode;
  reranker: 'on' | 'off';
  baseline_for?: string | null;
  overall_verdict: EvalRunVerdict;
  created_at: string;
}

export interface BenchmarkRunDetail {
  run_id: string;
  meta: BenchmarkRunMeta;
  metrics: NormalizedMetrics;
  by_family: BenchmarkRunByFamily;
  citation_jump_detail: CitationJumpDetail;
}

export interface GateVerdict {
  run_id: string;
  verdict: EvalRunVerdict;
  gate_failures: string[];
  metrics: NormalizedMetrics;
}

export interface EvaluationOverview {
  latest_offline_gate: GateVerdict | null;
  run_count: number;
  offline_count: number;
  online_count: number;
  recent_runs: BenchmarkRunSummary[];
}

export interface MetricDelta {
  base: number;
  candidate: number;
  delta: number;
  status: MetricDeltaStatus;
}

export interface BenchmarkDiff {
  base_run_id: string;
  candidate_run_id: string;
  base_verdict: EvalRunVerdict;
  candidate_verdict: EvalRunVerdict;
  deltas: Record<string, MetricDelta>;
  fallback_used_count_delta: number;
  summary: {
    improved: number;
    regressed: number;
    unchanged: number;
  };
}
