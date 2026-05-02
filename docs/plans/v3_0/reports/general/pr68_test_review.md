# PR #68 后端测试代码审查报告

**审查日期**: 2026-05-02
**审查范围**: apps/api/tests/ 目录下 PR #68 涉及的测试变更
**审查维度**: 测试充分性、测试隔离、命名清晰度、边界覆盖、重复/冗余、与实现对应

---

## 变更概览

| 文件 | 变更量 | 类型 |
|------|--------|------|
| test_phase_j_comparative_gate.py | +132/-77 | 大幅重写 |
| test_rag_trace_contract.py | +43 | 新增测试 |
| test_real_world_validation_service.py | +35 | 新增测试 |
| test_chat_persistence_flow.py | +12/-2 | 小幅修改 |
| test_services.py | +20/-10 | 中等修改 |
| test_phase4_hybrid_compare.py | +2 | 微调 |

---

## 逐文件审查

### 1. test_phase_j_comparative_gate.py

**评分: 8/10 -- 良好**

**优点:**
- 提取 `_entry()` 工厂函数消除大量重复的测试数据构造，代码可读性显著提升
- 覆盖全部 4 种 verdict 级别: PASS、FAIL、WARN、EXPERIMENT_ONLY
- 使用导入的常量 (`VERDICT_PASS` 等) 而非硬编码字符串/布尔值，与实现同步
- 新增 `test_phase_j_comparative_gate_warns_on_budget_regressions` 混合 academic + workflow 条目
- 新增 `test_render_markdown_summary_includes_closeout_sections` 验证新函数
- 断言精确到具体的 failure/warning reason 字符串

**问题:**

| 级别 | 问题 | 说明 |
|------|------|------|
| MEDIUM | 缺少 `case_source="academic_blind"` 覆盖 | `CASE_SOURCES` 定义了 3 种来源 (`academic_public`, `academic_blind`, `workflow`)，但 `_entry()` 默认只生成 `academic_public`，无测试覆盖 `academic_blind` 路径 |
| LOW | 缺少 `dataset_version_mismatch` 失败路径测试 | `compare_runs` 中有 `dataset_version_mismatch` 检查，但无对应测试 |
| LOW | 缺少 `workflow_success_regression` 警告路径测试 | 实现中有此 warning 分支，测试未覆盖 |
| LOW | `test_render_markdown_summary` 仅检查标题存在 | 未验证具体指标值是否出现在 markdown 中，断言过于宽松 |
| LOW | 缺少空输入边界测试 | 无测试覆盖 `entries=[]` 的 summarize_run 行为 |

### 2. test_rag_trace_contract.py

**评分: 7/10 -- 良好**

**优点:**
- 新测试 `test_rag_trace_contract_keeps_multi_paper_global_review_fallback_as_local_evidence` 精确验证了实现变更 (移除 `local_compare` 分支)
- 验证 `paper_scope` 多论文场景下仍降级到 `local_evidence`
- 断言覆盖 `execution_mode`、`retrieval_plane_policy`、`degraded_conditions` 三个关键字段

**问题:**

| 级别 | 问题 | 说明 |
|------|------|------|
| LOW | 内联 `__import__` 模式可读性差 | 现有测试已采用此模式 (一致性OK)，但建议后续重构为 fixture |
| LOW | 测试与现有 survey 测试高度相似 | 仅多了 `paper_scope` 参数和第二个 candidate，可考虑参数化 |

### 3. test_real_world_validation_service.py

**评分: 6/10 -- 一般**

**优点:**
- 测试新函数 `build_phase_j_workflow_bundle` 的核心路径
- 验证 bundle 类型、dataset_version、条目数、case_source、runtime_truth、latency、degraded_conditions
- 复用已有的 `_sample` 和 `_run` 辅助函数

**问题:**

| 级别 | 问题 | 说明 |
|------|------|------|
| HIGH | 只有 1 个测试覆盖 `build_phase_j_workflow_bundle` | 缺少关键边界: 空 runs、无 workflow_steps、无 runtime_truth、无 latency_ms、blocking bucket、success_state 变体 |
| MEDIUM | `assert len(bundle["entries"]) == 2` 缺乏解释 | 测试期望 2 个条目 (read_chat + review)，但未显式验证条目的 task_family 分布 |
| LOW | 未测试 `dataset_version` 回退逻辑 | 实现支持从 `schema_version` 回退获取 version，但测试未覆盖此路径 |

### 4. test_chat_persistence_flow.py

**评分: 8/10 -- 良好**

**优点:**
- 新增 `_create_assistant_message` 和 `_safe_update_assistant_message` 的 mock 和断言
- 修复 `get_session` mock 补充 `user_id` 字段，与实现变更同步
- 测试间隔离良好，每个测试独立 mock

**问题:**

| 级别 | 问题 | 说明 |
|------|------|------|
| LOW | 仅验证 `assert_awaited()` 未验证参数 | `_create_assistant_message` 和 `_safe_update_assistant_message` 被调用了，但未断言传入参数是否正确 |

### 5. test_services.py

**评分: 7/10 -- 良好**

**优点:**
- `mock_task` fixture 补充了 `is_retryable` 和 `paper` 属性
- `test_retry_task_resets_status` 显式设置 `mock_task.status = "failed"`
- `test_cancel_task_for_pending` 断言扩展到 `status`、`cancellation_reason`、`paper.status`
- 错误类型从 `ValueError` 改为 `RuntimeError` 与实现同步

**问题:**

| 级别 | 问题 | 说明 |
|------|------|------|
| MEDIUM | `test_cancel_task_for_pending` 未验证无硬删除 | 实现从 delete 改为 flush (软删除)，但测试未断言 `mock_db.delete` 未被调用 |
| MEDIUM | `test_retry_task_resets_status` 断言 `error_message is None` | MagicMock 属性默认返回 MagicMock (truthy)，如果实现未显式清空此字段，断言会失败。需确认实现确实设置了 `None` |
| LOW | `test_cancel_task_fails_for_non_pending` 仅测 "completed" | "processing" 状态同样不可取消，建议覆盖 |

### 6. test_phase4_hybrid_compare.py

**评分: 9/10 -- 优秀**

**优点:**
- 新增 2 个精确的契约断言:
  - `quality["unsupported_claim_rate"] == truthfulness_report["unsupportedClaimRate"]`
  - `quality["citation_coverage"] == truthfulness_summary["citation_coverage"]`
- 直接验证 compare_service 实现变更中新增的字段映射

**问题:**

| 级别 | 问题 | 说明 |
|------|------|------|
| 无 | -- | 变更精准且与实现同步 |

---

## 跨文件问题汇总

### 1. 测试覆盖缺口 (MEDIUM)

以下实现路径在测试中未被覆盖:

- `build_phase_j_workflow_bundle` 的边界条件 (空输入、缺失字段)
- `compare_runs` 的 `dataset_version_mismatch` 和 `workflow_success_regression` 路径
- `case_source="academic_blind"` 的归一化路径

### 2. Mock 深度问题 (LOW)

`test_services.py` 中 TaskService 测试通过 `patch.object(TaskService, 'get_task')` mock 了整个 get_task，导致 retry/cancel 的实际实现逻辑未被真正执行。测试仅验证 mock 对象的属性赋值，而非服务层真实行为。

### 3. 测试命名一致性 (LOW)

- 新测试命名风格一致，使用 `test_<功能>_<条件>_<预期结果>` 模式
- 旧测试 (如 `test_rag_trace_contract`) 命名较简短，但保持向后兼容可以接受

---

## 建议优先修复项

1. **[HIGH]** 为 `build_phase_j_workflow_bundle` 补充边界测试 (空 runs、缺失 runtime_truth、blocking bucket)
2. **[MEDIUM]** 为 `compare_runs` 补充 `dataset_version_mismatch` 和 `workflow_success_regression` 测试
3. **[MEDIUM]** `test_cancel_task_for_pending` 增加 `mock_db.delete.assert_not_called()` 断言
4. **[LOW]** 考虑为 `case_source="academic_blind"` 添加一条测试路径

---

## 总体评价

PR #68 的后端测试变更整体质量**良好**。主要亮点是 `test_phase_j_comparative_gate.py` 的重写显著提升了可读性和覆盖范围，`test_rag_trace_contract.py` 和 `test_phase4_hybrid_compare.py` 的新增断言与实现变更精确同步。

主要风险点是 `build_phase_j_workflow_bundle` 仅有 1 个 happy-path 测试，缺少边界覆盖，建议在合并前补充。
