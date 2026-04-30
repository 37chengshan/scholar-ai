# ChatWorkspaceV2 下一步意见

## 结论

`apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx` 目前仍有 855 行，不是因为 Battle C 又往里面塞了大量新业务，而是因为它还承担了四类编排职责：

1. URL scope 解析与校验
2. session 生命周期与删除确认
3. stream/runtime/store 三套状态的桥接
4. 页面级 UI 组装与副作用调度

Battle C 做的是“把系统接通”，不是“把页面彻底重构干净”。因此这次改动优先把 runtime 真状态接进来，但没有继续在同一 PR 内做高风险拆文件。

## 为什么现在还不能直接继续往里加逻辑

文件顶部已经写明 `LEGACY FREEZE`，而且当前长度说明它已经是页面编排层，不适合继续承接：

- scope 解析副作用
- SSE / confirmation 恢复流
- session 切换清理
- runtime 与 workspace store 同步
- 右侧面板与 message feed 的页面装配

如果再把新逻辑继续堆进这个文件，下一轮会出现两个问题：

1. 调试范围越来越大，任何 stream 问题都要回到单文件排查
2. Battle B runtime、Battle C workspace store、legacy stream state 的边界会重新变模糊

## 我的具体建议

### Phase 1：只拆“页面编排副作用”，不改行为

优先拆出 3 个 hook，目标是把副作用从页面主体拿掉，但不改变任何用户可见行为。

1. `useChatScopeController`
   - 输入：`searchParams`, `setSearchParams`, `setWorkspaceScope`, `setMode`
   - 输出：`scope`, `scopeLoading`, `handleExitScope`
   - 吸收内容：`paperId/kbId` 校验、title 拉取、error scope、auto/rag mode 切换

2. `useChatSessionController`
   - 输入：`useSessions` 返回值、`runtime.resetRun`, `resetRun`, `resetForSessionSwitch`
   - 输出：`handleNewSession`, `handleSwitchSession`, `handleDeleteSession`, `confirmDeleteSession`, `cancelDeleteSession`
   - 吸收内容：session 新建/切换/删除相关清理逻辑

3. `useChatRuntimeBridge`
   - 输入：`runtime`, `streamState`, `setActiveRun`, `setSelectedRunId`, `setActiveRunStatus`, `setPendingActions`, `setRecoveryBannerVisible`, `setRunArtifactsPanelOpen`
   - 输出：`ingestRuntimeEvent`, `handleConfirmation`
   - 吸收内容：runtime/store 同步、terminal fallback、confirmation SSE 恢复流

### Phase 2：把页面壳体变成纯装配层

当上面 3 个 hook 稳定后，`ChatWorkspaceV2` 只保留：

- 基础 refs
- 少量局部 UI state
- hooks 组合
- JSX 布局

目标是把主文件压到 300 到 400 行，变成真正的页面容器，而不是混合 orchestrator。

### Phase 3：继续缩窄状态边界

Battle C 后面最该做的不是继续美化 UI，而是减少多状态源并存：

1. 明确 `useChatStreaming` 只负责文本流与消息缓冲
2. 明确 `useRuntime` 只负责 run protocol 真状态
3. 明确 workspace store 只存页面级共享 UI 状态，不再承担隐式 run 推导

如果这一层不收口，之后任何“重试 / 恢复 / 验证 / timeline”问题都会在三套状态之间来回跳。

## 不建议现在做的事

- 不建议把 Notes 一起拖进这轮重构
- 不建议顺手重写 Chat message 渲染层
- 不建议在同一 PR 里再动 Search / Read / KB 的 workflow hydration
- 不建议先做视觉重构，再做状态边界收口

这些都不是现在的主要矛盾。

## 建议的执行顺序

1. 先修 `contract-gate` 误报，保证 PR 能过
2. 新开一个小 PR，只做 `useChatScopeController`
3. 再开一个小 PR，抽 `useChatRuntimeBridge`
4. 最后把 `ChatWorkspaceV2` 收成纯页面装配层

## 完成标准

下一轮如果要说“ChatWorkspaceV2 已经收口”，我的标准是：

- 文件长度降到 400 行以内
- 不再直接写 scope 校验副作用
- 不再直接写 confirmation SSE 恢复流
- 不再直接写 runtime/store 同步副作用
- 页面文件里只保留布局装配和少量 UI 本地 state

在这之前，它仍然只是“能工作”，还不能算“结构上健康”。