---
owner: ai-runtime
status: done
depends_on:
  - 2026-05-11_v4_0_phase_6_academic_rag_optimization_research
  - 18_v4_0_overview_plan
last_verified_at: 2026-05-11
evidence_commits:
  - working-tree-v4-0-phase-6-execution
---

# 24 v4.0-6 执行计划：Academic RAG Optimization

> 日期：2026-05-11
> 状态：execution-complete
> 上游研究：`docs/plans/v4_0/active/phase_6/2026-05-11_v4_0_phase_6_academic_rag_optimization_research.md`

## 0. 执行状态

本轮执行范围冻结为：

```txt
evidence action contract
-> rag recoveryActions
-> compare recovery_actions
-> review claim-level recovery_actions
- no second runtime
- no graph-first mainline replacement
```

## 1. 目标

1. `rag` 主链显式返回统一 `recoveryActions`。
2. `compare` 输出与 `rag` 共享 recovery action 语义。
3. `review` claim rows 除 `repair_hint` 外，还要带 `recovery_actions`。
4. 契约和资源文档承认这些字段为 Phase 6 首批真源。
5. 必须有真实后端测试与治理检查证据。

## 2. 交付单元

### WP1：统一 action builder

输出：

1. `apps/api/app/services/evidence_action_service.py`
2. `apps/api/app/rag_v3/schemas.py`

### WP2：主链接线

输出：

1. `apps/api/app/rag_v3/main_path_service.py`
2. `apps/api/app/core/agentic_retrieval.py`
3. `apps/api/app/services/compare_service.py`
4. `apps/api/app/services/review_draft_service.py`
5. `apps/api/app/api/rag.py`

### WP3：契约与计划回填

输出：

1. `docs/specs/architecture/api-contract.md`
2. `docs/specs/domain/resources.md`
3. `docs/plans/PLAN_STATUS.md`
4. `docs/specs/governance/phase-delivery-ledger.md`

## 3. 验收

1. `cd apps/api && PYTHONPATH=$PWD .venv/bin/pytest -q tests/unit/test_truthfulness_service.py tests/unit/test_answer_contract.py tests/unit/test_rag_trace_contract.py tests/unit/test_phase4_hybrid_compare.py tests/unit/test_review_draft_service.py tests/unit/test_agentic_iteration3.py tests/integration/test_rag_claim_verification.py --maxfail=1`
2. `bash scripts/check-phase-tracking.sh`
3. `bash scripts/check-doc-governance.sh`
4. `bash scripts/check-governance.sh`
