# PR #68 后端服务代码审查报告

## 总体评价

PR #68 后端变更涵盖 6 个文件，核心变更为：
1. 新增 `build_phase_j_workflow_bundle` 函数（153 行），将 Phase D real-world validation payload 转换为 Phase J comparative 格式
2. 简化 `message_service.get_messages` 的 session 管理逻辑
3. 修复 `chat.py` 中 session 所有权检查的防御性编程
4. 移除 `main_path_service` 中 multi-paper 的 `local_compare` 分支
5. `compare_service` 的 quality dict 新增 `unsupported_claim_rate` 字段
6. `task_service` 的 retry/cancel 语义改进

整体代码质量较好，新增函数逻辑清晰。但存在几个需要关注的正确性问题。

## 逐文件审查

### 1. `apps/api/app/api/chat.py` (1 行变更)

**变更**：`session.user_id != user_id` -> `getattr(session, "user_id", None) not in (None, user_id)`

**评价**：防御性编程改进，处理 session 对象可能没有 `user_id` 属性的边缘情况。逻辑正确：当 `user_id` 为 None（属性不存在）或与当前用户匹配时放行，否则 403。

**风险**：LOW。`getattr` 的默认值 `None` 与 `not in (None, user_id)` 配合，确保了 session 无 `user_id` 时不被拒绝，这在 session 刚创建但未关联用户时是合理的。

### 2. `apps/api/app/rag_v3/main_path_service.py` (2 行删除)

**变更**：移除了 `_resolve_runtime_execution_mode` 中当 `len(paper_scope) > 1` 时返回 `"local_compare"` 的分支。

**评价**：行为变更 — 多论文 scope 的 `global_review` 请求现在统一降级到 `local_evidence` 而非 `local_compare`。配套测试 `test_rag_trace_contract_keeps_multi_paper_global_review_fallback_as_local_evidence` 验证了新行为。

**风险**：MEDIUM。这是有意的行为变更，但需确认 compare 流程不依赖 `_resolve_runtime_execution_mode` 返回 `"local_compare"` 的路径。从测试覆盖来看，compare 流程有独立的 routing 逻辑，此项变更应无副作用。

### 3. `apps/api/app/services/compare_service.py` (1 行新增)

**变更**：`build_compare_contract` 的 `quality` dict 新增 `"unsupported_claim_rate": truthfulness_report.get("unsupportedClaimRate", 0.0)`。

**评价**：使 quality 指标与 truthfulness_report 保持同步。使用 `.get()` 带默认值，安全。配套测试验证了 `contract.quality["unsupported_claim_rate"] == contract.truthfulness_report["unsupportedClaimRate"]`。

**风险**：LOW。

### 4. `apps/api/app/services/message_service.py` (约 20 行重构)

**变更**：简化 `get_messages` 方法，移除嵌套的 `async with session_context` 逻辑，改为扁平化的 try/except 结构。

**评价**：代码可读性显著提升，从 52 行减少到 42 行。session 管理逻辑不变：有传入 `db` 时使用传入的 session，否则创建新的 `AsyncSessionLocal`。错误处理保留。

**风险**：LOW。纯重构，行为不变。

### 5. `apps/api/app/services/real_world_validation_service.py` (153 行新增)

**变更**：新增 `build_phase_j_workflow_bundle` 函数，将 Phase D validation payload 转换为 Phase J comparative entries。

**评价**：函数结构清晰，职责单一。但存在以下问题（详见发现的问题部分）：
- `citation_coverage` 使用全局 `evidence_reviews` 而非按 case 过滤
- `task_success_state` 可能为空字符串
- operator precedence 虽然正确但可读性不佳

**风险**：MEDIUM。

### 6. `apps/api/app/services/task_service.py` (约 20 行变更)

**变更**：
- `retry_task`：新增清除 `error_message`/`failure_message`、同步 `paper.status = "pending"`
- `cancel_task`：从硬删除改为软取消（`status="cancelled"`），异常类型从 `ValueError` 改为 `RuntimeError`

**评价**：改进合理。软取消保留了审计轨迹，配套测试覆盖了新行为。

**风险**：LOW。

## 发现的问题（按严重程度排序）

### CRITICAL

无。

### HIGH

#### H1: `build_phase_j_workflow_bundle` 中 `citation_coverage` 使用全局 evidence_reviews 而非按 case 过滤

**文件**: `apps/api/app/services/real_world_validation_service.py`, 第 383-390 行

```python
citation_review_hits = [
    review for review in evidence_reviews if review.get("citation_jump_passed") is True
]
citation_coverage = 1.0 if citation_review_hits else 0.0
```

此逻辑在整个 `for case_key, ... in workflow_cases` 循环内，但 `citation_review_hits` 始终遍历**全部** `evidence_reviews`，而非仅当前 case 对应的 reviews。结果是：如果任意一个 review 的 `citation_jump_passed=True`，则**所有** case（read_chat、review、compare）的 `citation_coverage` 都会被设为 1.0。

**影响**：compare case 的 citation_coverage 可能被 read_chat case 的 evidence review 错误地提升到 1.0。

**建议**：按 `required_steps` 过滤 `evidence_reviews`，与 `unsupported_claim_count` 的过滤逻辑保持一致：
```python
case_reviews = [
    review for review in evidence_reviews
    if str(review.get("surface") or "").strip().lower() in {name.lower() for name in required_steps}
    or not review.get("surface")
]
citation_review_hits = [
    review for review in case_reviews if review.get("citation_jump_passed") is True
]
```

### MEDIUM

#### M1: `task_success_state` 可能为空字符串

**文件**: `apps/api/app/services/real_world_validation_service.py`, 第 413 行

```python
task_success_state = "blocked" if blocking_conditions else success_state
```

`success_state` 来自 `str(run.get("success_state") or "").strip()`，当 run 缺少 `success_state` 字段时为空字符串 `""`。此时 `task_success_state` 为空字符串，不是有效的状态值。

**建议**：添加默认值：
```python
task_success_state = "blocked" if blocking_conditions else (success_state or "unknown")
```

#### M2: `build_phase_j_workflow_bundle` 缺少输入验证

**文件**: `apps/api/app/services/real_world_validation_service.py`, 第 310-460 行

函数内部直接操作 `payload.get("runs")` 的数据，没有对输入结构做防御性检查。虽然上游 `summarize_real_world_validation` 会调用 `validate_real_world_payload`，但如果 `build_phase_j_workflow_bundle` 被独立调用（不经过 summarize），则可能因畸形输入产生意外结果。

**建议**：在函数开头添加基本的输入验证，或在文档中明确说明此函数要求 payload 已通过 `validate_real_world_payload` 验证。

#### M3: `unsupported_claim_count` 过滤逻辑中 `or` 的 operator precedence 可读性差

**文件**: `apps/api/app/services/real_world_validation_service.py`, 第 364-375 行

```python
unsupported_claim_count = sum(
    int(review.get("unsupported_claim_count") or 0)
    for review in evidence_reviews
    if str(review.get("surface") or "").strip().lower() in {name.lower() for name in required_steps}
    or not review.get("surface")
)
```

Python 中 `or` 的优先级低于 `in`，所以实际解析为 `(A in B) or (not C)`，逻辑正确。但缺少括号使阅读者容易误读为 `A in (B or not C)`。

**建议**：添加显式括号提升可读性：
```python
if (str(review.get("surface") or "").strip().lower() in {name.lower() for name in required_steps}
    or not review.get("surface")):
```

### LOW

#### L1: `cost_estimate` 估算公式 `latency_ms / 1000000.0` 的合理性存疑

**文件**: `apps/api/app/services/real_world_validation_service.py`, 第 409-411 行

```python
if cost_estimate == 0.0 and task_latency_ms > 0:
    cost_estimate = round(task_latency_ms / 1000000.0, 6)
```

将延迟（毫秒）除以 100 万作为成本估算。对于 1500ms 的延迟，得到 0.0015 作为 cost_estimate。这个换算系数的依据不明确，建议添加注释说明此估算的来源和假设。

#### L2: `cancel_task` 异常类型从 `ValueError` 改为 `RuntimeError`

**文件**: `apps/api/app/services/task_service.py`, 第 194 行

这是一个行为变更。如果上游代码（如 API 路由层）通过捕获 `ValueError` 来处理 cancel 失败，改为 `RuntimeError` 可能导致未捕获的异常。

**建议**：确认所有调用 `cancel_task` 的地方都已更新异常捕获类型。

## 测试覆盖评估

| 变更文件 | 对应测试 | 覆盖评价 |
|---------|---------|---------|
| `real_world_validation_service.py` (新增函数) | `test_real_world_validation_service.py::test_build_phase_j_workflow_bundle_exposes_comparative_entries` | 单一用例，缺少多 run/多 case 和边缘情况 |
| `compare_service.py` (新增字段) | `test_phase4_hybrid_compare.py` (新增 2 个断言) | 充分，验证了 quality 与 truthfulness_report 同步 |
| `main_path_service.py` (移除分支) | `test_rag_trace_contract.py::test_rag_trace_contract_keeps_multi_paper_global_review_fallback_as_local_evidence` | 充分，验证了新行为 |
| `task_service.py` (retry/cancel 语义) | `test_services.py` (更新断言) | 充分，覆盖了 retry 清除错误、cancel 软删除、异常类型变更 |
| `chat.py` (防御性 getattr) | `test_chat_persistence_flow.py` (mock session 含 user_id) | 间接覆盖，但缺少 session 无 user_id 的边缘测试 |
| `message_service.py` (重构) | 无新增测试 | 重构不改变行为，现有测试足够 |

**总体测试评价**：测试覆盖基本充分，但 `build_phase_j_workflow_bundle` 建议补充更多用例。

## 建议

1. **优先修复 H1**：`citation_coverage` 的全局过滤问题影响数据正确性，应在合并前修复。
2. **补充 M1**：`task_success_state` 的空字符串防御是低成本高收益的修复。
3. **代码风格 M3**：添加括号可避免后续维护者的误读。
4. **测试覆盖**：`build_phase_j_workflow_bundle` 当前只有一个测试用例，建议补充：
   - 多 run、多 case 的场景
   - 缺少 `success_state` 的边缘情况
   - `citation_coverage` 在不同 case 间的独立性（验证 H1 修复后）
5. **文档**：`build_phase_j_workflow_bundle` 函数应在 docstring 中说明输入前提条件（需先通过 `validate_real_world_payload`）。
