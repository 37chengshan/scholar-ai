# v4.0-0 研究文档：Version Gate and v3.0 Residual Close-out

> 日期：2026-05-02  
> 状态：research  
> 对应执行计划：`docs/plans/v4_0/active/phase_0/19_v4_0_phase_0_execution_plan.md`  
> 上游总览：`docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md`

## 1. 研究问题

v4.0 已确认采用：

```txt
A+C 优先
+ 两个前端精细打磨 phase
+ B 后置为一个优化 phase 和一个测试评测 phase
```

因此 Phase 4.0-0 的研究问题不是“新增什么产品能力”，而是：

1. 当前仓库是否具备进入 v4.0 的最低可信基线。
2. v3.0 的哪些残留项已经被后续代码或测试关闭。
3. v3.0 的哪些残留项必须进入 v4.0 gate，不能被写成完成。
4. v4.0 后续 phase 开始前，需要哪些验证、资产和状态台账。

## 2. 当前事实基线

### 2.1 v4.0 方向已确认

当前 v4.0 不是纯技术升级版本，而是产品化和发布可用性优先：

1. `Phase 4.0-1`: Productized Research Workflow
2. `Phase 4.0-2`: Beta Release Hardening
3. `Phase 4.0-3`: Citation-backed Review Artifacts
4. `Phase 4.0-4`: Frontend Experience Craft
5. `Phase 4.0-5`: Frontend Interaction Quality
6. `Phase 4.0-6`: Academic RAG Optimization
7. `Phase 4.0-7`: Testing and Evaluation Gate

### 2.2 v3.0 不能直接宣称完全完成

`docs/plans/v3_0/active/overview/2026-04-29_v3_0_closeout_checklist.md` 仍显示：

1. Phase D 真实世界验证仍需新 run 或复核。
2. Phase F/G 的 full-chain walkthrough、Beta quickstart、demo dataset/account、known limitations 仍需回填。
3. 旧报告曾记录后端 target test 失败，但当前已经复测通过。

Phase 4.0-0 必须承认这个状态：v3.0 有 meaningful implementation，但不是 release-complete。

### 2.3 已复测通过的当前基线

当前已经有以下复测证据，可作为 Phase 4.0-0 的初始输入：

| area | command | result |
|---|---|---|
| backend smoke | `cd apps/api && python3 -m pytest -q tests/unit/test_services.py --maxfail=1` | 16 passed |
| backend contracts | `cd apps/api && python3 -m pytest -q tests/unit/test_chat_persistence_flow.py tests/unit/test_phase_h_runtime_contract.py tests/unit/test_phase_j_comparative_gate.py tests/unit/test_auth_rate_limit_and_failclosed.py --maxfail=5` | 21 passed |
| frontend type-check | `cd apps/web && npm run type-check` | passed |
| frontend unit suite | `cd apps/web && npm run test:run -- --reporter=dot` | 81 files / 308 tests passed |
| governance | `bash scripts/check-governance.sh` | passed |

这些结果说明当前基础 smoke、Chat persistence replay-only、Phase H runtime truth、Phase J comparative gate、auth fail-closed、frontend type-check 和 Vitest runner 暂时可作为 v4.0 启动基线。

## 3. 残留项分类

### 3.1 Closed

| id | source | conclusion |
|---|---|---|
| CO-BLK-005 | v3.0 close-out checklist | `TaskService.retry_task` smoke 已复测通过；正式语义保持只允许 failed task retry |
| V4G-003 | backend review | Chat persistence / Last-Event-ID replay-only 目标组已复测通过 |
| V4G-004 | frontend review | `npm run type-check` 和完整 Vitest runner 已复测通过 |
| V4G-005 | governance | 文档、计划、phase tracking、结构、代码边界、runtime hygiene 与总治理脚本均通过 |

### 3.2 Carried-forward

| id | source | reason | v4.0 handling |
|---|---|---|---|
| V4G-001 | v3.0 Phase D | full-chain real-world validation 仍缺可用新 run 或明确复核结论 | Phase 4.0-0 必须补 walkthrough evidence，不能推迟到 Phase 4.0-7 |
| V4G-002 | v3.0 Phase F/G | Beta quickstart、demo dataset/account、known limitations、walkthrough 缺口仍存在 | Phase 4.0-0 先定义最低资产清单；Phase 4.0-2 深化 |

### 3.3 Rejected / Not in Phase 0

| item | reason |
|---|---|
| 新 agent runtime | 与 v4.0 A+C 优先冲突，且会绕开既有 Chat/Search/KB 主链 |
| Graph/global synthesis implementation | 属于 Phase 4.0-6 技术优化，不进入 Phase 0 |
| 全站视觉重做 | 属于 Phase 4.0-4/5 前端打磨，不进入 Phase 0 |
| CI release gate 完整改造 | 属于 Phase 4.0-7，不进入 Phase 0 |

## 4. Phase 0 最小完成定义

Phase 4.0-0 只有满足以下条件，才能放行到 Phase 4.0-1：

1. `PLAN_STATUS.md` 与 `phase-delivery-ledger.md` 把 v4.0 Phase 0 标记为 active/in-progress，并且记录可追踪 DU。
2. 已关闭项和 carry-forward 项在 Phase 0 文档中有明确分类。
3. Full-chain walkthrough 至少形成一份 repo-local 报告，覆盖：
   - Search
   - Import
   - KB
   - Read
   - Chat
   - Notes
   - Compare
   - Review
4. Beta 最低资产清单明确，不要求全部制作完成，但必须知道哪些交给 Phase 4.0-2。
5. 后端 target tests、前端 type-check/Vitest、治理脚本有当前运行证据。
6. Phase 4.0-1 的首批研究边界明确：先做 continuous workflow，不做 agent runtime。

## 5. Phase 0 不做什么

1. 不新增业务代码。
2. 不重做前端页面。
3. 不新增 RAG 框架或模型路径。
4. 不把 Beta asset 缺口伪装成已完成。
5. 不用旧 v3.0 文档状态替代当前测试/验证证据。

## 6. 风险

| risk | impact | mitigation |
|---|---|---|
| Full-chain walkthrough 需要真实环境，可能不能只靠单测完成 | Phase 4.0-1 放行依据不足 | 先落手工 walkthrough report，再决定是否补浏览器自动化 |
| Beta asset 范围可能膨胀 | Phase 0 变成 Phase 2 | Phase 0 只定义最低资产清单，制作放到 Phase 4.0-2 |
| v3.0 残留项过多 | v4.0 被 close-out 拖住 | 只处理会影响 v4.0 启动可信度的 gate，其余进入后续 phase |
| 技术优化诱惑过早进入 | A+C 主线被稀释 | Phase 4.0-6 前不实现 agentic/Graph 主能力 |

## 7. 研究结论

Phase 4.0-0 应作为 v4.0 的正式启动 gate，而不是可选检查项。它的价值是把 v3.0 的真实状态、当前验证结果、Beta 缺口和 v4.0 后续 phase 的进入条件全部放到同一张证据表里。

结论：

1. 可以启动 Phase 4.0-0。
2. 不能直接进入 Phase 4.0-1 写代码。
3. Phase 4.0-0 的首要任务是补 full-chain walkthrough evidence 和 Beta 最低资产清单。
4. 已通过的后端、前端、治理验证可以作为 Phase 0 的初始证据，但不能替代真实 workflow walkthrough。

