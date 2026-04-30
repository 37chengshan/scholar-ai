# Chat 页面前端重构清单（可直接丢给 GPT-5.3 Codex 执行）

## 目标

把当前 chat 页面从“单个超重组件 + 双重流式动画 + 激进自动滚动 + 多状态源并存”改成“单一消息真源 + 单一 SSE 入口 + 稳定滚动 + 可拆分组件”的结构。

这不是视觉微调任务，而是 **前端渲染链路收口任务**。

## 已观察到的真实现状

1. `apps/web/src/features/chat/components/ChatLegacy.tsx` 只是桥接到 `ChatWorkspaceV2.tsx`，并没有真正的 legacy fallback。
2. `apps/web/src/features/chat/components/ChatRunContainer.tsx` 的 gate 实际没有形成有效 A/B，对排错帮助很弱。
3. `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx` 同时承担：scope 校验、session 切换、local message、placeholder、SSE 事件消费、滚动、右侧面板、confirmation、删除确认。
4. `apps/web/src/features/chat/components/message-feed/MessageFeed.tsx` 在 streaming assistant message 上使用了 `TypingText`，而上游本来就在做真实流式更新，形成“双重打字动画”。
5. `ChatWorkspaceV2.tsx` 里存在 `localMessages + sessionMessages + streamState + placeholderId + currentMessageIdRef` 多状态并存。
6. `ChatWorkspaceV2.tsx` 里对 `localMessages` 和 `streamState.contentBuffer` 的变化都执行 `scrollIntoView({ behavior: 'smooth' })`，会导致持续抢滚动。
7. `apps/web/src/features/chat/state/chatWorkspaceStore.ts` 已存在，但目前承接的业务状态还太薄，没形成真正的工作台状态真源。
8. `apps/web/src/features/chat/hooks/useChatStreaming.ts` 只是对 `app/hooks/useChatStream.ts` 做了一层浅包装，还没有成为真正的 feature 级入口。

## 最终目标状态

### 必须达到

- streaming 阶段不再使用伪打字动画
- 消息列表只有一个 canonical source of truth
- 自动滚动改为 pinned-bottom 机制，而不是每个 chunk 都 smooth scroll
- reasoning / tool timeline 不再反复挤压正文布局
- chat 页面组件拆分后，`ChatWorkspaceV2.tsx` 只负责组装，不再负责完整业务编排
- SSE 事件消费路径只有一条
- 右侧面板、当前消息选中、session 切换状态由 feature store 承接

### 明确不要做

- 不要顺手大改视觉主题
- 不要改动后端 SSE 协议
- 不要把新的业务逻辑继续塞回 `ChatWorkspaceV2.tsx`
- 不要引入新的第二套 chat store
- 不要保留 streaming 阶段 `TypingText`

---

## 执行顺序（按文件列出修改顺序）

## 阶段 0：先止血，不做大拆分

### 0.1 修改 `apps/web/src/features/chat/components/message-feed/MessageFeed.tsx`

#### 任务

- 删除 streaming assistant message 对 `TypingText` 的使用
- streaming 状态下直接渲染真实内容
- 可以保留一个简洁 cursor，但不要再用 interval/逐字补全
- `ReasoningPanel` / `ToolTimelinePanel` 的可见性计算抽成局部 helper，避免每次 render 都重新拼复杂条件

#### 验收

- assistant streaming 内容随真实 chunk 增长
- 不再出现“文本已经到 state 里，但视觉上还在慢慢补字”的现象
- markdown/citation 文本不因伪打字而闪烁

---

### 0.2 修改 `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`

#### 任务

- 删除当前基于 `localMessages` / `streamState.contentBuffer` 的全量 `smooth scroll` 逻辑
- 改成 pinned-bottom：
  - 新增 `isPinnedToBottom`
  - 用户距离底部阈值内时才自动跟随
  - streaming 中只允许低频滚动或 instant 对齐
  - 用户手动上滑后，停止强制滚动
- 不要在本阶段做大范围逻辑迁移，只替换滚动策略

#### 建议新增

- `apps/web/src/features/chat/hooks/usePinnedBottom.ts`

#### 验收

- streaming 时页面不再持续抢滚动
- 用户手动上滑查看历史消息时，不会被拉回底部
- done 后会自动完成一次最终对齐

---

## 阶段 1：拆掉“假 rollout”，清理页面边界

### 1.1 修改 `apps/web/src/features/chat/components/ChatLegacy.tsx`

#### 任务

- 保留该文件，但只作为过渡壳
- 不要继续让它承载任何逻辑
- 文件注释里明确：legacy bridge only

### 1.2 修改 `apps/web/src/features/chat/components/ChatRunContainer.tsx`

#### 任务

- 如果当前 gate 不能提供真实双实现，就不要让它继续制造“有 fallback”的假象
- 二选一：
  - 方案 A：保留 gate，但让 fallback 指向一个真实的旧实现
  - 方案 B：直接固定使用 V2，并在注释中声明 rollout 已结束

#### 建议

当前仓库更适合 **方案 B**。

#### 验收

- 代码阅读者可以一眼看清当前生产实现是谁
- 不再存在“看上去能回退，实际上回不了”的假安全感

---

## 阶段 2：把工作台状态真正落到 feature store

### 2.1 修改 `apps/web/src/features/chat/state/chatWorkspaceStore.ts`

#### 任务

把这个 store 从“薄状态壳”扩成真正的工作台状态承载层。至少承接：

- `selectedSessionId`
- `selectedMessageId`
- `rightPanelOpen`
- `composerDraft`
- `mode`
- `scope`
- `isPinnedToBottom`
- `streamingMessageId`
- `pendingDeleteSessionId`
- `recoveryBannerVisible`

#### 不要放进去的内容

- 真实 message 列表正文 buffer
- SSE transport 实例
- 巨量服务对象

message 正文真源仍应该由 chat view model / hook 管理，而不是所有东西都丢进 zustand。

---

### 2.2 修改 `apps/web/src/features/chat/hooks/useChatWorkspace.ts`

#### 任务

- 让它成为真正的 workspace 组装入口，而不是只做浅层 selector
- 接管：
  - scope → mode 的映射
  - right panel 开关
  - delete session 对话框状态
  - selected message / selected run 这类 UI 选择状态
- 让页面组件通过这个 hook 获取工作台状态，而不是在 `ChatWorkspaceV2.tsx` 里散落一堆 `useState`

#### 验收

- `ChatWorkspaceV2.tsx` 中 UI 类 `useState` 显著减少
- scope / mode / rightPanel 状态不再双处维护

---

## 阶段 3：把 message 真源收口

### 3.1 修改 `apps/web/src/features/chat/hooks/useChatMessagesViewModel.ts`

#### 任务

把它升级成 **消息真源的唯一入口**。它要负责：

- 把 `sessionMessages` 作为 canonical persisted messages
- 把 streaming 临时态和 placeholder 替换逻辑收口成 view-model
- 暴露给页面的是一个稳定的 `renderMessages`
- 页面层不再自己决定“什么时候 sync localMessages，什么时候跳过 sync”

#### 这里必须做的重构

- 去掉页面层的 `localMessages` 主导权
- placeholder 机制保留，但变成 view-model 内部逻辑
- 暴露给页面的每条消息都带完整渲染字段：
  - `displayContent`
  - `displayReasoning`
  - `displayToolTimeline`
  - `displayCitations`
  - `isStreaming`
  - `isPlaceholder`

#### 验收

- 页面组件不再自己 map 原始 message + streamState 拼内容
- `localMessages` 逐步退出 `ChatWorkspaceV2.tsx`

---

### 3.2 修改 `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`

#### 任务

- 去掉 `localMessages` 作为页面主状态
- 只消费 `useChatMessagesViewModel()` 暴露的 `renderMessages`
- 去掉“streaming 时不 sync sessionMessages”的页面级补丁逻辑
- `selectedMessage` 应从 render messages 派生，不要再靠页面本地维护一个不稳定副本

#### 验收

- 页面层不再直接持有“用户消息 + placeholder + 完成消息”的完整拼装责任
- `ChatWorkspaceV2.tsx` 体积明显下降

---

## 阶段 4：把发送和 streaming orchestration 从页面里挪走

### 4.1 新增 `apps/web/src/features/chat/hooks/useChatSend.ts`

#### 任务

把 `handleSend` 从 `ChatWorkspaceV2.tsx` 中拆出去。

职责只包括：

- session ensure
- scope/mode 到 request body 的映射
- placeholder 创建信号
- stream 启动
- onDone / onError / onCancel 收尾

#### 不要在这里做的事

- 直接操作 DOM 滚动
- 拼右侧面板 UI
- 处理引用跳转

---

### 4.2 修改 `apps/web/src/features/chat/hooks/useChatStreaming.ts`

#### 任务

- 不再只是 `useChatStream()` 的浅包装
- 让它成为 feature 层唯一 streaming 入口
- 对外暴露：
  - `startRun`
  - `stopRun`
  - `streamState`
  - `currentMessageId`
  - `confirmation`
- 屏蔽 `app/hooks/useChatStream.ts` 的低层细节

#### 验收

- `ChatWorkspaceV2.tsx` 不再直接编排 `startStream / handleSSEEvent / forceFlush / cancelStream`

---

### 4.3 修改 `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`

#### 任务

移除以下页面内聚职责：

- `handleSend`
- `handleStop`
- 大部分 SSE onMessage/onDone/onError 细节
- confirmation 恢复流的连接细节

页面只保留：

- 组件组装
- 用户事件转发
- 引用跳转
- 少量展示型计算

---

## 阶段 5：拆页面骨架

### 5.1 新增 `apps/web/src/features/chat/components/ChatHeader.tsx`

负责：

- 当前 session 标题
- 右侧栏开关
- 非正文类顶栏控件

### 5.2 新增 `apps/web/src/features/chat/components/ChatRightPanel.tsx`

负责：

- AgentStateSidebar
- TokenMonitor
- 未来 recovery / artifacts 区域

### 5.3 保留并精简 `apps/web/src/features/chat/components/message-feed/MessageFeed.tsx`

负责：

- 只接收 render-ready messages
- 不再拥有复杂业务分支

### 5.4 保留并精简 `apps/web/src/features/chat/components/composer-input/ComposerInput.tsx`

负责：

- draft 输入
- mode 切换
- send 触发
- Enter/Shift+Enter 行为

### 5.5 修改 `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`

最终让它只做：

- `SessionSidebar`
- `ChatHeader`
- `ScopeBanner`
- `MessageFeed`
- `ComposerInput`
- `ChatRightPanel`
- `ConfirmationDialog`
- `ConfirmDialog`

#### 验收

- 该文件不再是 1000 行级大组件
- 页面读起来能一眼看出结构与职责

---

## 阶段 6：收 reasoning / tool panel 的布局策略

### 6.1 修改 `apps/web/src/features/chat/components/reasoning-panel/ReasoningPanel.tsx`
### 6.2 修改 `apps/web/src/features/chat/components/tool-timeline/ToolTimelinePanel.tsx`
### 6.3 修改 `apps/web/src/features/chat/components/message-feed/MessageFeed.tsx`

#### 任务

- 不再让 reasoning/tool timeline 在正文气泡上方反复增删导致整体高度跳动
- 至少做到以下两点之一：
  - 方案 A：进入右侧固定面板
  - 方案 B：正文内保留固定占位 / 折叠容器，避免 chunk 到来时高度剧烈变化

#### 建议

当前仓库更适合：

- streaming 期的 reasoning/tool 活动主展示放右侧栏
- 正文内仅保留轻量摘要/折叠入口

---

## 阶段 7：测试补齐

### 7.1 修改 `apps/web/src/features/chat/components/message-feed/MessageFeed.test.tsx`

补测试：

- streaming message 不走 `TypingText`
- 引用渲染与点击不回退
- stop 按钮仅对 streaming assistant message 可见

### 7.2 修改 `apps/web/src/features/chat/hooks/useChatRun.test.tsx`

补测试：

- send → placeholder → real message id 替换
- stale message_id 事件被忽略
- done/error/cancel 后 terminal state 正确

### 7.3 新增 `apps/web/src/features/chat/hooks/usePinnedBottom.test.tsx`

补测试：

- pinned 状态下自动跟随
- 用户手动上滑后停止跟随
- done 后最终对齐

### 7.4 修改 `apps/web/src/features/chat/adapters/sseEventAdapter.test.ts`

补测试：

- 仅 canonical 事件进入业务层
- legacy alias 不再穿透到页面组件

---

## 建议 commit 切片

### Commit 1
- remove streaming TypingText
- add pinned-bottom scroll behavior

### Commit 2
- clarify chat rollout boundary
- clean ChatLegacy / ChatRunContainer

### Commit 3
- expand chatWorkspaceStore and useChatWorkspace

### Commit 4
- move message truth to useChatMessagesViewModel

### Commit 5
- extract useChatSend and feature-level useChatStreaming

### Commit 6
- split ChatWorkspaceV2 into header/right-panel/composition shell

### Commit 7
- stabilize reasoning/tool panel layout

### Commit 8
- add chat render and scroll tests

---

## 完成定义

满足以下条件才算完成，不接受“差不多”：

- `TypingText` 不再用于真实 streaming assistant message
- 页面不再每个 chunk 都 `smooth scroll`
- `ChatWorkspaceV2.tsx` 不再直接承担完整发送与流编排
- render messages 只有一个真源
- terminal state 下不会继续接受 streaming 更新
- 关键单测全部通过
- 手工验证以下路径稳定：
  - 新建会话 → 发送消息 → stream → done
  - stop/cancel
  - session 切换后再发送
  - `paperId` / `kbId` scope 下发送
  - 展开/收起右侧栏时正文不抖动

---

## 给 Codex 的执行约束

1. 先做阶段 0 和阶段 1，再做后续拆分。
2. 每完成一个阶段都运行前端 type-check 和相关 vitest。
3. 不要同时重写 chat 页面和 chat 协议；协议收口放到另一份文档执行。
4. 所有新增 hook / component 必须放在 `apps/web/src/features/chat/*`，不要再回流到 `app/*`。
5. 如果发现现有 hook 无法安全复用，允许在 `features/chat/hooks` 新建实现，但不要保留两套对外入口。
6. 可参考 `assistant-ui` 的 streaming / auto-scroll / composable primitives 思路，但不要整库迁入。
