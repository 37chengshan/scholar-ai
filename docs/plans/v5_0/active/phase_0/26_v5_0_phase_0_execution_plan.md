---
owner: product-engineering
status: execution-plan-complete
depends_on:
  - docs/plans/v5_0/active/overview/27_v5_0_overview_plan.md
  - docs/plans/v4_5/active/phase_0/26_v4_5_phase_0_execution_plan.md
  - docs/plans/v4_5/active/phase_0/v4_5_runtime_contract_freeze.md
  - docs/plans/v4_5/active/phase_0/v4_5_gate_input_matrix.md
  - docs/plans/v5_0/active/phase_0/README.md
last_verified_at: 2026-05-31
evidence_commits:
  - working-tree-v5-0-kickoff
---

# 26 v5.0-0 执行计划：Foundation + v4.x 迁移 + Audit Baseline

> 日期：2026-05-31
> 状态：execution-plan-complete
> 上游真源：`docs/plans/v5_0/active/overview/27_v5_0_overview_plan.md` § 4 + § 11

---

## 1. 目标

Phase 5.0-0 是 v5.0 的启动期，**主线为治理切换，不动任何业务代码**。

本 phase 完成后，v5.0 进入正式可执行状态，后续 phase 1–9 全部解锁。产出六个治理基础产物：

1. v4.x → v5.0 **migration inventory**（逐项映射 v4.0 phase_3 / phase_5 / phase_7 与 v4.5 残留任务到 v5.0 对应 phase）
2. `scripts/evals/run_v5_release_gate.py`（从 `run_v4_phase7_gate.py` 升级，成为 consolidated release gate runner）
3. **v5.0 runtime contract freeze**（继承 v4.5 contract + 预留 RAPTOR-lite / Graph synthesis / verifier fusion 字段）
4. **v5.0 gate input matrix**（5 个输入面：audit + benchmark + walkthrough + governance + perf）
5. **v5.0 perf baseline snapshot**（首轮 Lighthouse + bundle 体积，供后续 phase 回填 delta）
6. **v5.0 phase_0 audit baseline report**（multidimensional audit 二轮第一次跑，记录起点状态）

---

## 2. 范围与不在范围

### 在范围

- 把 v4.0 phase_3 / phase_5 / phase_7 在 `PLAN_STATUS.md` 标为 `superseded`，并指向 v5.0 替代 phase
- 把 v4.5 bridge 残留任务（若有 W2+ 未 closeout 的工作单元）逐项写入 inventory
- 从 `run_v4_phase7_gate.py` 升级出 `run_v5_release_gate.py`（结构升级 + 5 个输入面扩展）
- 基于 v4.5 `v4_5_runtime_contract_freeze.md` 增量，冻结 v5.0 contract，新增 RAPTOR / Graph / verifier 字段占位
- 以 v4.5 gate input matrix 为基底，扩展为 5 面 v5.0 版本（新增 perf 输入面）
- 运行 Lighthouse（4 个主路由）+ 记录 bundle 体积，产出基线快照
- 运行 multidimensional audit 二轮第一次，记录初始状态（不要求修复）
- 更新 `docs/plans/PLAN_STATUS.md`、`phase-delivery-ledger.md`、`docs/README.md`

### 不在范围

- 任何 `apps/web`、`apps/api` 业务代码修改
- 任何前端 UI 改动（留给 phase 1–6）
- 任何后端 Pipeline / Auth / Observability 改动（留给 phase 7）
- 任何 RAG 能力改动（留给 phase 8）
- 写出 release verdict 或 release-candidate 声明
- 执行 Playwright E2E walkthrough（留给 phase 9）
- 修复 audit baseline report 发现的问题（仅记录，不修）

---

## 3. 工作分解（W0 ~ W5）

| Wave | 产物 | 对应文件 | 估时 |
|---|---|---|---|
| W0 | Migration Inventory | `v5_0_v4x_migration_inventory.md` | 2–3 天 |
| W1 | Perf Baseline Snapshot | `v5_0_perf_baseline_snapshot.md` | 1–2 天（与 W0 并行） |
| W2 | Runtime Contract Freeze | `v5_0_runtime_contract_freeze.md` | 1–2 天（W0 后） |
| W3 | Gate Input Matrix | `v5_0_gate_input_matrix.md` | 1 天（W2 后） |
| W4 | Gate Runner 升级 | `scripts/evals/run_v5_release_gate.py` | 2 天（W3 后） |
| W5 | Audit Baseline Report | `docs/plans/v5_0/reports/2026-XX-XX_v5_0_phase_0_audit_baseline.md` | 2–3 天（W0–W4 后） |

总计：最短 7 天 / 含 buffer 约 10–12 天（1–2 周内完成）

---

## 4. 每个 Wave 的具体任务清单

### W0 — Migration Inventory

**目的：** 建立 v4.x 残留任务与 v5.0 的完整映射，是后续所有 phase 的迁移真源。

任务：

1. 读取 `docs/plans/v4_0/active/` 下 phase_3、phase_5、phase_7 的 README 与执行计划，提取所有未 closeout 的 deliverable unit
2. 读取 `docs/plans/v4_5/active/` 下各 wave（W0–W?）状态，提取未 closeout 或状态不明的工作单元
3. 逐条列出映射关系：`v4.x 来源 phase` → `v5.0 对应 phase` + 处置方式（superseded / carried / merged）
4. 在 `docs/plans/PLAN_STATUS.md` 将 v4.0 phase_3、phase_5、phase_7 状态改为 `superseded`，并在 `superseded_by` 字段填写 v5.0 对应 phase 编号
5. 写入 `docs/plans/v5_0/active/phase_0/v5_0_v4x_migration_inventory.md`

产物路径：`docs/plans/v5_0/active/phase_0/v5_0_v4x_migration_inventory.md`

验收条件：
- 文件包含 v4.0 phase_3、phase_5、phase_7 的全量 deliverable unit 逐条映射，无遗漏
- `PLAN_STATUS.md` 中三个 v4.0 phase 状态均已改为 `superseded`，且 `superseded_by` 字段非空
- `bash scripts/check-plan-governance.sh` 通过（或已记录 known exemption）

---

### W1 — Perf Baseline Snapshot（可与 W0 并行）

**目的：** 建立 v5.0 性能基线，为后续 phase 2 performance 体系提供 delta 参照点。

任务：

1. 启动本地 `apps/web` 开发服务（`npm run dev`）或 preview build（`npm run build && npm run preview`）
2. 对 4 个主路由运行 Lighthouse CLI（desktop 模式）：`/`、`/kb`、`/read`（带 paperId）、`/chat`（带 sessionId）
3. 记录各路由的 Performance / Accessibility / Best Practices / SEO 四维分数
4. 运行 Vite build，记录 `dist/assets/` 目录各 chunk 文件大小（gzipped 估算）
5. 记录 dist 总体积，列出超过 200KB gzipped 的 chunk（风险标注）
6. 写入 `docs/plans/v5_0/active/phase_0/v5_0_perf_baseline_snapshot.md`

产物路径：`docs/plans/v5_0/active/phase_0/v5_0_perf_baseline_snapshot.md`

验收条件：
- 文件包含 4 个路由的 Lighthouse 分数表格（performance、a11y、best-practices、seo 四列）
- 文件包含 bundle 体积表格，列出所有 chunk 及 gzipped 估算值
- 明确标注超限 chunk（当前无 budget，属于 baseline 记录，不要求修复）
- 所有数字均来自实际运行，禁止估算填写

---

### W2 — Runtime Contract Freeze（依赖 W0）

**目的：** 冻结 v5.0 对外 runtime 契约，作为 phase 1–9 的接口真源。

任务：

1. 读取 `docs/plans/v4_5/active/phase_0/v4_5_runtime_contract_freeze.md` 作为基底
2. 逐项继承 v4.5 contract 字段（不删除已有字段）
3. 新增 RAPTOR-lite 字段预留区（`retrieval_strategy: "raptor-lite" | "standard"`）
4. 新增 Graph synthesis 字段预留区（`graph_synthesis_mode: "review-only" | "disabled"`）
5. 新增 Verifier fusion 字段预留区（`claim_verification: { mode: "unified" | "legacy", nli_enabled: boolean }`）
6. 新增 perf contract 字段：`lighthouse_targets`（四路由 Performance ≥ 90）、`bundle_budget`（首屏 ≤ 500KB gzipped）
7. 明确标注各字段的 phase 引入计划（哪个 phase 负责落地）
8. 写入 `docs/plans/v5_0/active/phase_0/v5_0_runtime_contract_freeze.md`

产物路径：`docs/plans/v5_0/active/phase_0/v5_0_runtime_contract_freeze.md`

验收条件：
- 文件包含 v4.5 contract 全量字段，无遗漏
- RAPTOR / Graph / verifier fusion / perf 四个新增预留区均已写入
- 每个新增字段标注 `introduced_in: phase_X` 说明引入 phase
- 文件开头有明确 `status: frozen` 标注

---

### W3 — Gate Input Matrix（依赖 W2）

**目的：** 冻结 v5.0 release gate 的五个输入面定义，作为 phase 9 验收的最终口径。

任务：

1. 读取 `docs/plans/v4_5/active/phase_0/v4_5_gate_input_matrix.md` 作为基底
2. 继承 audit、benchmark、walkthrough、governance 四个输入面，逐项更新以反映 v5.0 新 phase 范围
3. 新增第五个输入面：perf（Lighthouse CI 四路由 ≥ 90 + bundle 首屏 ≤ 500KB gzipped）
4. 明确每个输入面的：负责 phase、产出形式、判定口径（pass / fail / blocked 三态）
5. 写入 `docs/plans/v5_0/active/phase_0/v5_0_gate_input_matrix.md`

产物路径：`docs/plans/v5_0/active/phase_0/v5_0_gate_input_matrix.md`

验收条件：
- 文件包含五个输入面：audit、benchmark、walkthrough、governance、perf，每面均有负责 phase 和判定口径
- benchmark 面明确包含：RAG academic baseline + RAPTOR-lite comparative benchmark（phase 8 产出）
- walkthrough 面明确列出 7 条核心 journey（来自 overview § 4 Phase 9 目标）
- perf 面明确列出 4 个路由名称与分数门禁值

---

### W4 — Gate Runner 升级（依赖 W3）

**目的：** 把 v4.0 phase_7 gate runner 升级为 v5.0 consolidated release gate runner。

任务：

1. 读取 `scripts/evals/run_v4_phase7_gate.py`（若存在），理解现有结构
2. 新建 `scripts/evals/run_v5_release_gate.py`，继承 phase7 runner 的结构框架
3. 扩展以支持五个输入面（audit / benchmark / walkthrough / governance / perf）的命令行参数
4. 每个输入面支持 `--skip-X` 开关（用于分阶段验证）
5. 输出格式：structured JSON summary（`artifacts/validation-results/v5_0/release_gate/<timestamp>/summary.json`）+ 人读 Markdown（`summary.md`）
6. 如果输入面数据缺失，输出 `blocked`，不允许输出 `pass`
7. 文件头部必须包含注释：当前仅供 phase_0 结构验证，final gate 在 phase_9 激活

产物路径：`scripts/evals/run_v5_release_gate.py`

验收条件：
- `python3 scripts/evals/run_v5_release_gate.py --help` 能正常运行并显示五个输入面的参数说明
- 运行 `--skip-audit --skip-benchmark --skip-walkthrough --skip-governance --skip-perf` 后输出 `all-inputs-skipped`，不报错
- 代码文件行数 ≤ 400 行（超出须拆分辅助模块）
- 禁止把任何 blocked 状态写成 pass

---

### W5 — Audit Baseline Report（依赖 W0–W4 全部完成）

**目的：** 记录 v5.0 启动时的多维审计初始状态，作为 phase 9 二轮 audit 的对比基准。

任务：

1. 基于 `2026-05-26_v4_5_frontend_backend_multidimensional_audit.md` 已修闭环结果，确认 P1 修复状态
2. 对以下维度运行二轮第一次审计（仅记录，不要求修复）：
   - 前端代码质量（test coverage 现状、文件超限、0 test 组件列表）
   - 后端 Pipeline 稳定性（已知残端清单）
   - Auth/Ownership 覆盖现状
   - 设计系统 token 现状（当前 39 个 CSS vars 的覆盖分析）
   - Observability 现状（trace_id / run_id 贯通率）
3. 每个维度用表格形式列出：发现项、严重级别（P1/P2/P3）、负责修复的 v5.0 phase、修复状态（待处理）
4. 写入 `docs/plans/v5_0/reports/2026-05-31_v5_0_phase_0_audit_baseline.md`
5. 回填 `docs/specs/governance/phase-delivery-ledger.md`（phase 5.0-0 条目）

产物路径：`docs/plans/v5_0/reports/2026-05-31_v5_0_phase_0_audit_baseline.md`

验收条件：
- 文件涵盖至少五个审计维度
- P1 级问题全部注明负责 phase，不允许 P1 无 owner
- 文件明确标注：本报告为 baseline 记录，不是修复完成声明
- `phase-delivery-ledger.md` 中 phase 5.0-0 条目状态为 `done`

---

## 5. 依赖与顺序

```
W0 (Migration Inventory)
├── W1 (Perf Baseline) ← 可与 W0 并行，完全独立
├── W2 (Contract Freeze) ← 依赖 W0（需要 inventory 确认 v4.x 字段继承清单）
│   └── W3 (Gate Matrix) ← 依赖 W2（matrix 引用 contract 字段）
│       └── W4 (Gate Runner) ← 依赖 W3（runner 参数面来自 matrix 定义）
└── W5 (Audit Baseline) ← 依赖 W0–W4 全部完成
```

关键约束：

- W0 和 W1 可以同时启动（互不依赖）
- W2 必须等 W0 完成后才能启动（inventory 决定 contract 新增字段范围）
- W3 必须等 W2 完成后才能启动（gate matrix 的 perf 面参数来自 contract freeze）
- W4 必须等 W3 完成后才能启动（runner 命令行参数面与 matrix 定义一一对应）
- W5 必须等 W0–W4 全部完成后才能启动（baseline 报告需要 inventory + gate structure 作为参照）
- **phase 5.0-0 完成后才能解锁 phase 5.0-1 至 5.0-9**

---

## 6. 风险与缓解

| 风险 | 可能性 | 缓解措施 |
|---|---|---|
| v4.0 phase_3/5/7 残留工作量远大于预期，inventory 无法 1–2 天完成 | 中 | 先完成 phase_7 mapping（最重要，影响 gate runner 升级），phase_3/5 可在 inventory 中写"待细化" |
| 本地无完整测试数据，Lighthouse 无法对 `/read` / `/chat` 等需要参数的路由采集真实数据 | 高 | 改用 `/read/sample-paper-id`（固定 seed 参数），Lighthouse 取 desktop 模式，允许 network 相关指标用"-"标记 |
| `run_v4_phase7_gate.py` 若不存在，升级无法参照现有结构 | 低 | 先检查脚本是否存在，若不存在则从 v4.5 live RAG benchmark runner 结构衍生 |
| audit baseline 报告发现大量 P1，导致 phase_0 被阻塞 | 低 | baseline 报告的目的是**记录**，不是修复。P1 发现项写入负责 phase，不阻塞 phase_0 closeout |
| 五个输入面的 gate runner 行数超过 400 行 | 中 | 将每个输入面的检查逻辑拆分到 `scripts/evals/gates/` 子模块，主文件仅做分发 |

---

## 7. 验收口径（Phase 5.0-0 Closeout 标准）

以下条件**全部满足**，phase 5.0-0 才可 closeout：

1. `docs/plans/v5_0/active/phase_0/v5_0_v4x_migration_inventory.md` 已存在，且 v4.0 phase_3、phase_5、phase_7 全量 deliverable unit 均有 v5.0 映射记录
2. `docs/plans/PLAN_STATUS.md` 中 v4.0 phase_3、phase_5、phase_7 状态均为 `superseded`，`superseded_by` 非空
3. `docs/plans/v5_0/active/phase_0/v5_0_runtime_contract_freeze.md` 已存在，`status: frozen`，RAPTOR / Graph / verifier / perf 四个预留区均已写入
4. `docs/plans/v5_0/active/phase_0/v5_0_gate_input_matrix.md` 已存在，五个输入面（audit / benchmark / walkthrough / governance / perf）各有负责 phase 和 pass/fail/blocked 判定口径
5. `scripts/evals/run_v5_release_gate.py` 已存在，`--help` 可运行，五个输入面参数完整
6. `docs/plans/v5_0/active/phase_0/v5_0_perf_baseline_snapshot.md` 已存在，包含 4 个路由 Lighthouse 数据 + bundle 体积数据（均为实测值）
7. `docs/plans/v5_0/reports/2026-05-31_v5_0_phase_0_audit_baseline.md` 已存在，五维审计结果齐全，P1 项无空 owner
8. `docs/specs/governance/phase-delivery-ledger.md` 中 phase 5.0-0 条目已回填为 `done`
9. 以下治理脚本全部通过（或已记录 known exemption 并附 PR 编号）：
   - `bash scripts/check-doc-governance.sh`
   - `bash scripts/check-plan-governance.sh`
   - `bash scripts/check-phase-tracking.sh`
   - `bash scripts/check-governance.sh`

---

## 8. 不产出的东西（明确边界）

以下内容**禁止**在 phase 5.0-0 中产出或声明：

- **release verdict**（release-pass / release-blocked 结论）：只有 phase 5.0-9 有权写出，本 phase 禁止
- **release-candidate 声明**：同上，禁止
- 任何 `apps/web/` 或 `apps/api/` 目录下的代码改动
- 任何对现有 UI 布局、组件或交互的修改
- 任何 RAG 能力改动（RAPTOR、Graph、Verifier 字段本轮仅做**预留占位**，不落地）
- E2E Playwright walkthrough（仅 phase 9 负责）
- 修复 audit baseline 发现的任何问题（baseline 是记录，不是修复单）
- 新增任何 npm 依赖或 Python 包（gate runner 仅使用标准库 + 已存在的 project 工具）
