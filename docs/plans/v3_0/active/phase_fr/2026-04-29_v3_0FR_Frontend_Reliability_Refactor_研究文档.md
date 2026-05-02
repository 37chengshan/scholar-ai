# v3.0FR Frontend Reliability Refactor 研究文档

> 日期：2026-04-29  
> 状态：research  
> 上游依据：
> - `docs/plans/v3_0/reports/frontend/frontend-design-audit-2026-04-29.md`
> - `docs/specs/design/frontend/DESIGN_SYSTEM.md`
> - `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`
> - `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`
> - `apps/web/src/app/pages/Read.tsx`
> - `apps/web/src/app/pages/Notes.tsx`

## 1. 研究目标

本研究文档聚焦 `Chat / Knowledge Base / Read / Notes` 四个核心生产力页面，回答三个问题：

1. 当前真实代码中，哪些问题已经可以在一轮安全切片内直接修？
2. 哪些问题属于结构性重构，必须被拆成后续切片，不能在本轮混做？
3. 如何在不新造平行实现路径的前提下，为 `Phase F` 的产品化打磨先清障？

## 2. 当前实现基线

### 2.1 Chat

当前主入口已经是 `ChatWorkspaceV2`，且内部已经拆出了：

1. `message-feed/MessageFeed`
2. `composer-input/ComposerInput`
3. `ChatRightPanel`
4. 多个 workspace hook：`useChatWorkspace`、`useChatStreaming`、`useChatSend`、`useChatSessionController`

这说明 `Chat` 已经处于“半拆分完成”的状态，当前最大的工程问题不是缺少分层，而是：

1. 页面根仍然过重。
2. 仍保留 `ChatLegacy.tsx` 兼容桥。
3. 后续若继续把逻辑塞回根组件，会再次回到 giant page。

### 2.2 Knowledge Base

`KnowledgeWorkspaceShell` 已经将工作台拆成独立 panel，但仍存在两个高风险点：

1. 论文列表在大量数据下仍是完整 map 渲染。
2. `KnowledgeBaseDetailLegacy.tsx` 仍保留 bridge。

其中虚拟化是立刻可做、且收益明确的一项；而完整 IA 重新设计不应混入本轮。

### 2.3 Read

`Read.tsx` 已经具备阅读主流程，但以下偏好状态仍然留在页面本地：

1. `rightTab`
2. `isPanelOpen`
3. `isFullscreen`
4. `panelWidth`

其中 `panelWidth` 甚至仍直接使用页面内 `localStorage` 读写。这类状态属于“用户界面偏好”，应进入持久化 store，而不是继续散落在页面内部副作用中。

### 2.4 Notes

`Notes.tsx` 已经拥有 folder-first 工作流和本地持久化的手工文件夹，但仍有两个明显问题：

1. `selectedFolderId`、`tagFilter` 这类浏览偏好仍卡在页面局部状态。
2. 删除按钮默认 `opacity-0 group-hover:opacity-100`，在移动端和触屏设备上接近不可用。

## 3. 风险分层

### 3.1 本轮可安全落地

1. 删除 `ChatLegacy.tsx` 和 `KnowledgeBaseDetailLegacy.tsx` 这类无真实业务逻辑的 bridge。
2. 给 KB 论文列表加虚拟化。
3. 将 `Read / Notes` 的偏好状态外提到持久化 store。
4. 移除 Notes 列表中 Hover-only 的删除按钮策略。

### 3.2 本轮不应混入

1. `ChatWorkspaceV2` 的完整 Shell / Controller / Sections 三段式深拆。
2. `KnowledgeWorkspaceShell` 的整体 IA 重排。
3. `Compare / Review` 的完整 UI 重做。
4. 全站 Link 语义整改与 Button-Navigation 全量替换。

这些事项虽然方向正确，但都属于第二轮或第三轮重构，混入当前切片会显著提高回归风险。

## 4. 建议切片

### Slice 1：Reliability Cleanup

1. 删除无调用价值的 legacy bridge。
2. 给 KB 大列表加虚拟化。
3. 将 `Read / Notes` 偏好状态持久化。
4. 修复 `Notes` 的 Hover-only 删除交互。

### Slice 2：Controller Decomposition

1. 继续分解 `ChatWorkspaceV2`。
2. 收拢 `Read` 副作用与保存逻辑。

### Slice 3：Canonical Component Cleanup

1. 组件唯一实现审计。
2. 移除跨 feature 的平行卡片与 detail panel。

## 5. 推荐验证方式

1. `cd apps/web && npm run test:run -- ChatWorkspaceV2 KnowledgeWorkspaceShell`
2. `cd apps/web && npm run type-check`
3. 对 `Notes` 的删除按钮与 KB 列表的可见区域进行 UI 回归检查。

## 6. 结论

`v3.0FR` 的第一轮不应追求“彻底拆完所有大页面”，而应优先完成一组低风险、高杠杆、可立即验证的结构清障改动。这样既能响应审计报告中的痛点，也不会把当前主链页面再次拖入长周期不稳定状态。
