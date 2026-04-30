# v3.0I Experiment Backlog And Adoption Order

> 日期：2026-04-30  
> 状态：freeze  
> 目标：补齐 WP6 的 experiment backlog、adoption order 与 Phase J benchmark contract hooks。

## 1. Benchmark Contract Hooks

所有候选路线统一输出以下 hooks 供 `Phase J` 消费：

1. `task_family`
2. `execution_mode`
3. `truthfulness_report_summary`
4. `retrieval_plane_policy`
5. `degraded_conditions`
6. `citation_coverage`
7. `unsupported_claim_rate`
8. `total_latency_ms`
9. `cost_estimate`

正式 gate 脚本：

1. `scripts/evals/run_phase_j_comparative_gate.py`

## 2. 主线候选

### Wave 1

1. `PaperQA-style evidence-first workflow`
   - target task family: `single_paper_fact`, `single_paper_method`
   - expected gain: citation fidelity
   - added cost: low
   - rollback condition: unsupported claim rate regression
2. `rarr_cove_scifact_lite verifier`
   - target task family: `chat`, `compare`, `review`
   - expected gain: claim support precision
   - added cost: low-medium
   - rollback condition: latency regression without truthfulness gain
3. `STORM-lite global review`
   - target task family: `survey`, `related_work`, `method_evolution`
   - expected gain: review coverage, structured synthesis
   - added cost: medium
   - rollback condition: citation coverage regression or partial draft rate increase

### Wave 2

1. `RAPTOR-style hierarchical retrieval`
2. `Adaptive-RAG runtime policy threshold tuning`
3. `DSPy-style synthesis optimization`

## 3. 实验 backlog

1. `GraphRAG`
   - target: `conflicting_evidence`, `global_review`
   - expected gain: contradiction tracing
   - added cost: high
   - rollback condition: cost or degraded rate exceeds gate budget
2. `LightRAG`
   - target: `cross_paper`, `survey`
   - expected gain: lighter graph augmentation
   - added cost: medium-high
   - rollback condition: no measurable citation/truthfulness lift
3. `IRCoT`
   - target: `hard`, `conflicting_evidence`
   - expected gain: deeper reasoning with retrieval iteration
   - added cost: high
   - rollback condition: latency regression beyond gate
4. `OpenScholar-style long-form synthesis`
   - target: `survey`, `related_work`
   - expected gain: longer coherent reviews
   - added cost: high
   - rollback condition: evidence traceability weakens
5. `stronger SciFact classifier backend`
   - target: all truthfulness-required tasks
   - expected gain: claim entailment precision
   - added cost: medium
   - rollback condition: unsupported claim reduction does not offset cost

## 4. Adoption Order Freeze

1. `dual-kernel route metadata`
2. `STORM-lite global review`
3. `rarr_cove_scifact_lite verifier`
4. `Phase J comparative gate`
5. `RAPTOR hierarchical retrieval`
6. `DSPy tuning`
7. `GraphRAG / LightRAG / IRCoT / OpenScholar` only after gate pass