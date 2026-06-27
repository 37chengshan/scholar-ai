---
owner: product-engineering
status: research
depends_on:
  - 21_v4_0_phase_2_execution_plan
  - 22_v4_0_phase_3_execution_plan
  - 24_v4_0_phase_5_execution_plan
  - 24_v4_0_phase_6_execution_plan
last_verified_at: 2026-05-13
evidence_commits:
  - working-tree-v4-5-bridge-prework
---

# v4.5 Release Readiness Bridge 研究文档

> 日期：2026-05-13  
> 状态：research  
> 版本角色：`v4.0` release-readiness bridge prework  
> 当前真相约束：在 v4.5 overview / phase_0 execution plan 冻结前，`docs/plans/PLAN_STATUS.md` 中的 `v4.0` 仍是实现与发布状态真源。

## 1. 研究问题

v4.5 的目标不是定义下一代架构，也不是把 `v4.0` 推翻重来。它要回答的是：

1. 当前仓库距离“可诚实宣称 release-candidate”还缺哪些跨 phase 收口项。
2. 哪些问题是“能力不存在”，哪些只是“路由、shared contract、测试或 walkthrough 没闭环”。
3. v4.5 应该如何把 `v4.0` 的残余 closeout 统一收成一条可执行 bridge 主线，而不是再分散到 Phase 3 / 5 / 6 / 7 各自表述。
4. 需要先创建哪些 repo 内真源目录、状态入口和前置文档，才能让后续实现与验证不继续漂移。

## 2. 当前仓库真相

### 2.1 `v4.0` 现在并不是 “Phase 7 blocked”

`docs/plans/PLAN_STATUS.md` 当前给出的 `v4.0` 真相是：

1. Phase 2：`closeout-complete / controlled-beta-ready`
2. Phase 3：`execution-plan-complete / code-and-evidence-required`
3. Phase 4：`closeout-complete / scope-limited`
4. Phase 5：`execution-plan-complete / implementation-in-progress`
5. Phase 6：`closeout-complete / focused-runtime-shipped`
6. Phase 7：`direction-confirmed / plan-required`

因此，v4.5 的出发点不应再写成：

```txt
local controlled-beta-ready / Phase 7 blocked
-> release-candidate
```

更准确的表达应是：

```txt
controlled-beta-ready exists
+ phase_3 code-and-evidence gap
+ phase_5 interaction gap
+ phase_6 shared runtime contract gap
+ no consolidated v4.5 release gate yet
-> bridge these gaps into a release-candidate track
```

### 2.2 v4.5 不是新主线，而是 bridge 版本

当前 repo 已经证明：

1. 产品主链不是空白，`Search -> Import -> KB -> Read -> Chat -> Compare -> Review` 已有真实实现与部分 closeout。
2. 但 release truth 仍分散在 `v4.0` 的多个 phase 文档、closeout report、feedback queue 和运行时字段里。
3. 如果直接继续按 `v4.0` 分 phase 推进，发布收口会继续被拆散成“某个 phase 看起来完成、整体 release 仍没有统一 verdict”。

所以 v4.5 的职责是：

1. 继承 `v4.0` 已有实现与边界。
2. 把 release-readiness 相关的跨 phase 缺口聚合成一个 bridge 版本。
3. 先补 code truth、shared contract、artifact closeout、walkthrough 和 consolidated gate，再讨论更高一级的发布结论。

## 3. 已验证代码发现

## 3.1 P0：KB-scoped Chat / Search 不是“底层不支持”，而是入口 wiring 没闭环

前端 KB scope handoff 已存在：

1. `KnowledgeWorkspaceShell.tsx` 会生成 `kbId`。
2. `useChatScopeController.ts` 会把它解析为 `full_kb`。
3. `useChatSend.ts` 会把它发成：

```ts
{
  type: 'knowledge_base',
  knowledge_base_id: scope.id,
}
```

后端底层也不是完全缺能力：

1. `build_answer_contract_payload(...)` 已接受 `kb_id` 参数。
2. `retrieve_evidence(...)` 已支持 `kb_id=kb_id`。

真实缺口最初出现在入口层，且主路径也存在半闭环：

1. `apps/api/app/api/chat.py`
   - `chat_v3_query(...)` 只抽取 `paper_scope`，未把 `knowledge_base_id` 透传给 `build_answer_contract_payload(...)`。
   - scoped SSE RAG path 同样只传 `paper_scope`。
2. `apps/api/app/api/search/__init__.py`
   - `V3SearchRequest` 只有 `paper_id`，没有 `kb_id`。
   - `search_evidence_v3(...)` 只向 `build_answer_contract_payload(...)` 传 `paper_scope=[request.paper_id]`。
3. `apps/api/app/rag_v3/main_path_service.py`
   - `retrieve_evidence(...)` 接受 `kb_id`，但最初只把它写入 diagnostics，没有把 KB membership 解析成真实 `paper_scope`。

因此更准确的结论是：

```txt
KB scope handoff exists
+ main_path_service can carry kb_id metadata
- chat/search route contract initially did not forward kb_id end-to-end
- main_path_service initially did not enforce KB scope at retrieval time
```

这会直接影响：

1. full KB chat 是否真的按 KB 边界检索
2. KB evidence search 是否可沿同一 shared path 工作
3. full-chain walkthrough 中 “KB scoped answer” 的 release truth

## 3.2 P0：Phase 6 语义已存在，但仍是分散字段，不是统一 shared runtime contract

当前 repo 里并不存在统一的 `phase6_runtime` 字段或 service。

已存在的是分散的运行时语义：

1. `runtime_truth`
2. `degraded_conditions`
3. `retrieval_plane_policy`
4. `truthfulness_summary`
5. `recovery_actions`
6. `task_family`
7. `execution_mode`

这些字段主要来自：

1. `apps/api/app/rag_v3/main_path_service.py`
2. `apps/api/app/services/review_draft_service.py`
3. `apps/api/app/services/compare_service.py`
4. `apps/api/app/api/chat.py` 的 persisted answer contract

当前真正的问题不是“后端完全没有 runtime contract”，而是：

1. `packages/types/src/chat/contracts.ts` 没有统一 DTO 承接这些 runtime 语义。
2. `apps/web/src/features/chat/hooks/useChatSend.ts` 的 `normalizeAnswerContract()` 没有稳定保留它们。
3. 前端 UI 也没有统一 runtime quality 面板去消费这些字段。

因此 v4.5 的第一步应该是：

```txt
freeze a shared runtime contract
from existing distributed fields
-> then productize it in web UI
```

而不是把当前状态误写成“只差把已经存在的 phase6_runtime 字段前端接一下”。

## 3.3 P0：Compare path 当前对 fallback / degraded 仍然过于乐观

`apps/api/app/services/compare_service.py` 当前仍有两处关键低报：

1. `degraded_conditions=[]`
2. `quality.fallback_used=False`

这意味着 Compare 即使经历了检索降级、fallback 或 evidence 质量问题，也可能继续输出看似干净的 contract。

这条缺口的重要性在于：

1. Compare 已经是 release walkthrough 的主链页面之一。
2. 它会污染 release bridge 对“runtime honesty”与“artifact honesty”的判断。
3. 如果不修，后续 consolidated gate 会天然高估 Compare readiness。

## 3.4 P1：Search / Chat / KB 的轻量测试存在，但 release truth 仍缺 route-contract 级测试

当前 repo 已有一些 useful 基线：

1. `apps/web/src/services/chatApi.test.ts`
   - 证明前端 `knowledge_base` scope body 结构存在
2. `apps/api/tests/unit/test_kb_query_contract.py`
   - 证明 KB query path 有独立契约验证
3. `apps/api/tests/unit/test_main_path_service_scope_routing.py`
   - 证明 `paper_scope` 能被向 `retrieve_evidence(...)` 透传

但当前仍缺两类关键验证：

1. Chat API route 是否把 `knowledge_base_id` 真正传给 `build_answer_contract_payload(...)`
2. Search evidence route 是否支持 `kb_id` 并把它传给同一主路径

另外，现有两个测试过轻：

1. `apps/api/tests/unit/test_chat_uses_v3_retriever.py`
   - 只是源码字符串断言
2. `apps/api/tests/unit/test_search_evidence_api.py`
   - 只覆盖后端失败时的 degraded payload

所以 v4.5 不该写成“没有任何相关测试”，而应写成：

```txt
basic route existence tests exist
+ some main-path and KB contract tests already exist
- no end-to-end route-contract test for kb-scoped chat/search yet
```

## 3.5 P1：v4.5 bridge 不能只盯 Phase 5 / 6，还必须显式纳入 Phase 3 closeout

原始草稿主要盯住：

1. KB scope
2. Phase 6 runtime contract
3. Phase 5 interaction quality
4. full-chain verification

但当前 `PLAN_STATUS` 明确显示：

1. Phase 3 仍是 `code-and-evidence-required`

如果 v4.5 bridge 不把 Phase 3 纳入范围，就会出现新的假闭环：

```txt
chat / compare / runtime / walkthrough 看起来更完整
but review artifact closeout still lacks code-and-evidence truth
```

因此 v4.5 至少要承认：

1. citation-backed review artifacts 仍是 release bridge 的上游阻断项
2. release-candidate 口径不能绕开 Phase 3 直接成立

## 3.6 P1：当前 repo 没有专门的 v4.5 gate runner，不能再引用不存在的脚本

当前仓库里存在：

1. `scripts/evals/v3_0_official_gate.py`
2. 多个 `v4.0` closeout 与 controlled-beta 文档

但不存在：

1. `scripts/evals/run_v4_phase7_gate.py`
2. `apps/api/app/services/phase6_runtime_service.py`

所以 v4.5 研究文档必须修正口径：

1. 不能把不存在的脚本当作现状
2. 应该把 “新增 consolidated v4.5 gate runner / verdict report” 写成 bridge 交付项

## 3.7 P0：v4.5 必须显式纳入“真实 backend 启动 + live RAG benchmark”

本次本地核对后，v4.5 的前置项不能只停留在文档层。

已经验证的运行前提：

1. `apps/api/.venv` 存在，可直接用于本地启动。
2. 在以下环境下，数据库初始化与 Redis 可用：
   - `ENVIRONMENT=test`
   - `NEO4J_DISABLED=true`
   - `AI_STARTUP_MODE=off`
   - `PREFLIGHT_ON_STARTUP=false`
3. 健康检查入口已存在：
   - `/health/live`
   - `/health/ready`
   - `/health/deep`

因此 v4.5 不能再把 benchmark 写成“未来补一个脚本”，而应明确：

```txt
phase_0 must include
real backend startup
+ authenticated route probe
+ functionality + accuracy report
+ artifact output
```

## 3.8 P0：当前真实数据允许 single-paper / compare / primary-KB benchmark，但 many-to-many KB truth 仍未就绪

本地数据真相已确认：

1. `papers = 60`
2. `knowledge_bases = 88`
3. `knowledge_base_papers = 0`
4. `papers with knowledge_base_id != null = 60`
5. `users = 107`

这意味着：

1. single-paper 与 multi-paper compare 路径具备真实 benchmark 样本基础。
2. primary-KB scope 路径可沿 `Paper.knowledge_base_id` 形成真实 benchmark 样本，不应再被错误标记为整体 blocked。
3. `knowledge_base_papers` 为空意味着 many-to-many association truth 尚未验证，不能把“主 KB scope 可跑”偷换成“多知识库 membership 语义已闭环”。
4. `v4.5` 的 gate 输入矩阵应允许 `kb-scoped chat/search/query` 进入真实 pass/fail，但需要把 `knowledge_base_papers` 为空单独记为结构性风险，而不是直接阻断整个 KB benchmark。

## 4. v4.5 正确定位

v4.5 应定义为：

```txt
verified release-readiness bridge
=
code truth repair
+ shared runtime contract freeze
+ phase_3 artifact closeout carry-in
+ phase_5 interaction closeout
+ full-chain workflow verification
+ consolidated gate and verdict
```

其中 `full-chain workflow verification` 在 v4.5 的第一步必须落实为：

1. 真 backend 启动
2. 真 health probe
3. 真 RAG route benchmark
4. JSON / Markdown artifact 回填

它明确不做：

1. GraphRAG 大重写
2. STORM full stack
3. 第二套 agent runtime
4. 新模型实验平台
5. 脱离现有主链的 UI 重做
6. 把 `controlled-beta-ready` 越级写成 `public-beta-ready` 或 `release-pass`

## 5. 推荐的 v4.5 拆分

## Phase 4.5-0：Bridge Prework and Code Truth Repair

目标：

1. 修正 KB-scoped chat/search route contract
2. 冻结 shared runtime contract
3. 修复 Compare runtime honesty
4. 增加 route-contract 级测试
5. 形成 v4.5 overview / phase_0 execution 输入

建议范围：

1. `apps/api/app/api/chat.py`
2. `apps/api/app/api/search/__init__.py`
3. `apps/api/app/rag_v3/main_path_service.py`
4. `apps/api/app/services/compare_service.py`
5. `packages/types/src/chat/contracts.ts`
6. `apps/web/src/features/chat/hooks/useChatSend.ts`
7. `apps/api/tests/unit/*kb_scope*`
8. `apps/web/src/features/chat/**/*phase6Runtime*`

## Phase 4.5-1：Citation-backed Artifact Closeout

目标：

1. 把 Phase 3 的 `code-and-evidence-required` 纳入 v4.5 bridge
2. 收口 review artifact、evidence note、compare matrix、known limitations return path
3. 让 release bridge 不再绕开 artifact closeout

这一步是对原始草稿的重要补强，因为当前 release bridge 不能只看 chat/runtime，而不看 review artifact truth。

## Phase 4.5-2：Interaction Quality + Runtime Productization

目标：

1. 继续完成 Phase 5 的 interaction closeout
2. 把 shared runtime contract 产品化成前端可见质量面板
3. 让 user-facing UI 能诚实表达：
   - degraded
   - fallback
   - recovery action
   - current execution mode

## Phase 4.5-3：Full-chain Verification + Consolidated Release Gate

目标：

1. 运行 fresh account / controlled dataset 的 full-chain walkthrough
2. 产出 machine-readable results 与 markdown report
3. 新增 repo-local consolidated gate runner
4. 给出 `blocked / release-candidate / release-pass` 中的一项结论

这里的 gate runner 是新增交付物，不是引用既有脚本。

## 6. Phase 4.5-0 的前置文档输出

本次 prework 创建的目录与下一步建议真源如下：

1. `docs/plans/v4_5/README.md`
   - v4.5 目录入口
2. `docs/plans/v4_5/active/overview/2026-05-13_v4_5_release_readiness_bridge_research.md`
   - bridge 研究真源
3. `docs/plans/v4_5/active/phase_0/README.md`
   - 预留 phase_0 execution / contract freeze / gate input matrix 的入口
4. `docs/plans/v4_5/search/README.md`
   - 外部资料与 gap scan 材料落点
5. `docs/plans/v4_5/reports/README.md`
   - walkthrough / gate / closeout 报告落点

建议下一批文件：

1. `docs/plans/v4_5/active/overview/25_v4_5_overview_plan.md`
2. `docs/plans/v4_5/active/phase_0/26_v4_5_phase_0_execution_plan.md`
3. `docs/plans/v4_5/active/phase_0/v4_5_runtime_contract_freeze.md`
4. `docs/plans/v4_5/active/phase_0/v4_5_gate_input_matrix.md`

## 7. 完成定义

v4.5 只有在以下条件同时满足时，才有资格往 `release-candidate` 推进：

1. KB-scoped chat/search route contract 真实闭环
2. shared runtime contract 在 backend / shared type / frontend 三层闭环
3. Compare 的 degraded / fallback honesty 修复
4. Phase 3 artifact closeout 被显式纳入并补齐
5. Phase 5 interaction quality 有真实验证证据
6. full-chain walkthrough 有 machine-readable repo-local artifacts
7. consolidated v4.5 gate runner 与 verdict report 落地
8. `PLAN_STATUS`、phase ledger、目录入口和报告路径全部同步

## 8. 研究结论

v4.5 的正确定位不是“再开一轮功能开发”，而是：

```txt
把 v4.0 分散的 closeout 缺口
压缩成一条可验证、可回填、可给 verdict 的 bridge 主线
```

当前最优先的不是重新谈框架，而是先修：

1. KB-scoped route contract
2. shared runtime contract freeze
3. Compare runtime honesty
4. Phase 3 artifact carry-in
5. consolidated release gate inputs
