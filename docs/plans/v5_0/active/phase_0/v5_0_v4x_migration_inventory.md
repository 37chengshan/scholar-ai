---
owner: product-engineering
status: draft
depends_on:
  - 27_v5_0_overview_plan.md
  - docs/plans/PLAN_STATUS.md
  - docs/specs/governance/phase-delivery-ledger.md
  - 22_v4_0_phase_3_execution_plan.md
  - 24_v4_0_phase_5_execution_plan.md
  - 25_v4_0_phase_7_execution_plan.md
  - 2026-05-26_v4_5_frontend_backend_multidimensional_audit.md
  - 2026-05-27_v4_5_rag_drift_recheck.md
last_verified_at: 2026-05-31
evidence_commits:
  - working-tree-v5-0-kickoff
---

# v5.0 v4.x Migration Inventory

> 日期: 2026-05-31
> 状态: draft
> 上游: `docs/plans/v5_0/active/overview/27_v5_0_overview_plan.md` 第 3 节

## 0. 文档作用

本文档是 v4.x 所有未 closeout 工作向 v5.0 phase 的逐项映射真源。任何 v4.x 残留工作必须出现在本文档中，要么映射到 v5.0 某个 phase，要么明确标 `superseded`。

## 1. 逐项映射总表

| v4.x 残留 ID | 来源 phase | 残留内容 (一句话) | 迁入 v5.0 phase | 处置 | 优先级 |
|---|---|---|---|---|---|
| V4-P3-WP1 | v4.0-3 | Artifact Contract Freeze 未落代码 | 5.0-5 + 5.0-6 | 迁入 | P1 |
| V4-P3-WP2 | v4.0-3 | Citation Audit and Claim Repair 未落代码 | 5.0-6 | 迁入 | P1 |
| V4-P3-WP3 | v4.0-3 | Evidence Note Productization 未落代码 | 5.0-5 | 迁入 | P1 |
| V4-P3-WP4 | v4.0-3 | Compare Matrix as Artifact 未落代码 | 5.0-6 | 迁入 | P2 |
| V4-P3-WP5 | v4.0-3 | Known Limitations and Return Path 未落代码 | 5.0-5 + 5.0-6 | 迁入 | P2 |
| V4-P3-WP6 | v4.0-3 | Phase 3 Closeout 未执行 | 5.0-9 | 迁入 | P1 |
| V4-P5-P1 | v4.0-5 | Search/Compare/Review stale/pending/responsive 语义 | 5.0-1 + 5.0-2 | 迁入 | P1 |
| V4-P5-P2 | v4.0-5 | Read/Notes/Chat handoff 焦点落点与恢复动作 | 5.0-4 + 5.0-5 | 迁入 | P2 |
| V4-P5-P3 | v4.0-5 | coarse pointer / reduced motion walkthrough | 5.0-2 | 迁入 | P2 |
| V4-P5-P4 | v4.0-5 | 前端交互专项测试与浏览器级验证 | 5.0-9 | 迁入 | P2 |
| V4-P7-GATE | v4.0-7 | gate runner 已存在但 verdict=blocked | 5.0-9 | 升级 | P1 |
| V4-AUD-P1-AUTH | v4.5 audit | Auth/Ownership P1 已修但需进一步加固 | 5.0-7 | 加固 | P1 |
| V4-AUD-P1-TASK | v4.5 audit | 上传/导入/任务 P1 已修但需集成验证 | 5.0-7 | 加固 | P1 |
| V4-AUD-P1-DATA | v4.5 audit | Milvus/向量数据 P1 已修但需集成验证 | 5.0-7 | 加固 | P1 |
| V4-AUD-P1-FE | v4.5 audit | 前端契约/状态 P1 已修但需回归测试 | 5.0-2 + 5.0-3 | 加固 | P1 |
| V4-AUD-P1-GOV | v4.5 audit | 治理/runtime hygiene P1 已修但需持续验证 | 5.0-0 + 5.0-7 | 加固 | P2 |
| V4-RAG-DRIFT | v4.5 recheck | RAG drift 4 红点已消除 | — | done | — |
| V4-P0-CLOSE | v4.5 phase_0 | bridge phase_0 已 closeout | — | done | — |
| V4-5-DIR | v5/ directory | v5/ 平行计划 (DU-20260530-001~006) | — | superseded | — |

## 2. 逐条 Detail

### V4-P3-WP1: Artifact Contract Freeze

- **残留代码/文档边界**: `docs/plans/v4_0/active/phase_3/22_v4_0_phase_3_execution_plan.md` WP1 定义了 artifact 类型表、support/coverage/limitation 词汇表，但 PLAN_STATUS 为 `execution-plan-complete / code-and-evidence-required`，未进入代码实现。
- **为什么映射到 5.0-5 + 5.0-6**: artifact contract 的核心承载者是 Notes (evidence note) 和 Chat (citation panel)，5.0-5 Notes 重构需要在新编辑器中落地 evidence note contract，5.0-6 Chat citation panel 需要落地 citation-backed artifact 语义。
- **closeout 条件**: Notes 页 evidence note 可持久化且可回跳；Chat citation panel 可展示 claim/evidence/support 三层语义；contract 文档与代码一致。

### V4-P3-WP2: Citation Audit and Claim Repair

- **残留代码/文档边界**: WP2 定义了 citation audit 结果结构和 claim repair 规则，但未实现。当前 `review_draft_service.py` 已有 `partial` / `insufficient_evidence` 语义，但 claim repair 入口未与 UI 闭环。
- **为什么映射到 5.0-6**: citation audit 和 claim repair 的用户入口在 Chat citation panel 和 Review panel，5.0-6 是 Chat 精修 phase。
- **closeout 条件**: unsupported/weakly supported claim 在 Chat 内有明确 UI 语义和 repair 入口；citation audit 结果可持久化。

### V4-P3-WP3: Evidence Note Productization

- **残留代码/文档边界**: WP3 定义了 `linked_evidence`、note title normalization、source tags 的收束，当前 Notes 页已有基础 `linked_evidence` 字段但未做 artifact 级收束。
- **为什么映射到 5.0-5**: 5.0-5 是 Notes 系统深度重构 phase，evidence note 的 artifact 化与 TipTap 编辑器二次封装同步进行。
- **closeout 条件**: evidence note 有独立 contract；note-to-review / note-to-chat return path 可用；raw claim 不再直接暴露为不受控标题。

### V4-P3-WP4: Compare Matrix as Artifact

- **残留代码/文档边界**: WP4 定义了 `compare_matrix` 作为正式 artifact，当前 `compare_service.py` 已有 `compare_matrix` 输出但未做 artifact 级 return path。
- **为什么映射到 5.0-6**: compare card UI 重做和 Chat↔Notes 集成桥都在 5.0-6。
- **closeout 条件**: compare matrix 具备可回跳证据；compare 不脱离 artifact bundle 单独宣称完成。

### V4-P3-WP5: Known Limitations and Return Path

- **残留代码/文档边界**: WP5 定义了 known limitations 和 run trace / return path，当前 chat handoff 已支持 prefill-only 跳转但 artifact 级 return path 未实现。
- **为什么映射到 5.0-5 + 5.0-6**: return path 的两端分别在 Notes 和 Chat。
- **closeout 条件**: limitation 是 artifact bundle 的组成部分而非附录；用户可从 artifact 回到来源页或 Chat。

### V4-P3-WP6: Phase 3 Closeout

- **残留代码/文档边界**: WP1-WP5 均未执行代码收口，WP6 closeout 自然未执行。
- **为什么映射到 5.0-9**: artifact bundle 的整体验收需要在所有前端精修完成后统一做。
- **closeout 条件**: 5.0-9 consolidated release gate 中包含 artifact bundle 验收项。

### V4-P5-P1: Search/Compare/Review stale/pending/responsive 语义

- **残留代码/文档边界**: `24_v4_0_phase_5_execution_plan.md` P1 定义了 Search/Compare/Review 的 stale/pending/responsive 语义和 Read/Notes/Chat handoff 焦点落点，当前仅完成 P0 切片 (link-first navigation, hover-only 修复, KB 主动作语义化)。
- **为什么映射到 5.0-1 + 5.0-2**: stale/pending/busy 交互语义属于设计系统 v2 (5.0-1) 的状态系统和 WorkspaceShell v2 (5.0-2) 的四态系统化。
- **closeout 条件**: Search/Compare/Review 页面有统一的 stale/pending/busy/error 语义；设计系统 token 覆盖交互状态。

### V4-P5-P2: Read/Notes/Chat handoff 焦点落点

- **残留代码/文档边界**: P2 定义了 handoff 焦点落点与恢复动作，当前 chatHandoff 只做 prefill-only 跳转。
- **为什么映射到 5.0-4 + 5.0-5**: Read 页和 Notes 页的焦点管理分别在 5.0-4 和 5.0-5 中作为 UX 细节处理。
- **closeout 条件**: Read→Notes→Chat 的 handoff 焦点落点在各页面 closeout 中被验证。

### V4-P5-P3: coarse pointer / reduced motion walkthrough

- **残留代码/文档边界**: P3 定义了 reduced motion 降级和 coarse pointer 适配，当前 `WorkspaceShell.tsx` 已有 Reduce Motion 降级基础。
- **为什么映射到 5.0-2**: 5.0-2 是 WorkspaceShell v2 + 响应式 phase，coarse pointer 和 reduced motion 属于 shell 层系统化能力。
- **closeout 条件**: WorkspaceShell 在 reduced motion 和 coarse pointer 场景下有明确降级策略和验证。

### V4-P5-P4: 前端交互专项测试与浏览器级验证

- **残留代码/文档边界**: P4 定义了前端交互专项测试与浏览器级验证，当前未执行。
- **为什么映射到 5.0-9**: 浏览器级验证属于 5.0-9 全链 walkthrough 范畴。
- **closeout 条件**: 5.0-9 的 7 个核心 journey E2E 覆盖了交互验证。

### V4-P7-GATE: gate runner 升级

- **残留代码/文档边界**: `scripts/evals/run_v4_phase7_gate.py` 已存在，当前 verdict=blocked。Phase 7 定义了 7 项 gate checks 和三态 verdict 逻辑。
- **为什么映射到 5.0-9**: 5.0-9 的 consolidated release gate 是 v4.0 phase_7 gate runner 的直接升级，继承其检查结构并扩展为 v5.0 的 8 项 release-pass 门禁。
- **closeout 条件**: `scripts/evals/run_v5_release_gate.py` 可运行且包含 v5.0 全部 8 项 release-pass 条件。

### V4-AUD-P1-AUTH: Auth/Ownership 加固

- **残留代码/文档边界**: 2026-05-26 audit P1-AUTH-001~005 已在 closeout update 中修复 (chat/cancel ownership, chat/retry ownership, notes paper ownership, evidence source artifact fallback)，但修复仅到"定向测试通过"，未做跨用户全覆盖负向测试。
- **为什么映射到 5.0-7**: 5.0-7 是 Auth/Observability 收口 phase，需要在已有修复基础上做 cross-user 路径全覆盖测试。
- **closeout 条件**: cross-user 负向测试零失败；Auth/Ownership 路径有独立测试套件。

### V4-AUD-P1-TASK: 上传/导入/任务可靠性加固

- **残留代码/文档边界**: P1-TASK-001~005 已修复 (local upload os import, chunked upload validation, batch import enqueue, retry enqueue, import job stage sync)，但修复仅到定向测试通过，未做全链集成验证。
- **为什么映射到 5.0-7**: 5.0-7 是 Pipeline 真稳定性 phase，需要在 5.0-3 上传可视化基础上做后端收口。
- **closeout 条件**: 上传→解析→chunk→embed→index→ready 全链路在真实 broker 下通过；task cancel/retry/revoke 有集成测试。

### V4-AUD-P1-DATA: Milvus/向量数据正确性加固

- **残留代码/文档边界**: P1-DATA-001~004 已修复 (Milvus strict insert, reindex/delete 清理, dimension mismatch fail-fast, legacy RAG 对齐)，但需集成验证。
- **为什么映射到 5.0-7**: 向量数据正确性是 Pipeline 稳定性的一部分。
- **closeout 条件**: Milvus insert 全部失败时 paper 不标记 searchable；reindex/delete 后无残留向量。

### V4-AUD-P1-FE: 前端契约/状态回归

- **残留代码/文档边界**: P1-FE-001~004 已修复 (SSE done payload 透传, SearchAuthorPanel s2PaperId, KB polling queued, WorkspaceShell 窄屏)，但需回归测试确认不被后续 phase 覆盖破坏。
- **为什么映射到 5.0-2 + 5.0-3**: WorkspaceShell 窄屏在 5.0-2 升级为响应式底层；上传可视化在 5.0-3 接入前端。
- **closeout 条件**: 已修复的前端 P1 在 5.0-2/5.0-3 closeout 时有回归测试覆盖。

### V4-AUD-P1-GOV: 治理/runtime hygiene 持续验证

- **残留代码/文档边界**: P1-GOV-001~002 已修复 (data/ gitignore, Symphony 架构定位)，P2-GOV-001 已修复 (testing strategy 收敛)。
- **为什么映射到 5.0-0 + 5.0-7**: 5.0-0 建立治理 baseline，5.0-7 做持续验证。
- **closeout 条件**: governance scripts 在每个 phase closeout 时通过。

### V4-RAG-DRIFT: RAG drift 红点消除

- **残留代码/文档边界**: `2026-05-27_v4_5_rag_drift_recheck.md` 确认 4 个 current drift 红点全部消除，测试全部通过。
- **处置**: 已完成，不迁入任何 v5.0 phase。v5.0-8 RAG SOTA 深扩是新能力扩展，不承接 drift 修复。

### V4-P0-CLOSE: v4.5 phase_0 closeout

- **残留代码/文档边界**: v4.5 phase_0 已 closeout，包含 runtime contract freeze、gate input matrix、live RAG benchmark、full RAG chain state report。
- **处置**: 维持 done。v5.0-0 的 runtime contract freeze 和 gate input matrix 在 v4.5 基础上增量扩展，不重做。

### V4-5-DIR: v5/ 平行目录

- **残留代码/文档边界**: `docs/plans/v5/` 下有 DU-20260530-001~006 (V5.0-W0, V5.0-A~E)，定义了 5 个 Phase (A-E)，与 `docs/plans/v5_0/` 的 10 phase 方案冲突。
- **处置**: superseded。`docs/plans/v5_0/` 的 27_v5_0_overview_plan.md 是 v5.0 的正式总览，`docs/plans/v5/` 的旧方案被替代。

## 3. v4.5 multidimensional audit P1 残留分类

2026-05-26 audit 报告的 16 个 P1 在 closeout update 中已全部修复到定向测试通过。按 v5.0 phase 归类:

| 类别 | P1 IDs | 已修状态 | v5.0 加固 phase | 加固内容 |
|---|---|---|---|---|
| Auth/Ownership | P1-AUTH-001~005 | 修复+定向测试 | 5.0-7 | cross-user 负向测试全覆盖 |
| Upload/Task | P1-TASK-001~005 | 修复+定向测试 | 5.0-7 | 全链集成验证 (真实 broker) |
| Vector/Data | P1-DATA-001~004 | 修复+定向测试 | 5.0-7 | Milvus 集成验证 |
| Frontend | P1-FE-001~004 | 修复+定向测试 | 5.0-2 + 5.0-3 | 回归测试 |
| Schema | P1-SCHEMA-001~002 | 修复+migration | 5.0-7 | 生产 schema 验证 |
| Governance | P1-GOV-001~002 | 修复 | 5.0-0 + 5.0-7 | 持续 governance gate |

## 4. v4.0 phase 状态与 superseded 判定

| v4.0 phase | PLAN_STATUS 当前状态 | v5.0 处置 | 理由 |
|---|---|---|---|
| phase_0 | done | 保持 done | 已 closeout，无残留 |
| phase_1 | done | 保持 done | 已 closeout，无残留 |
| phase_2 | done | 保持 done | 已 closeout，无残留 |
| phase_3 | execution-plan-complete / code-and-evidence-required | **superseded** | WP1-WP6 未执行代码收口，整体迁入 5.0-5/5.0-6/5.0-9 |
| phase_4 | done (scope-limited) | 保持 done | 已 closeout，scope 内工作完成 |
| phase_5 | execution-plan-complete / implementation-in-progress | **superseded** | 仅 P0 切片完成，P1-P4 迁入 5.0-1/5.0-2/5.0-4/5.0-5/5.0-9 |
| phase_6 | implementation-in-progress / runtime-contract-extended | 部分 done | runtime contract 已扩展 (done)，RAPTOR-lite/Graph/verifier 融合迁入 5.0-8 |
| phase_7 | execution-complete / blocked | **superseded** | gate runner 升级到 5.0-9，verdict 逻辑继承 |

## 5. 执行回填动作

### 5.1 PLAN_STATUS 回填

1. **v4.0 phase_3**: 在 `docs/plans/PLAN_STATUS.md` v4.0 面板中将 `closeout_status` 从 `execution-plan-complete / code-and-evidence-required` 改为 `superseded-by-v5.0`，notes 补充 `artifact contract closeout 迁入 5.0-5/5.0-6/5.0-9`。
2. **v4.0 phase_5**: 将 `closeout_status` 从 `execution-plan-complete / implementation-in-progress` 改为 `superseded-by-v5.0`，notes 补充 `interaction quality 残留迁入 5.0-1/5.0-2/5.0-4/5.0-5/5.0-9`。
3. **v4.0 phase_7**: 将 `closeout_status` 从 `execution-complete / blocked` 改为 `superseded-by-v5.0`，notes 补充 `gate runner 升级到 5.0-9 consolidated release gate`。
4. **v5/ directory entries**: 在活跃计划面板中将 `DU-20260530-001` (V5.0-W0) 及 `DU-20260530-002~006` (V5.0-A~E) 标为 `superseded`，notes 补充 `被 docs/plans/v5_0/ 的 10-phase 方案替代`。
5. **v4.5 audit findings**: 不需要在 PLAN_STATUS 中单独标注，因为 P1 已在 closeout update 中修复，加固工作由 5.0-7 承接。

### 5.2 Phase Delivery Ledger 回填

1. **新增 V5.0-0 deliverable**: 在 `docs/specs/governance/phase-delivery-ledger.md` 中增加一条 `DU-20260531-001`，phase_id=`V5.0-0`，status=`in-progress`，code_scope 包含本 inventory 文档和后续 5.0-0 产物，doc_scope 包含 `docs/plans/v5_0/active/phase_0/` 全部文件。
2. **标注 V4.0-3 deliverable 状态**: `DU-20260508-001` (V4.0-3-W0) 和 `DU-20260508-003` (V4.0-3-W1) 保持 `in-progress` 不变，但在 `uncovered_items` 中补充 `superseded by v5.0-5/5.0-6/5.0-9`。
3. **标注 V4.0-5 deliverable 状态**: `DU-20260511-002` (V4.0-5-W0) 保持 `in-progress` 不变，uncovered_items 补充 `superseded by v5.0-1/5.0-2/5.0-4/5.0-5/5.0-9`。
4. **标注 V4.0-7 deliverable 状态**: `DU-20260512-003` (V4.0-7-W1) 保持 `done` 不变，notes 补充 `gate runner upgraded to 5.0-9 consolidated release gate`。

### 5.3 5.0-0 自身 closeout 条件

本 inventory 文档完成后，5.0-0 的 v4.x 迁移子项即满足 closeout 条件。5.0-0 整体 closeout 还需:

1. `scripts/evals/run_v5_release_gate.py` 落地
2. `v5_0_runtime_contract_freeze.md` 落地
3. `v5_0_gate_input_matrix.md` 落地
4. `v5_0_perf_baseline_snapshot.md` 落地
5. 多维 audit baseline 二轮跑一次
6. 上述 PLAN_STATUS 和 ledger 回填完成
