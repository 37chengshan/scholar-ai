---
phase: pr7-pr8-pr10-final-review
reviewed: 2026-04-17T14:45:30Z
depth: strict
files_reviewed: 11
files_reviewed_list:
  - apps/api/app/api/rag.py
  - apps/api/app/core/streaming.py
  - apps/api/app/core/docling_service.py
  - apps/api/app/workers/storage_manager.py
  - apps/api/tests/unit/test_docling_chunk_strategy.py
  - apps/api/tests/unit/test_sprint4_docling_config.py
  - apps/api/tests/unit/test_pr7_storage_evidence.py
  - apps/api/tests/unit/test_storage_manager.py
  - apps/api/tests/unit/test_rag_confidence.py
  - apps/api/tests/unit/test_streaming_contract.py
  - docs/plans/pr10-first-round-closeout-checklist.md
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: scope_passed_with_baseline_gaps
---

# Phase pr7-pr8-pr10-final-review: Code Review Report

**Reviewed:** 2026-04-17T14:45:30Z
**Depth:** strict
**Files Reviewed:** 11
**Status:** scope_passed_with_baseline_gaps

## Scope Verdict

本轮六项执行目标（5.1、P7-A、P7 模板、P7-B/C、P8-A、PR10 第一轮收尾清单）在代码与门禁范围内已闭环，且完成复测。发现的未闭环问题属于测试基线历史漂移，不是本轮改动引入。

## Findings (Ordered by Severity)

### WR-01: `tests/test_rag.py` 仍使用历史路由断言

**File:** `apps/api/tests/test_rag.py`
**Issue:** 用例对 `/rag/query` 断言 `200/501`，当前应用路由实际返回 `404`，表现为测试基线与现行路由契约不一致。
**Impact:** 全量回归时会出现假失败，影响 CI 信号质量。
**Action:** 后续基线修复时统一替换为现行 API 路由前缀并对鉴权/返回结构做新契约断言。

### WR-02: `tests/unit/test_agentic_citations.py` 依赖已迁移私有方法

**File:** `apps/api/tests/unit/test_agentic_citations.py`
**Issue:** 用例调用 `_build_context_with_citations` 等不存在的方法，属于测试与实现长期漂移。
**Impact:** 相关测试不可作为本轮质量门禁依据。
**Action:** 作为独立清理项重写为当前 orchestrator 契约测试（`_collect_sources`/最终回答验证路径）。

### IN-01: 已修复的真实回归（图片-only 入库）

**File:** `apps/api/app/workers/storage_manager.py`
**Issue:** 仅图片/表格输入时返回 ID 为空，导致历史用例失败。
**Fix Applied:** 保留图片/表格-only 场景的插入 ID 返回；并在无文本 chunk 时跳过 Neo4j chunk 建图。
**Verification:** `tests/unit/test_storage_manager.py` 全量通过。

## Validation Evidence

- Backend scoped suite:
  - `cd apps/api && ./.venv/bin/python -m pytest -q tests/unit/test_docling_chunk_strategy.py tests/unit/test_sprint4_docling_config.py tests/unit/test_pr7_storage_evidence.py tests/unit/test_storage_manager.py tests/unit/test_rag_confidence.py tests/unit/test_streaming_contract.py`
  - Result: `46 passed`
- Governance gates:
  - `bash scripts/check-plan-governance.sh`
  - `bash scripts/check-governance.sh`
  - Result: 全部通过
- Frontend scoped suite:
  - `cd apps/web && pnpm vitest run src/services/chatApi.test.ts src/features/kb/components/KnowledgeWorkspaceShell.test.tsx src/app/pages/Chat.test.tsx`
  - `cd apps/web && pnpm type-check`
  - Result: `3 files, 5 tests passed` + `type-check passed`

## Six-Item Completion Matrix

| Item | Status | Review Evidence |
| --- | --- | --- |
| 1. 计划系统修复 PR (5.1) | done | `check-plan-governance` + `check-governance` 通过 |
| 2. PR7 P7-A（解析契约 + adaptive chunking） | done | docling 相关单测通过 |
| 3. PR7 验收回填模板 | done | `docs/plans/templates/PR7_ACCEPTANCE_BACKFILL_TEMPLATE.md` 已建立 |
| 4. PR7 P7-B/P7-C | done | storage evidence + storage manager 单测通过 |
| 5. PR8 P8-A（检索契约统一启动） | done | rag confidence + streaming contract 单测通过 |
| 6. PR10 收尾清单第一轮 | done（第一轮范围） | checklist、前端定向测试与 type-check 通过 |

---

_Reviewed: 2026-04-17T14:45:30Z_
_Reviewer: Copilot (GPT-5.3-Codex)_
_Depth: strict_
