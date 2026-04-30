# v3.0J RAG Benchmark 与对比门禁研究文档

> 日期：2026-04-30  
> 状态：research-draft  
> 用途：定义 `Phase 3.0-J` 的 benchmark 边界，使其同时服务线上化迁移、框架创新和 release gate。  

## 1. 目标

建立统一的 RAG benchmark 与 comparative gate，用同一口径比较当前线上基线、候选框架和关键策略改动。

## 2. 覆盖范围

1. retrieval quality
2. citation fidelity
3. claim support
4. review quality
5. latency
6. cost
7. failure rate
8. real-world workflow success

## 3. 明确边界

1. 本阶段不替代 `Phase 3.0-A` 的学术 benchmark 资产建设，而是把其扩展为系统级对比门禁。
2. benchmark 不只看离线指标，必须纳入真实工作流结果。
3. benchmark 不直接决定产品方向，但为 Phase H/I 的取舍提供硬证据。
4. 不在本研究文档中冻结具体阈值，阈值由后续执行计划结合基线结果确定。

## 4. 预期产物

1. benchmark taxonomy
2. baseline / candidate / diff protocol
3. online transition comparison suite
4. framework innovation comparison suite
5. release gate input contract

## 5. 后续文档

后续应补：

1. benchmark schema extension
2. comparative runbook
3. gate threshold proposal

## 6. 当前已冻结的 Phase I Hook

`Phase I` 当前主链已统一输出以下字段，作为 `Phase J comparative gate` 的正式输入：

1. `task_family`
2. `execution_mode`
3. `truthfulness_report_summary`
4. `retrieval_plane_policy`
5. `degraded_conditions`
6. `citation_coverage`
7. `unsupported_claim_rate`
8. `total_latency_ms`
9. `cost_estimate`

正式脚本：

1. `scripts/evals/run_phase_j_comparative_gate.py`

gate 基本规则：

1. 候选若缺少 hook，直接失败。
2. `unsupported_claim_rate` 不允许显著回退。
3. `citation_coverage` 不允许回退。
4. `latency / cost / degraded_rate` 的回归必须在预算内。
