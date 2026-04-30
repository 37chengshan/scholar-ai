# ScholarAI v2.0 Close-Out Pass Framework

## Purpose

冻结 v2.0 收尾通过标准，避免只按“功能基本有了”宣布完成。

## Pass Rule

ScholarAI v2.0 只有在以下条件全部成立时才算 `PASS`：

1. 10 条完成标准全部达成。
2. 当前 Phase 4 / Phase 6 已知 4 个回归全部修复。
3. RAG 真实链路测试通过，不能只靠 unit tests。
4. Phase 6 offline gate 通过，并阻断本地 release gate 与 CI release gate。
5. close-out 证据包齐全，可追溯到代码、测试、benchmark runs 与 diff。

任一项失败，v2.0 即为 `NOT PASS`。

## RAG Framework Lanes

- RAG-1：Evidence -> Notes persistence
- RAG-2：Reading Card + section-aware single-paper QA
- RAG-3：multi-paper compare with hybrid retrieval + rerank
- RAG-4：KB review / related-work generation with citations + run trace
- RAG-5：Phase 6 benchmark / diff / dashboard / regression gate

## Benchmark Minimums

冻结 benchmark 目录：`apps/api/artifacts/benchmarks/phase6/`

必须同时满足：

- `paper_count >= 50`
- `query_count >= 128`
- 8 个 families 全量覆盖：
  - `single_fact`
  - `method`
  - `experiment_result`
  - `table`
  - `figure_caption`
  - `multi_paper_compare`
  - `kb_global`
  - `no_answer`
- `queries[]` 必须是完整冻结集，不接受仅代表样本
- manifest 中必须同时存在：
  - 1 个 offline baseline run
  - 1 个 offline candidate run
- candidate run 必须带 `diff_from_baseline.json`
- 每个 run 必须完整包含：
  - `meta.json`
  - `dashboard_summary.json`
  - `retrieval.json`
  - `answer_quality.json`
  - `citation_jump.json`

## Offline Gate Thresholds

candidate run 必须通过：

- `retrieval_hit_rate >= 0.80`
- `recall_at_5 >= 0.75`
- `citation_jump_valid_rate >= 0.85`
- `answer_supported_rate >= 0.80`
- `groundedness >= 0.70`
- `abstain_precision >= 0.80`
- `latency_p95 <= 8.0s`
- `fallback_used_count <= 5`
- `cost_per_answer` 存在
- `overall_verdict == PASS`

Diff 对 baseline 还必须满足：

- 以下 6 项不允许回退：
  - `retrieval_hit_rate`
  - `answer_supported_rate`
  - `groundedness`
  - `citation_jump_valid_rate`
  - `abstain_precision`
  - `recall_at_5`
- `latency_p95` 允许轻微回退的唯一条件：
  - 仍然 `<= 8.0s`
  - 且最终 close-out 报告显式说明 tradeoff

## Required Real Tests

前端 / E2E：

- `apps/web/e2e/chat-critical.spec.ts`
- `apps/web/e2e/chat-evidence.spec.ts`
- `apps/web/e2e/retrieval-critical.spec.ts`
- `apps/web/e2e/notes-rendering.spec.ts`
- `apps/web/e2e/kb-critical.spec.ts`
- `apps/web/e2e/compare-critical.spec.ts`

后端 / integration path：

- compare endpoint 返回真实 requested papers evidence，不得回退到 synthetic lexical placeholders
- chat compare follow-up 必须消费 `context.paper_ids`
- section-aware single-paper retrieval 必须正确下推 filters
- review draft pipeline 必须经 canonical API 路径返回 citations + run trace

benchmark / dashboard：

- 1 个 offline blocking run
- 1 个 online report-only run
- 1 个 candidate-vs-baseline diff
- `/api/v1/evals/*` 成功读取真实 artifact
- `/analytics` 成功渲染 overview / run detail / diff

## Release Evidence Bundle

发版前必须产出并归档：

- 最新 offline gate 结果
- baseline run summary
- candidate run summary
- diff report
- `/analytics` 基于真实 run data 的证明
- governance / structure / code-boundary checks 输出
- 最终 close-out 审计报告

## Current Implementation Hooks

- compare v4 真源：`apps/api/app/api/compare.py` + `apps/api/app/services/compare_service.py`
- chat scoped RAG 真源：`apps/api/app/api/chat.py`
- eval artifact gate 真源：`apps/api/app/services/eval_service.py`
- gate script：`scripts/evals/phase6_gate.py`
- 本地 release gate：`scripts/release/run-v2-gate.sh`
- CI release gate：`.github/workflows/release-gate.yml`
