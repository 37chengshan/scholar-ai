# EP-2026-04-20 战役A Workflow UI/IA 重构实施计划

作者：glm5.1+37chengshan
日期：2026-04-20
分支：feat/workflow-ui-ia-reset-20260420
任务来源：战役A_Workflow_UI_IA_重构任务单_可直接给5.3Codex.md

## 1. 目标与边界

### 1.1 唯一目标
将前端从“页面集合导航”重构为“Agent-Native 工作流工作台壳层”，统一任务状态、动作、恢复、证据与作用域语义。

### 1.2 明确不做
- 不做 Chat 后端 agent runtime 深改
- 不做 Run/Step/ToolEvent 后端协议重构
- 不做 RAG 算法升级
- 不做知识图谱后端重构
- 不做模型/Prompt 大改

## 2. 现状基线（实施前）
- 一级路由仍暴露：/dashboard、/notes（与目标 IA 冲突）
- 缺少全站统一 workflow shell
- Search/KB/Chat/Read 分别维护局部状态，缺统一 workflow store
- Landing 文案偏技术能力宣传，不是 workflow 工作台叙事

## 3. 交付分解（严格按任务单 WP1-WP6）

## WP1 Workflow Shell 重构

### 产物
- apps/web/src/features/workflow/components/WorkflowShell.tsx
- apps/web/src/features/workflow/components/ActiveScopeBanner.tsx
- apps/web/src/features/workflow/components/CurrentRunBar.tsx
- apps/web/src/features/workflow/components/PendingActionsPanel.tsx
- apps/web/src/features/workflow/components/RecoverableTasksPanel.tsx
- apps/web/src/features/workflow/components/ActivityTimelineDrawer.tsx
- apps/web/src/features/workflow/components/ArtifactsDrawer.tsx

### 实施点
- 在 Layout 级别挂载 WorkflowShell，非 chat/read/search/kb 的工具页不展示
- 壳层区域固定：Scope Banner + Run Bar + 右侧抽屉入口 + Pending/Recoverable 区
- 壳层可跨 chat/knowledge-bases/read/search 复用

### 验收
- 以上核心页面均可见统一壳层
- 壳层展示 active scope、active run/job、pending/recoverable、artifacts/timeline

## WP2 全局 workflow store / adapters / resolvers

### 产物
- apps/web/src/features/workflow/state/workflowStore.ts
- apps/web/src/features/workflow/state/workflowSelectors.ts
- apps/web/src/features/workflow/state/workflowActions.ts
- apps/web/src/features/workflow/adapters/workflowAdapters.ts
- apps/web/src/features/workflow/resolvers/workflowResolvers.ts
- apps/web/src/features/workflow/types.ts
- apps/web/src/features/workflow/hooks/useWorkflowHydration.ts

### 必含函数
- mapRunToWorkflowViewModel
- mapImportJobToWorkflowCard
- mapErrorToUiAction
- mapArtifactToUiRenderable
- mapScopeToBannerModel
- resolveNextActions
- resolveRecoverableActions
- resolveStatusBadge
- resolveWorkflowCopy

### 实施点
- 聚合输入来源：
  - chat scope（URL query）
  - search import runtimeStatus
  - knowledge-base import 状态与 location state
  - read 页面 paper scope
- 页面组件不直拼 raw API 状态；统一走 adapter+resolver

### 验收
- 不出现散落式 status if/else 直接在页面拼接文案
- workflow UI 文案和 badge 来自 resolver

## WP3 路由与布局重构

### 产物
- apps/web/src/app/routes.tsx
- apps/web/src/app/components/Layout.tsx
- apps/web/src/app/routes.test.tsx（更新）

### 实施点
- 一级导航收敛为：Chat/Workspace、Library、Search、Settings
- /knowledge-bases 作为 Library 的主路由保留，导航文案统一为 Library
- /dashboard 从一级导航移除并降级为非一级内部入口，路由重定向到 /knowledge-bases
- /notes 从一级导航移除（路由保留兼容），并引导到 Read / Library 的上下文笔记能力
- chat/kb/search/read 接入统一 workflow shell

### 验收
- Layout 不再显示 Dashboard/Notes 一级入口
- 路由策略体现“工作流主线优先”

## WP4 Landing 重写

### 产物
- apps/web/src/app/pages/Landing.tsx
- apps/web/src/app/components/landing/*（按需新增/替换）

### 实施点
- Hero 改为 Agent-Native 学术研究工作台叙事
- 核心承诺：任务执行、过程与证据可视化、可恢复可确认
- 删除旧叙事中过强技术堆料式表达（保留必要能力说明）

### 验收
- Landing 首屏与核心 section 明确 workflow/agent-native 定位

## WP5 旧页面审计与清理

### 产物
- docs/frontend/page-audit-workflow-reset.md

### 必含字段
- route
- current purpose
- keep / merge / downgrade / delete
- replacement
- blockers
- owner

### 实施点
- 明确 dashboard 处理结论（降级）
- 明确 notes 处理结论（移出一级导航并并入 read/library 上下文）
- 清理无主线价值旧入口/死路由暴露

## WP6 全站文案统一

### 产物
- docs/frontend/workflow-ui-ia-reset.md
- 相关页面文案 patch（Layout/Chat/Library/Search/Read/Landing）

### 实施点
- 统一 status/action/scope/artifact/pending/recover 文案语义
- 更新空状态/按钮文案，避免旧“页面导向”术语

### 验收
- 核心页面使用一致 workflow 术语

## 4. 执行顺序
1) 页面审计与 IA 固化（WP5 先行，先定义删改边界）
2) Workflow store + adapter/resolver（WP2）
3) Workflow Shell（WP1）
4) 路由与布局重构（WP3）
5) Landing 重写（WP4）
6) 文案统一与清理收口（WP6）

## 4.1 Wave 与任务拆分（执行级）

### Wave-1（IA 审计与边界固定）
- A1：新增 docs/frontend/page-audit-workflow-reset.md，完成 route 审计表
- A2：新增 docs/frontend/workflow-ui-ia-reset.md，固定新 IA、导航与文案术语
- A3：明确 dashboard/notes/knowledge-bases 的保留与降级策略

验收：审计表覆盖现有一级路由，且 replacement 字段完整。

### Wave-2（Workflow 领域层）
- B1：新增 workflow types/store/selectors/actions 基础骨架
- B2：新增 workflow adapters（run/import/scope/error/artifact）
- B3：新增 workflow resolvers（next/recoverable/status/copy）
- B4：新增 useWorkflowHydration，接入 chat/search/kb/read 状态源

验收：页面通过 selector 消费 view model，不直接拼 raw API 字段。

### Wave-3（Shell + 路由 + 布局）
- C1：实现 WorkflowShell 与 6 个子组件（scope/run/pending/recover/timeline/artifacts）
- C2：Layout 接入 WorkflowShell，并仅在核心 workflow 页面显示
- C3：收敛一级导航（移除 dashboard/notes 一级入口）
- C4：routes 重构：dashboard 重定向到 knowledge-bases，notes 保留兼容路由

验收：一级导航仅 Chat/Library/Search/Settings，且 shell 在 chat/kb/read/search 可见。

### Wave-4（Landing + 文案 + 清理）
- D1：Landing 改为 Agent-Native 工作台叙事
- D2：统一关键页面文案（Chat/Library/Search/Read/Layout）
- D3：删除或降级无主线价值入口与死暴露
- D4：补充测试与复查报告

验收：Landing 与全站术语统一，旧页面不再高优暴露。

## 5. 测试与复查计划
- 前端类型检查：cd apps/web && npm run type-check
- 关键测试：
  - cd apps/web && npm run test:run -- src/app/routes.test.tsx
  - cd apps/web && npm run test:run -- src/app/pages/Search.test.tsx src/app/pages/Chat.test.tsx
- 补充 workflow 层单测：adapter/resolver/store 的 unit test
  - src/features/workflow/adapters/workflowAdapters.test.ts
  - src/features/workflow/resolvers/workflowResolvers.test.ts
  - src/features/workflow/state/workflowStore.test.ts
- 复查点：
  - 一级导航收敛验证
  - dashboard/notes 暴露级别验证
  - workflow shell 在 chat/kb/search/read 的一致性验证
  - grep 验证：核心页面不再直接拼 status 文案（统一由 resolver 产出）

## 5.1 Landing 保留/删除标准
- 保留：与 workflow 主线直接相关的能力表述（计划、执行、确认、恢复、证据）
- 删除：纯技术堆料式宣传（不与用户任务阶段绑定的底层名词堆叠）

## 5.2 WP6 文案必改清单
- Layout 主导航文案（Chat/Library/Search/Settings）
- WorkflowShell 的 pending/recoverable/artifact/scope 文案
- Chat 页入口说明（Workspace 语义）
- Library 页标题与空状态
- Search 页标题与空状态
- Read 页右侧与空状态文案
- Notes 降级后的引导文案（跳转到上下文能力）

## 6. 风险与应对
- 风险：历史页面耦合导致路由回归
  - 应对：先保留路由兼容，再降级入口显示
- 风险：状态源分散导致 workflow store 同步不一致
  - 应对：引入单向 hydration hook，仅由 adapter 更新 store
- 风险：视觉变化过大引发使用成本
  - 应对：保留原核心功能路径，先统一壳层与语义，不改业务动作顺序

## 7. 完成即停标准（DoD）
1) 全站统一 Workflow Shell 存在并生效
2) workflow store + resolver + adapter 层存在并被消费
3) 一级导航完成收敛
4) Dashboard 删除或降级（本次采用降级）
5) Notes 已移出一级导航并给出合并路径
6) Landing 完成 Agent-Native 重写
7) 无明显死路由继续高优暴露
8) 审计文档 + IA 文档已提交
