---
owner: product-engineering
status: frozen
version: v5.0
date: 2026-05-31
depends_on:
  - docs/plans/v4_5/active/phase_0/v4_5_runtime_contract_freeze.md
  - apps/api/app/services/phase6_runtime_service.py
  - apps/api/app/rag_v3/schemas.py
  - apps/api/app/services/truthfulness_service.py
  - apps/api/app/services/evidence_action_service.py
  - docs/specs/architecture/api-contract.md
  - docs/plans/v5_0/active/overview/27_v5_0_overview_plan.md
supersedes: v4_5_runtime_contract_freeze.md
---

# v5.0 Runtime Contract Freeze

## 1. 目的与范围

本文件冻结 v5.0 所有 phase 必须共享的 runtime contract，作为 RAG / Chat / Compare / Review 四条后端路径与前端 SSE 消费的**唯一真源**。它是 v4.5 contract 的严格超集：完整继承 `phase6_runtime_service.py` 已暴露的全部字段，并为 Phase 5.0-8 的 RAPTOR-lite、Graph synthesis、Verifier fusion 三项 RAG SOTA 能力预留字段。所有 v5.0 phase 的实现必须与本文件保持一致；字段语义若有变更，须先修改本文件并记录变更原因。

---

## 2. 继承自 v4.5 的字段

以下字段由 `build_phase6_runtime_contract()` 生成，是 v5.0 所有路径的**必须字段基线**。所有路径在任何情况下都必须输出这些字段，即使某些字段值为空列表或零。

### 2.1 答案状态字段

- `answer_mode` — 本次答案的完整度判断：`"full" | "partial" | "abstain"`
- `confidence_level` — 综合置信等级：`"high-confidence" | "medium-confidence" | "low-confidence"`
- `degraded` — 本次回答路径是否出现降级：`boolean`
- `degraded_reasons` — 触发降级的具体原因列表：`string[]`，可能条目包括 `"weak_first_pass_retrieval"` / `"corrective_retrieval_triggered"` / `"fallback_used"` / `"claim_verification_failed"` / `"partial_answer"` / `"insufficient_evidence"`

### 2.2 检索与修正字段

- `corrective_retrieval_used` — 是否触发了迭代式修正检索：`boolean`
- `corrective_actions` — 修正检索所采用的行动类型列表：`string[]`，例如 `"query_rewrite"` / `"citation_expansion"` / `"summary_fallback"`
- `fallback_used` — 是否使用了 fallback 路径：`boolean`
- `fallback_events` — 触发 fallback 的事件列表：`string[]`

### 2.3 可信度与声称验证字段

- `unsupported_claim_count` — 本次答案中未被证据支持的声称数量：`number`（非负整数）
- `recovery_outcome` — 降级后的恢复结果：`"not_needed" | "recovered" | "partial" | "failed"`
- `silent_fallback` — fallback 已发生但未被前端显式感知（无 recovery_actions 且无 next_step_entry）：`boolean`

### 2.4 RAPTOR-lite 信号字段（继承自 v4.5 雏形）

- `raptor_lite_used` — 本次检索是否使用了 RAPTOR-lite 相关层级：`boolean`
- `raptor_lite_signals` — 具体信号列表：`string[]`，可能条目：`"paper_summary_index"` / `"section_summary_recall"` / `"deep_retrieval_plan"`

### 2.5 Review Graph 证据字段（继承自 v4.5 雏形）

- `review_global_evidence_used` — 是否使用了 graph-assisted 全局证据：`boolean`
- `review_global_evidence` — 全局证据详情对象或 `null`，结构如下：
  - `graph_assist_used: boolean`
  - `storm_lite_used: boolean`
  - `themes: string[]`
  - `candidate_papers: string[]`
  - `section_seed_titles: string[]`
  - `section_seed_perspectives: string[]`
  - `comparative_section_count: number`

### 2.6 导航与用户操作字段

- `next_step_entry` — 后端建议的下一步操作入口（可为 `null`）：`object | null`，由 `open_recovery_entry` action 的 params 填充

### 2.7 可观测性基线字段（来自 AnswerContract）

- `trace_id` — 本次请求的分布式追踪 ID：`string`（可为空字符串，但不可缺失键）
- `run_id` — 本次 RAG pipeline 运行 ID：`string`（可为空字符串，但不可缺失键）

### 2.8 答案元字段（来自 AnswerContract）

- `response_type` — 本次响应的类型：`"general" | "rag" | "compare" | "review" | "reading" | "abstain" | "error"`
- `task_family` — 任务族标识：`string`
- `execution_mode` — 执行模式：`string`
- `truthfulness_required` — 本次是否触发了 truthfulness 验证：`boolean`
- `truthfulness_summary` — truthfulness 验证摘要对象（未触发时为 `{}`）：`object`，关键子字段：
  - `total_claims: number`
  - `supported_claims: number`
  - `weakly_supported_claims: number`
  - `partially_supported_claims: number`
  - `unsupported_claims: number`
  - `unsupported_claim_rate: number`（`0.0–1.0`）
  - `answer_mode: string`
  - `verifier_backend: string`
- `truthfulness_report` — 完整 truthfulness 验证报告（未触发时为 `{}`）：`object`
- `retrieval_plane_policy` — 检索层策略（未使用时为 `{}`）：`object`
- `degraded_conditions` — 降级条件列表（与 `degraded_reasons` 同源，由 AnswerContract 单独维护）：`string[]`
- `recovery_actions` — 后端建议的恢复动作列表：`object[]`，每项包含 `action / status / scope / reason / params`

### 2.9 内容字段（来自 AnswerContract）

- `answer` — 最终答案文本：`string`（abstain 时可为空字符串）
- `claims` — 声称列表（含 support_status）：`AnswerClaim[]`
- `unsupported_claims` — 未支持声称文本列表：`string[]`
- `missing_evidence` — 缺失证据描述列表：`string[]`
- `citations` — 引用列表：`AnswerCitation[]`
- `evidence_blocks` — 证据块列表：`EvidenceBlock[]`
- `quality` — 质量评分对象：`object`（含 answerability / paper_coverage_score 等）
- `compare_matrix` — 多论文对比矩阵（仅 compare 路径）：`CompareMatrix | null`

---

## 3. v5.0 新增字段

> **PLANNED — 以下字段在 Phase 5.0-8 之前不落代码，仅在本 contract 中冻结语义和类型。**
> **Phase 5.0-0 ~ 5.0-7 输出对象中这些键不必出现（或以 `null` 填充）。**
> **Phase 5.0-8 开始，标注 `[5.0-8 REQUIRED]` 的字段必须真实填充。**

### 3.1 RAPTOR-lite 深度字段

- `retrieval_tree_depth` — 本次检索实际遍历的摘要树层深：`number | null`
  - 取值域：非负整数，0 表示未使用树结构，1 = 论文级摘要，2 = 节区级摘要，3+ = 深层递归
  - 何时出现：RAPTOR-lite 激活时（`raptor_lite_used === true`）
  - 何时缺失：`raptor_lite_used === false` 时为 `null`
  - **[5.0-8 REQUIRED]** when `raptor_lite_used === true`

- `tree_level_used` — 实际贡献最终答案的摘要树层级（层级号）：`number | null`
  - 取值域与 `retrieval_tree_depth` 相同，但表示**最终采用**的层级，可 ≤ `retrieval_tree_depth`
  - 何时出现：同 `retrieval_tree_depth`
  - 何时缺失：`null`

- `aggregated_summary_chunk_ids` — 在树级聚合中实际参与综合的 chunk ID 列表：`string[] | null`
  - 取值域：source_chunk_id 字符串列表，空列表合法
  - 何时出现：`retrieval_tree_depth >= 1` 时
  - 何时缺失：`null`

### 3.2 Graph synthesis 字段

- `community_id_used` — 本次 review 生成使用的 graph community ID：`string | null`
  - 取值域：uuid 字符串 或 `null`
  - 何时出现：`graph_synthesis_mode !== "none"` 时
  - 何时缺失：`null`

- `community_summary_source` — community summary 的来源路径描述：`string | null`
  - 取值域：枚举字符串，如 `"neo4j_community_cache"` / `"on_the_fly_extraction"` / `"storm_lite_draft"`
  - 何时出现：`community_id_used` 非空时
  - 何时缺失：`null`

- `graph_synthesis_mode` — graph 合成模式：`"none" | "review_only"`
  - 取值域：固定为两值之一；v5.0 不扩展到 KB chat 主链（见 5.0-8 设计约束）
  - 何时出现：**始终出现**（Phase 5.0-8 前默认为 `"none"`）
  - 何时缺失：不允许缺失

### 3.3 Verifier fusion 字段

- `verifier_pipeline` — 本次验证使用的 verifier 列表（有序）：`Array<"claim" | "citation" | "claim_evidence" | "nli"> | null`
  - 取值域：上述四个 verifier 的任意子集（有序），空数组合法
  - 何时出现：`truthfulness_required === true` 时
  - 何时缺失：`truthfulness_required === false` 时为 `null`
  - **[5.0-8 REQUIRED]** when `truthfulness_required === true`

- `verifier_consensus_score` — 多 verifier 共识得分（0.0–1.0），取参与 verifier 的加权平均 support_score：`number | null`
  - 取值域：`0.0–1.0`，精度 4 位小数
  - 何时出现：`verifier_pipeline` 长度 ≥ 2 时
  - 何时缺失：单 verifier 或未触发验证时为 `null`

- `verifier_disagreement_flag` — 不同 verifier 对同一声称的判断出现分歧（support_status 不一致）：`boolean | null`
  - 何时出现：`verifier_pipeline` 长度 ≥ 2 时
  - 何时缺失：`null`

### 3.4 全链可观测性强一致字段

- `compare_matrix_id` — 本次 compare 请求生成的矩阵 ID（用于前端去重与缓存对齐）：`string | null`
  - 取值域：uuid 字符串
  - 何时出现：`response_type === "compare"` 且矩阵已成功生成时
  - 何时缺失：`null`

> **全链强一致要求（Phase 5.0-7 起执行）：**
> `trace_id` / `run_id` / `compare_matrix_id` 三字段必须在同一请求的所有 SSE 事件帧与最终响应中保持相同值。后端禁止在 SSE 流中途更换 `run_id`。前端必须以首帧 `trace_id` 作为本次交互的幂等键。

---

## 4. 字段语义细则

### `answer_mode`

- **Type:** `"full" | "partial" | "abstain"`
- **必填性:** 必填，所有路径，任何情况下不可缺失
- **取值域:** 三值枚举
- **何时出现:** 始终
- **语义:** `"full"` — 所有声称均有证据支持；`"partial"` — 部分声称有支持，至少一条 unsupported；`"abstain"` — 证据不足，后端主动放弃生成实质答案

### `confidence_level`

- **Type:** `"high-confidence" | "medium-confidence" | "low-confidence"`
- **必填性:** 必填
- **取值域:** 三值枚举，由 `_phase6_confidence_level()` 确定性推导，前端不允许重新计算
- **何时出现:** 始终
- **何时为 `"low-confidence"`:** `answer_mode === "abstain"`，或 `fallback_used` 且无 recovery，或存在 unsupported claims 且 `answer_mode !== "full"`

### `degraded` / `degraded_reasons`

- **Type:** `boolean` / `string[]`
- **必填性:** 必填
- **何时为 `true`:** `degraded_reasons` 非空、`fallback_used`、`retrieval_evaluator.is_weak`、`answer_mode` 为 `"partial"` 或 `"abstain"` 任一条件成立
- **前端语义:** `degraded === true` 时必须显示降级指示器；不允许静默忽略

### `recovery_outcome`

- **Type:** `"not_needed" | "recovered" | "partial" | "failed"`
- **必填性:** 必填
- **映射规则:** `!degraded → "not_needed"`；`degraded && answer_mode === "full" → "recovered"`；`answer_mode === "partial" → "partial"`；其余 → `"failed"`

### `silent_fallback`

- **Type:** `boolean`
- **必填性:** 必填
- **语义:** `true` 表示 fallback 已发生但前端无法感知（无 recovery_actions 且 next_step_entry 为 null）。前端在收到 `silent_fallback === true` 时必须记录诊断日志，不允许无声呈现为正常答案。

### `trace_id` / `run_id`

- **Type:** `string`（UUID v4，非空时格式为 `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`）
- **必填性:** 键必须始终出现，值可为空字符串（Phase 5.0-0 ~ 5.0-6）；Phase 5.0-7 起值必须非空
- **全链强一致:** 同一请求的所有 SSE 帧和最终响应中值相同

### `graph_synthesis_mode`

- **Type:** `"none" | "review_only"`
- **必填性:** 必填（Phase 5.0-8 前固定为 `"none"`）
- **约束:** v5.0 不允许取值 `"kb_chat"` 或任何其他值；Graph synthesis 不进 KB chat 主链

### `verifier_pipeline`

- **Type:** `Array<"claim" | "citation" | "claim_evidence" | "nli"> | null`
- **必填性:** `truthfulness_required === true` 时必填，Phase 5.0-8 之前可为 `null`
- **顺序语义:** 列表顺序反映执行顺序，前端可用于展示 pipeline 进度

---

## 5. 前端消费契约

前端在处理所有 RAG / Chat / Compare / Review 响应时，必须遵守以下规则：

1. **降级显示（必须）：** `degraded === true` 时，在答案卡片或消息气泡附近显示降级指示器（如黄色提示条或 badge），不允许静默丢弃。
2. **置信度着色（必须）：** 根据 `confidence_level` 对答案容器做视觉区分；`"low-confidence"` 时显示警告色，不允许与 `"high-confidence"` 使用同色方案。
3. **abstain 态渲染（必须）：** `answer_mode === "abstain"` 时，渲染"证据不足"占位状态，禁止渲染空字符串。
4. **recovery_actions 展示（必须）：** `recovery_actions` 非空时，至少在 UI 中提供一个入口（如"查看建议"折叠项）；优先级 `required > recommended > available`。
5. **silent_fallback 日志（必须）：** `silent_fallback === true` 时，前端须向 observability 层写入诊断事件，不允许无声呈现。
6. **trace_id 锚定（必须）：** 首个 SSE 帧中的 `trace_id` 作为本次交互的幂等键，后续重试或轮询以此键去重。
7. **新字段 null 容忍（必须，Phase 5.0-8 前）：** `retrieval_tree_depth` / `community_id_used` / `verifier_pipeline` 等新增字段在 Phase 5.0-8 前可为 `null`，前端不允许因这些字段为 `null` 而崩溃或报错。
8. **compare_matrix_id 去重（必须，Phase 5.0-7 起）：** 收到相同 `compare_matrix_id` 的响应时，前端不允许重复渲染矩阵，应更新已有矩阵而非追加。
9. **graph_synthesis_mode 展示（可选）：** `"review_only"` 时可在 review draft 标题区域展示"Graph 辅助"badge，`"none"` 时不展示。

---

## 6. 后端实现契约

后端在所有路径中必须遵守以下规则：

1. **`build_phase6_runtime_contract()` 是唯一入口：** 所有路径的 runtime contract 字段必须经由此函数或其 v5.0 升级版生成，禁止手动拼接。
2. **全路径覆盖（必须）：** `POST /api/v1/chat`、`POST /api/v1/search/evidence`、`POST /api/v1/queries/query`、`POST /api/v1/compare/v4`、`POST /api/v1/knowledge-bases/{kb_id}/query` 五条路径均必须在响应中包含完整的第 2 节字段集合。
3. **`trace_id` 生成时机：** 在请求进入 API handler 时立即生成，在 SSE 首帧中发出，后续帧不允许重新生成。
4. **`run_id` 生命周期：** 单次 RAG pipeline 运行唯一，跨 corrective retrieval 迭代保持不变。
5. **`degraded_reasons` 去重：** 使用 `_dedupe_strings()` 确保无重复条目，顺序反映触发时序。
6. **新字段空值规范（Phase 5.0-8 前）：** 第 3 节中所有 `PLANNED` 字段在 Phase 5.0-8 前输出时必须为 `null` 或缺失，不允许输出随机值或占位字符串。
7. **`graph_synthesis_mode` 默认值：** Phase 5.0-8 前所有路径必须输出 `"none"`，不允许省略此键（因为前端依赖此键判断是否展示 Graph badge）。
8. **truthfulness_summary 结构稳定：** `truthfulness_summary` 的子字段结构（见第 2.8 节）冻结，`verifier_backend` 字段必须存在且非空（可选值如 `"lexical_overlap"` / `"lexical_abstain_guard"` / `"fallback_unstructured_answer"` / `"nli_entailment"`）。

---

## 7. 兼容性策略

| 字段组 | Phase 5.0-0 ~ 5.0-6 | Phase 5.0-7 | Phase 5.0-8 |
|---|---|---|---|
| 第 2 节全部字段（继承自 v4.5） | **必须输出** | **必须输出** | **必须输出** |
| `trace_id` / `run_id` | 可为空字符串 | 必须非空 UUID | 必须非空 UUID |
| `compare_matrix_id` | 不要求 | 必须非空（compare 路径） | 必须非空（compare 路径） |
| `graph_synthesis_mode` | 必须为 `"none"` | 必须为 `"none"` | `"none"` 或 `"review_only"` |
| RAPTOR-lite 新字段 | `null` | `null` | **部分 REQUIRED**（见第 3.1 节标注） |
| Graph synthesis 新字段 | `null` | `null` | **部分 REQUIRED**（见第 3.2 节标注） |
| Verifier fusion 新字段 | `null` | `null` | **部分 REQUIRED**（见第 3.3 节标注） |

**兼容升级原则：** 新字段以 `null` 进入，通过 Phase 迁移逐步变为必填，永远不强删现有字段。前端必须对所有 `null` 值做容错处理。

---

## 8. 冻结范围与不冻结范围

### 冻结范围（IN）

- 所有第 2 节字段的**键名、类型、必填性、枚举值域**
- 所有第 3 节字段的**键名、类型、取值域语义**（值可为 null 直到对应 phase）
- `build_phase6_runtime_contract()` 函数的**输出键集合**（不允许删减已有键）
- `truthfulness_summary` 的**子字段结构**
- `review_global_evidence` 的**子字段结构**
- 前端消费规则（第 5 节），作为 UI 实现的最低合规基线
- 后端全路径覆盖要求（第 6 节第 2 条）

### 不冻结范围（OUT）

- `build_phase6_runtime_contract()` 的**内部推导逻辑**（可在 Phase 5.0-8 重构，但输出键集合必须超集兼容）
- `retrieval_evaluator` / `retrieval_diagnostics` 的**内部结构**（属于检索层内部契约，不在本文件约束范围）
- `quality` 对象的**具体子字段**（由各路径自行扩展，本文件不约束）
- `recovery_actions` 的**具体 action 字符串值**（可在不同 phase 按需添加新值）
- `verifier_backend` 的**具体取值字符串**（可随 verifier 升级扩展）
- RAPTOR-lite 内部摘要树的**构建算法和分层策略**（属于 5.0-8 内部实现）
- Graph synthesis 的**社区检测算法选型**（属于 5.0-8 内部实现）
- NLI 模型的**具体选型和阈值**（属于 5.0-8 内部实现）

---

## 9. 5.0-1 Input: Accessibility Baseline Requirements

> 本节为 Phase 5.0-1（设计系统 v2）提供无障碍基线要求。所有 5.0-1 及后续 phase
> 的前端实现必须满足以下最低标准。

### 9.1 Skip-Navigation Pattern

**WCAG 2.4.1 Bypass Blocks (Level A)**: 页面提供一种跳过重复内容块的机制。

**实现要求**:

1. `WorkspaceShell` 组件中，**第一个可聚焦元素**必须是一个 visually hidden 的
   "Skip to content" 链接（`<a href="#main-content">`）。
2. 该链接在获得焦点时必须变为可见（`focus:visible` 样式），位于左上角。
3. 目标锚点 `id="main-content"` 必须设置在主内容区域的容器元素上。
4. Tab 顺序验证：首次 Tab 必须命中 skip link，而非侧边栏导航。

**实现参考**:

```tsx
// apps/web/src/components/layout/WorkspaceShell.tsx
<a
  href="#main-content"
  className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2
             focus:z-50 focus:rounded focus:bg-primary focus:px-4 focus:py-2
             focus:text-primary-foreground focus:outline-none focus:ring-2
             focus:ring-ring"
>
  Skip to content
</a>
```

### 9.2 Contract Field Addition

在本文件第 3 节（v5.0 新增字段）中追加以下 PLANNED 字段：

| 字段名 | 类型 | 说明 | introduced_in |
|---|---|---|---|
| `a11y_skip_nav` | `boolean` | 前端是否已实现 skip-navigation pattern | phase_5.0-1 |

**Phase 5.0-0 ~ 5.0-0**: 该字段不要求出现。
**Phase 5.0-1 起**: 前端在 `WorkspaceShell` 中实现 skip link 后，该字段设为 `true`。

### 9.3 5.0-9 Release Gate 关联

Face E（Perf）的 Lighthouse audit 中，"Bypass Blocks" 审计项（`bypass-blocks`）
必须为 pass。该审计项与 `a11y_min_score >= 90` 的 gate 规则协同工作。
