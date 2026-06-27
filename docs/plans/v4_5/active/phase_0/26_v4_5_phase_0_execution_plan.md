---
owner: product-engineering
status: done
depends_on:
  - 25_v4_5_overview_plan
  - 2026-05-13_v4_5_release_readiness_bridge_research
last_verified_at: 2026-05-13
evidence_commits:
  - working-tree-v4-5-phase-0-kickoff
---

# 26 v4.5-0 执行计划：Release Readiness Bridge Kickoff

> 日期：2026-05-13  
> 状态：execution-plan-complete

## 0. 执行状态

本轮 phase_0 只冻结 bridge 的启动真源与 benchmark 入口：

```txt
truth freeze
+ gate input matrix
+ live benchmark runner
- no release verdict yet
- no fake KB-ready claim
```

## 1. 目标

1. 把 v4.5 从“研究文档 + 目录预热”推进到正式 phase_0。
2. 让 live benchmark 成为仓库里的真实脚本入口，而不是计划占位。
3. 冻结 v4.5 对 runtime truth、auth、样本选择和 blocked cases 的正式口径。
4. 为后续 release gate、walkthrough 和 verdict 报告建立可复用产物路径。

## 2. 交付单元

### WP1：Phase 0 文档冻结

输出：

1. `docs/plans/v4_5/active/overview/25_v4_5_overview_plan.md`
2. `docs/plans/v4_5/active/phase_0/26_v4_5_phase_0_execution_plan.md`
3. `docs/plans/v4_5/active/phase_0/v4_5_runtime_contract_freeze.md`
4. `docs/plans/v4_5/active/phase_0/v4_5_gate_input_matrix.md`

### WP2：真实 benchmark 入口

输出：

1. `scripts/evals/run_v4_5_live_rag_benchmark.py`
2. `artifacts/validation-results/v4_5/live_rag_benchmark/<timestamp>/summary.json`
3. `artifacts/validation-results/v4_5/live_rag_benchmark/<timestamp>/summary.md`

### WP3：治理同步

输出：

1. `docs/README.md`
2. `docs/plans/README.md`
3. `docs/plans/PLAN_STATUS.md`
4. `docs/specs/governance/phase-delivery-ledger.md`
5. `docs/plans/v4_5/README.md`
6. `docs/plans/v4_5/active/phase_0/README.md`

## 3. benchmark 执行策略

### 3.1 启动方式

1. 默认允许脚本自启动本地 backend。
2. backend 启动环境固定为：
   - `ENVIRONMENT=test`
   - `NEO4J_DISABLED=true`
   - `AI_STARTUP_MODE=off`
   - `PREFLIGHT_ON_STARTUP=false`
3. 启动后必须等待 `/health/live` 通过，再进入路由 benchmark。

### 3.2 认证方式

1. 脚本优先复用数据库中的真实样本用户。
2. 本地 benchmark 允许通过内部 token mint 生成 `Authorization: Bearer ...`，避免被未知密码阻断。
3. 该策略只适用于本地 phase_0 benchmark，不构成对外登录流替代。

### 3.3 当前 route 范围

本轮 benchmark 入口冻结为：

1. `POST /api/v1/chat`
2. `POST /api/v1/search/evidence`
3. `POST /api/v1/queries/query`
4. `POST /api/v1/compare/v4`
5. `POST /api/v1/knowledge-bases/{kb_id}/query`

### 3.4 blocked truth

若本地不存在任何可用 KB membership 样本，则：

1. KB-scoped benchmark case 必须输出 `blocked`
2. summary 中必须记录 `blocked-by-data-truth`
3. 不允许把 KB-scoped gate 写成 pass

补充边界：

1. 若 `Paper.knowledge_base_id` 已有真实样本，则 `kb-scoped chat/search/query` 必须进入真实 pass/fail。
2. `knowledge_base_papers = 0` 只代表 many-to-many association truth 仍为空，必须在报告中单独标注为结构性风险。

## 4. 验收

1. `python3 scripts/evals/run_v4_5_live_rag_benchmark.py --help`
2. `python3 scripts/evals/run_v4_5_live_rag_benchmark.py --launch-backend`
3. `bash scripts/check-doc-governance.sh`
4. `bash scripts/check-plan-governance.sh`
5. `bash scripts/check-phase-tracking.sh`
6. `bash scripts/check-governance.sh`
