# 2026-05-01 前端系统审查报告

## 1. 审查范围

本次审查聚焦 `apps/web` 的四类问题：

1. 前端基础验证是否通过
2. 单测/测试基建是否可信
3. 前端对 `packages/sdk` / `packages/types` 的依赖方式是否稳定
4. Chat / KB 关键页面相关的实现与组件层告警

本次没有修改业务代码，只做证据式检查与报告落盘。

## 2. 本次执行的验证

已执行命令与结果：

1. `cd apps/web && npm run type-check`：passed
2. `cd apps/web && npm run test:run -- --reporter=dot`：failed

前端测试总体结果：

1. `81` 个测试文件里 `78` 个通过，`3` 个失败
2. `296` 个测试里 `294` 个通过，`2` 个失败
3. 另有大量运行期警告，主要是 `react-router mock`、`canvas getContext`、`Dialog ref` 问题

直接失败点：

1. `src/app/routes.test.tsx` 无法解析 `@scholar-ai/sdk`
2. `src/app/pages/KnowledgeBaseDetail.test.tsx` 无法解析 `@scholar-ai/sdk`
3. `src/features/chat/workspace/ChatWorkspaceV2.test.tsx` 中 `react-router` mock 缺失 `useLocation`

## 3. 总体结论

结论：**前端运行主线比后端稳定，但测试基建明显落后于当前实现。**

更准确地说：

1. `type-check` 通过，说明 TS 静态层没有大面积破裂。
2. 大部分单测也能通过，说明前端不是全面失稳。
3. 但当前失败主要集中在“依赖解析与测试基建”而不是纯业务逻辑，这会让前端进入一种危险状态：
   - 开发时看起来能跑
   - 类型也能过
   - 但测试环境和真实构建边界并不一致
4. 这类问题会持续拖慢 Chat / KB / Workflow 页面后续迭代。

## 4. 高优先级问题

### 4.1 Vitest 与 Vite/TS 的路径解析不一致，导致 `@scholar-ai/sdk` 在测试环境直接失效

证据：

1. `apps/web/vite.config.ts:13-19`
2. `apps/web/tsconfig.json:23-31`
3. `apps/web/vitest.config.ts:14-18`
4. `apps/web/src/services/sessionsApi.ts:1-7`
5. `apps/web/src/services/kbReviewApi.ts:1-9`
6. `cd apps/web && npm ls @scholar-ai/sdk @scholar-ai/types --depth=0` 输出 `(empty)`

现象：

1. `vite.config.ts` 为 `@scholar-ai/sdk` 和 `@scholar-ai/types` 配了 alias
2. `tsconfig.json` 也配置了对应 paths
3. 但 `vitest.config.ts` 只配置了 `@`，没有配置 `@scholar-ai/sdk` / `@scholar-ai/types`
4. 同时 `apps/web` 自身也没有把这两个包安装成实际依赖

结果：

1. `type-check` 能过
2. 某些运行场景也能过
3. 但进入 Vitest 后，`src/app/routes.test.tsx` 和 `src/app/pages/KnowledgeBaseDetail.test.tsx` 直接因 import 解析失败而挂掉

判断：

1. 这是当前前端最重要的问题之一。
2. 它说明前端依赖关系是“构建时 alias 勉强成立”，而不是“workspace 依赖真实成立”。

影响：

1. 测试环境与开发环境不一致，导致测试红灯不再可靠地区分“业务 bug”还是“环境 bug”。
2. 后续 SDK 扩展会不断放大这个问题。

建议：

1. 要么给 `vitest.config.ts` 补齐与 `vite.config.ts` 同步的 alias。
2. 要么把 `@scholar-ai/sdk` / `@scholar-ai/types` 变成真实 workspace 依赖，并让测试、构建、类型解析统一走同一条路径。

### 4.2 `ChatWorkspaceV2` 测试 mock 没有跟随实现演进，Chat 主工作台测试已经失真

证据：

1. `apps/web/src/features/chat/hooks/useChatHandoff.ts:43-80`
2. `apps/web/src/features/chat/workspace/ChatWorkspaceV2.test.tsx:11-14`
3. 同一测试文件失败日志：`No "useLocation" export is defined on the "react-router" mock`

现象：

1. `useChatHandoff()` 现在显式依赖 `useLocation()`
2. 但 `ChatWorkspaceV2.test.tsx` 的 `react-router` mock 只提供了 `useNavigate` 和 `useSearchParams`
3. 结果是两个关键用例都直接在测试基建层报错，而不是验证真实交互逻辑

判断：

1. 这说明 `ChatWorkspaceV2` 仍是重 orchestration 组件，任何新增依赖都会迅速让测试桩失效。
2. 现在的失败并不一定表示用户侧功能坏了，但它清楚表明“Chat 核心页面的测试壳没有跟上页面复杂度”。

影响：

1. Chat 页面未来再接 handoff、workflow、runtime hydration 时，测试很容易继续脆化。
2. 开发者会越来越倾向于“先跳过这组测试”，这对核心页面很危险。

建议：

1. `react-router` mock 改成 partial mock，保留真实导出，只覆盖需要的 hook。
2. 把 handoff、scope、session、streaming 的测试拆层，不要把所有依赖都塞进 `ChatWorkspaceV2` 单个大组件测试。

## 5. 中优先级问题

### 5.1 Dialog 组件存在 ref 告警，Radix 组合方式不够稳

证据：

1. `apps/web/src/app/components/ui/dialog.tsx:33-70`
2. 测试日志中明确出现：
   - `Function components cannot be given refs`
   - `Check the render method of SlotClone`

判断：

1. 这不是当前最致命的问题，但它说明 `DialogOverlay` / `DialogContent` 这套包裹层没有完全遵循 Radix 对 ref forwarding 的预期。
2. 继续堆复杂交互时，焦点管理、可访问性、动画时序都可能出边角问题。

建议：

1. 统一用 `React.forwardRef` 包装这些 primitive wrapper。

### 5.2 测试环境缺少 canvas 能力 mock，导致大量噪音警告

证据：

1. `apps/web/src/test/setup.ts`
2. `npm run test:run` 输出中大量出现：
   - `Not implemented: HTMLCanvasElement's getContext() method`

判断：

1. 这是典型的测试基建设施缺口。
2. 它本身未必是产品 bug，但会污染测试输出，降低开发者对真正错误的敏感度。

建议：

1. 在 `src/test/setup.ts` 里补统一 canvas mock，或为依赖 canvas 的组件做更明确的 stub。

### 5.3 `apiClient` 的全局重试/日志/Toast 策略过重，测试与非稳定环境噪音偏大

证据：

1. `apps/web/src/utils/apiClient.ts:150-315`
2. `Settings.test.tsx` 运行期间出现：
   - `GET /api/v1/users/me`
   - `Network Error`
   - 自动 retry 日志

判断：

1. 当前 `apiClient` 同时承担了请求、解包、401 refresh、网络重试、toast、日志等多重职责。
2. 在真实产品里这未必立刻坏，但在测试环境和边缘页面里，它已经开始制造过多副作用。

影响：

1. 页面测试更难隔离。
2. 当接口短暂失败时，UI 可能出现比预期更慢的失败反馈。

建议：

1. 给测试环境或部分查询型请求增加可关闭的 retry / toast 策略。
2. 进一步把 transport、auth refresh、ui feedback 这三层职责拆开。

### 5.4 `sessionsApi` 与 `chatApi` 同时混用 `apiClient` 和 `sdkHttpClient`，接口消费层不够统一

证据：

1. `apps/web/src/services/sessionsApi.ts:27-75`
2. `apps/web/src/services/chatApi.ts`
3. `apps/web/src/services/sdkHttpClient.ts`

现象：

1. 有的地方走 SDK client
2. 有的地方直接走 `apiClient`
3. 还有手动兼容 `response.data` / `response.data.data` 的分支

判断：

1. 这不是立即阻断的问题，但会持续增加接口层心智负担。
2. 一旦后端 envelope 或 SDK 行为再变，前端会出现“某些 service 正常、某些 service 又要手拆响应”的状况。

建议：

1. 统一 session/chat 这条线的 client 入口，减少手写兼容分支。

## 6. 正向信号

前端也有明确的正向证据：

1. `cd apps/web && npm run type-check`：passed
2. `81` 个测试文件中 `78` 个通过
3. `296` 个测试中 `294` 个通过
4. `KnowledgeWorkspaceShell`、`search import flow`、`workflow hydration` 等近期复杂交互相关测试大体可运行

这说明：

1. 前端主代码并没有处于全面断裂状态。
2. 当前主要短板集中在“测试环境一致性”和“核心 orchestrator 页面测试壳老化”。

## 7. 前端评分

本次基于当前证据给前端单独评分：

| 维度 | 分数 | 说明 |
|---|---:|---|
| UI/交互实现成熟度 | 7.5/10 | 主页面功能面较完整，近期工作流能力已实装不少 |
| 类型与静态约束 | 8.0/10 | `type-check` 通过，TS 基线较稳 |
| 测试基建可靠性 | 5.8/10 | 主要问题在测试环境与真实依赖解析不一致 |
| 依赖与工程一致性 | 5.8/10 | Vite/TS/Vitest 三套解析规则未完全统一 |
| 可维护性 | 6.5/10 | ChatWorkspaceV2 仍偏重，service 层消费方式不够统一 |
| 发布就绪度 | 6.6/10 | 日常开发可推进，但不适合忽略当前测试红灯 |

前端综合分：**6.7/10**

## 8. 建议修复顺序

建议按下面顺序收口：

1. 先统一 `Vite + TS + Vitest` 对 `@scholar-ai/sdk` / `@scholar-ai/types` 的解析方式
2. 再修 `ChatWorkspaceV2.test.tsx` 的 router mock，恢复 Chat 核心页面测试可信度
3. 给 `Dialog` wrapper 补 `forwardRef`
4. 给测试环境补 canvas mock，降低输出噪音
5. 统一 session/chat service 的 client 使用方式

## 9. 最终判断

前端现在最真实的状态不是“界面有很多明显坏点”，而是：

**产品层实现已经走到中后段，但工程层测试基建没有完全跟上，导致当前最大的风险来自工程一致性和核心页面测试脆弱性。**
