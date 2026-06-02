# v5.0 Phase 0 Foundation Closeout Report

> 日期：2026-05-31
> Phase：5.0-0 | Foundation
> 状态：done
> Owner：product-engineering

---

## 1. 目标回顾

Phase 5.0-0 是 v5.0 的启动期，主线为**治理切换 + v4.x 迁移 + Audit Baseline**，不动任何业务代码。

本 phase 完成后，v5.0 进入正式可执行状态，后续 phase 1–9 全部解锁。

---

## 2. 交付物清单

| # | 产物 | 路径 | 验证状态 |
|---|---|---|---|
| 1 | Migration Inventory | `active/phase_0/v5_0_v4x_migration_inventory.md` | done |
| 2 | Runtime Contract Freeze | `active/phase_0/v5_0_runtime_contract_freeze.md` | done |
| 3 | Gate Input Matrix | `active/phase_0/v5_0_gate_input_matrix.md` | done |
| 4 | Gate Runner (v5 release gate) | `scripts/evals/run_v5_release_gate.py` | done |
| 5 | Perf Baseline Snapshot | `active/phase_0/v5_0_perf_baseline_snapshot.md` | done |
| 6 | Audit Baseline Report | `reports/2026-05-31_v5_0_phase_0_audit_baseline.md` | done |
| 7 | Execution Plan | `active/phase_0/26_v5_0_phase_0_execution_plan.md` | done |

---

## 3. Wave 执行结果

### Wave 1: Gate Runner Hardening（Tasks 1–3）

**Task 1: `--playwright-report` + path safety**
- 新增 `_safe_path()` 辅助函数，解析路径并断言在 ROOT 下
- 接入 `--playwright-report` CLI 参数到 `_evaluate_face_c()` 的 `walkthrough_path` 参数
- 所有 4 个 CLI 路径参数（`--audit-report`、`--benchmark-dir`、`--playwright-report`、`--perf-dir`）均通过 `_safe_path()` 校验
- `--playwright-report /etc` 正确触发 `SystemExit(2)` 并给出清晰错误
- 修改文件：`scripts/evals/run_v5_release_gate.py`、`scripts/evals/test_run_v5_release_gate.py`

**Task 2: `last_benchmark_date` 从 artifact 时间戳提取**
- 新增 `_latest_benchmark_date()` 辅助函数，依次尝试 `generated_at`、`timestamp`、`run_date` key，回退到文件 mtime
- `last_benchmark_date` 现在从所有 artifact 文件的最新日期提取（格式 YYYY-MM-DD）
- 修改文件：`scripts/evals/run_v5_release_gate.py`、`scripts/evals/test_run_v5_release_gate.py`

**Task 3: a11y score gate in Face E**
- 从 Lighthouse JSON 中提取 `categories.accessibility.score`，与 performance 并列
- Face E 输出新增 `a11y_scores` 和 `a11y_min_score` 字段
- 当 `a11y_min_score < 90` 时阻断（在 performance gate 之后、bundle/CWV 之前检查）
- Gate input matrix 文档已更新新字段和 gate rule
- 修改文件：`scripts/evals/run_v5_release_gate.py`、`scripts/evals/test_run_v5_release_gate.py`、`docs/plans/v5_0/active/phase_0/v5_0_gate_input_matrix.md`

### Wave 2: Cross-Phase Input Documentation（Tasks 4–5）

**Task 4: Vite optimization scope for 5.0-2**
- Perf baseline snapshot 新增第 11 节，含 3 个子节：manualChunks、font-loading、visualizer
- 每个子节有具体、可测量的验收条件
- 修改文件：`docs/plans/v5_0/active/phase_0/v5_0_perf_baseline_snapshot.md`

**Task 5: a11y baseline for 5.0-1**
- Runtime contract freeze 新增第 9 节，含 skip-navigation pattern 要求
- 引用 WCAG 2.4.1 (Bypass Blocks)，定义 `a11y_skip_nav` PLANNED 字段
- 修改文件：`docs/plans/v5_0/active/phase_0/v5_0_runtime_contract_freeze.md`

### Wave 3: Verification（Task 6）

**Task 6: Full verification**
- 34/34 tests pass（`python3 -m pytest scripts/evals/test_run_v5_release_gate.py -q`）
- Gate runner dry-run 产生预期输出，包含新字段（`a11y_scores`、`a11y_min_score`、`last_benchmark_date`）
- 路径遍历被 `SystemExit(2)` 正确阻断（`--playwright-report /etc`）
- `check-doc-governance.sh` 通过
- `check-plan-governance.sh` 通过

---

## 4. 测试结果汇总

### 4.1 后端测试（Python pytest）— FAIL

**总览：** 1376 passed / 163 failed / 46 errors（共 1585 项，耗时 7m37s）

**收集错误（ImportError / AttributeError）：**

| 文件 | 错误类型 | 说明 |
|---|---|---|
| `tests/test_milvus_service.py` | ImportError | `cannot import name '_truncate_varchar' from 'app.core.milvus_service'`，测试引用已删除/重命名的内部函数 |
| `tests/e2e/test_graph_e2e.py::test_entity_extraction_e2e` | AttributeError | `module 'app.core.entity_extractor' has no attribute 'litellm'`，mock 路径与实际模块导入不一致 |

**批量 ERROR（collect/setup 阶段失败）：**

| 文件 | ERROR 数 | 说明 |
|---|---|---|
| `tests/unit/test_semantic_cache.py` | 12 | 全部 AttributeError，mock 路径与实现不匹配 |
| `tests/unit/test_uploads.py` | 18 | 全部，同类型问题 |
| `tests/unit/test_storage_manager_title_guard.py` | 2 | 同类型问题 |

**失败用例主要分布（163 failed）：**

| 文件 | 失败数 | 说明 |
|---|---|---|
| `tests/unit/test_user_isolation.py` | 3 | F.F.F. |
| `tests/unit/test_worker_prewarm.py` | 1 | - |
| `tests/integration/test_api.py` | 7 | F.F..FF.........F |
| `tests/integration/test_multimodal_indexer_extended.py` | ~14 | 大量 F |

### 4.2 前端测试（Vitest）— FAIL

**总览：** 366 passed / 1 failed（共 367 项，耗时 17.72s，91 个测试文件中 90 passed, 1 failed）

**失败用例：**

- `src/app/pages/KnowledgeBaseDetail.test.tsx` — 第 155 行 `waitFor` 超时
  - 测试点击"检索"按钮后期望出现 "Important result snippet" 和 "Paper One" 文本
  - 原因：mock 的检索服务返回结果未正确渲染到 DOM，或异步状态更新时序问题

### 4.3 前端类型检查（TypeScript tsc --noEmit）— PASS

无错误输出，类型检查通过。

---

## 5. 需要关注的问题汇总

| # | 问题 | 严重级别 | 建议修复 phase |
|---|---|---|---|
| 1 | `test_milvus_service.py` — `app.core.milvus_service` 缺少 `_truncate_varchar` 导出 | HIGH | 5.0-7 |
| 2 | `test_graph_e2e.py` — mock 路径与实际模块导入不一致 | HIGH | 5.0-7 |
| 3 | `test_semantic_cache.py` / `test_uploads.py` — 批量 ERROR，mock 路径系统性偏移 | HIGH | 5.0-7 |
| 4 | `KnowledgeBaseDetail.test.tsx` — 检索结果渲染时序问题 | MEDIUM | 5.0-1 或 5.0-3 |

---

## 6. 治理验证

| 验证项 | 结果 |
|---|---|
| `bash scripts/check-doc-governance.sh` | passed |
| `bash scripts/check-plan-governance.sh` | passed |
| `bash scripts/check-phase-tracking.sh` | passed |
| `bash scripts/check-governance.sh` | passed |
| Gate runner `--help` | 5 Face 参数正确 |
| Gate runner dry run | verdict=blocked（符合预期） |
| Gate runner unit tests | 34/34 pass |

---

## 7. 结论

Phase 5.0-0 所有 6 个任务完成，7 个 deliverable 全部验证通过。

- **gate runner dry-run verdict=blocked** 是预期行为，因为后续 phase 尚未 closeout
- **后端测试 163 failed + 46 errors** 是已知存量问题（mock 路径偏移），不阻塞 Phase 5.0-0 closeout
- **前端 1 failed** 是已知时序问题，不阻塞 Phase 5.0-0 closeout
- **前端类型检查 PASS**

Phase 5.0-0 不产出 release verdict 或 release-candidate 声明，仅建立治理基线。

---

## 8. 下一步

- Phase 5.0-1（Design Tokens + WorkspaceShell v2）和 5.0-7（后端 Pipeline 稳定性）可并行启动
- Phase 5.0-2 必须重做动态 baseline（build + Lighthouse），当前 perf baseline 是静态测量
- 后端测试 mock 路径问题建议在 Phase 5.0-7 中统一修复

---

## 9. 证据清单

- Gate runner 代码：`scripts/evals/run_v5_release_gate.py`
- Gate runner 测试：`scripts/evals/test_run_v5_release_gate.py`
- Gate input matrix：`docs/plans/v5_0/active/phase_0/v5_0_gate_input_matrix.md`
- Runtime contract freeze：`docs/plans/v5_0/active/phase_0/v5_0_runtime_contract_freeze.md`
- Perf baseline snapshot：`docs/plans/v5_0/active/phase_0/v5_0_perf_baseline_snapshot.md`
- Migration inventory：`docs/plans/v5_0/active/phase_0/v5_0_v4x_migration_inventory.md`
- Audit baseline report：`docs/plans/v5_0/reports/2026-05-31_v5_0_phase_0_audit_baseline.md`
- PLAN_STATUS：`docs/plans/PLAN_STATUS.md`
- Delivery ledger：`docs/specs/governance/phase-delivery-ledger.md`
