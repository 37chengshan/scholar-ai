---
phase_id: 5.0-6a
name: Chat Polish (Core)
owner: web-platform
status: not-started
created_at: 2026-05-31
last_verified_at: -
research_doc: docs/plans/v5_0/search/2026-05-31_v5_0_phase_6_chat_polish_research.md
depends_on:
  - v5_0_phase_4_read_pretext
  - v5_0_phase_5_notes_refactoring
---

## Phase 5.0-6a Chat Polish (Core) -- Execution Plan

### Objective

将 Chat 体验从"功能可用"打磨到"产品精致"：Message Feed 接入 virtualization 消除长对话性能瓶颈，Composer 补齐键盘快捷键与多行编辑，Citation Panel 从纯展示升级为可交互引用面板，SSE 状态系统化为统一用户可见反馈，CompareCard 与 Reasoning/ToolTimeline 视觉升级对齐设计系统 v2。

**范围边界：**
- 本 phase 只做 Chat 内部精修，不涉及 Chat↔Notes 双向桥（桥接功能拆入 5.0-6b）
- Chat↔Notes 桥（@ mention 笔记、push conclusion、@ chat session）依赖 5.0-7 后端 API，单独成 phase
- LEGACY FREEZE 决策：ChatWorkspaceV2.tsx 的 LEGACY FREEZE 注释已过期，本 phase 将其移除，所有新逻辑通过 extracted hooks 实现，ChatWorkspaceV2 仅做薄编排层

### Pre-conditions

| 条件 | 状态 |
|------|------|
| 5.0-4 Read + pretext closeout | **DONE** -- measureText 高度预测可复用 |
| 5.0-5 Notes Refactoring closeout | **DONE** -- MentionExtension 逻辑可复用（5.0-6b 阶段） |
| 5.0-1 Design System v2 | **DONE** -- token 可用于视觉升级 |
| 5.0-2 WorkspaceShell v2 | **DONE** -- 布局已就绪 |
| react-window 已安装 | **已确认** -- package.json 中存在但 chat 未使用 |

### Security Acceptance Criteria

本 phase 涉及的安全面：

| 子任务 | 安全要求 |
|--------|---------|
| T1 Virtualization | 无新用户输入面；确保 virtualized list 不泄露 off-screen 消息到 DOM（已有消息按 session 隔离） |
| T3 Composer 快捷键 | textarea maxLength 限制（默认 10000 字符）；快捷键不绕过现有输入验证 |
| T5 Citation Panel | citation_jump_url 来自 SSE 流数据，必须做 allowlist 校验（仅允许 `/read` 路由 + 同源 URL）；不直接 `window.open` 未校验 URL |
| T7 CompareCard | 无新输入面；确保 comparison 数据不泄露跨用户信息（已有 session 隔离） |
| T8 SSE 状态 | 错误 toast 不泄露后端内部错误详情；仅展示用户可理解的错误消息 |
| T9 a11y 基线 | 无直接安全面，但确保 assistive technology 不暴露隐藏内容 |

### Wave 1: Virtualization Foundation（无依赖，可立即启动）

#### Task 1.1 -- Message Feed Virtualization PoC

| 字段 | 值 |
|------|-----|
| **name** | T1: Message Feed 接入 react-window VariableSizeList |
| **files** | `apps/web/src/features/chat/components/message-feed/MessageFeed.tsx`, `apps/web/src/features/chat/hooks/useMeasuredMessages.ts`, `apps/web/src/features/chat/components/message-feed/VirtualizedMessageList.tsx`（新建） |
| **action** | 1. 新建 `VirtualizedMessageList.tsx`，封装 `VariableSizeList` 作为 MessageFeed 的 virtualization 层<br>2. 将 `useMeasuredMessages` 的高度预估接入 `itemSize` 回调；对无法预估的消息使用 fallback 高度（200px）<br>3. MessageFeed 保留 `.map()` 作为 < 20 条消息的 fast-path，>= 20 条时切换到 VirtualizedMessageList<br>4. 每个消息 item renderer 保持现有组件（ReasoningPanel、ToolTimelinePanel、CitationPanel、EvidencePanel），仅外层包裹 virtualization row<br>5. 确保 `overscanCount=5` 防止快速滚动白屏<br>6. 移除 ChatWorkspaceV2.tsx 的 LEGACY FREEZE 注释（已过期） |
| **verify** | `cd apps/web && npm run type-check` 通过；`npm run test:run` 无新增失败；手动验证 200 条消息场景下滚动流畅（无 jank）；DOM 节点数从 O(n) 降至 O(overscan) |
| **done** | VirtualizedMessageList 存在且被 MessageFeed 条件使用；200 条消息场景 DOM 节点数 < 30；scrollbar 行为与当前一致（偏差 < 10%） |
| **type** | feat |

#### Task 1.2 -- Streaming 动态高度重算

| 字段 | 值 |
|------|-----|
| **name** | T2: Streaming 期间 VariableSizeList 动态高度重算 |
| **files** | `apps/web/src/features/chat/components/message-feed/VirtualizedMessageList.tsx`, `apps/web/src/features/chat/hooks/useMeasuredMessages.ts` |
| **action** | 1. 在 streaming 状态下，当新 token 到达导致消息高度变化时，调用 `listRef.current.resetAfterIndex(changedIndex)` 触发重算<br>2. 对 streaming 消息使用 `ResizeObserver` 监测实际 DOM 高度，而非仅依赖 `measureText` 预估<br>3. 高度变化回调防抖 100ms，避免 streaming 期间每 token 都触发 `resetAfterIndex`<br>4. streaming 消息完成后（`isStreaming=false`），将其高度从预估切换为实测值并做最终 `resetAfterIndex`<br>5. 保留 `usePinnedBottom` 的 scroll-to-bottom 行为：virtualization 模式下在 `onItemsRendered` 回调中检测是否 pinned |
| **verify** | `npm run type-check` 通过；手动验证 streaming 场景：消息高度随内容增长正确撑开，scrollbar 不跳动；pinned-bottom 行为在 streaming 期间正常工作 |
| **done** | streaming 消息高度实时更新无 layout shift；pinned-bottom 在 virtualization 模式下正常工作；`resetAfterIndex` 调用频率 <= 10次/秒 |
| **type** | feat |

#### Task 1.3 -- Pinned-Bottom 与 Virtualization 集成

| 字段 | 值 |
|------|-----|
| **name** | T3: usePinnedBottom 与 VariableSizeList 集成 |
| **files** | `apps/web/src/features/chat/hooks/usePinnedBottom.ts`, `apps/web/src/features/chat/components/message-feed/VirtualizedMessageList.tsx` |
| **action** | 1. `usePinnedBottom` 增加 virtualization 模式：当列表使用 VariableSizeList 时，通过 `onItemsRendered` 回调判断是否已滚动到底部<br>2. pinned 状态下新消息到达时，调用 `listRef.current.scrollToItem(items.length - 1, 'end')`<br>3. 用户手动向上滚动 > 100px 时自动取消 pinned，显示 "↓ New messages" 浮层按钮<br>4. 点击浮层按钮恢复 pinned 并滚动到底部<br>5. 保持非 virtualization 模式（< 20 条消息）的现有行为不变 |
| **verify** | `npm run type-check` 通过；手动验证：streaming 期间自动跟随底部，手动上滚取消 pinned，点击浮层恢复；非 virtualization 模式行为不变 |
| **done** | pinned-bottom 在两种模式下均正确工作；"↓ New messages" 浮层在取消 pinned 时显示 |
| **type** | feat |

---

### Wave 2: Composer UX + Citation Panel（依赖 Wave 1 完成或可并行）

#### Task 2.1 -- Composer 键盘快捷键

| 字段 | 值 |
|------|-----|
| **name** | T3: Composer 快捷键系统（Cmd+B/I/K, Escape, /commands） |
| **files** | `apps/web/src/features/chat/components/composer-input/ComposerInput.tsx`, `apps/web/src/features/chat/components/composer-input/useComposerShortcuts.ts`（新建） |
| **action** | 1. 新建 `useComposerShortcuts.ts` hook，封装 textarea 键盘事件处理<br>2. 实现快捷键：<br>  - `Cmd/Ctrl+B`：插入 `**bold**` 包裹选中文本<br>  - `Cmd/Ctrl+I`：插入 `*italic*` 包裹选中文本<br>  - `Cmd/Ctrl+K`：插入 `[text](url)` 链接模板<br>  - `Escape`：清空当前输入或取消 streaming<br>  - `/` 行首：触发 slash commands 下拉（`/rag`, `/agent`, `/compare`）<br>3. slash commands 下拉使用 Radix Popover，支持键盘上下选择 + Enter 确认<br>4. textarea 设置 `maxLength={10000}` 防止超长输入<br>5. 保持现有 Enter 发送 / Shift+Enter 换行行为不变 |
| **verify** | `npm run type-check` 通过；新增 `useComposerShortcuts.test.ts` 覆盖每个快捷键；手动验证所有快捷键在 textarea 中正确触发 |
| **done** | 5 个快捷键全部可用；slash commands 下拉可键盘导航；maxLength 限制生效 |
| **type** | feat |

#### Task 2.2 -- Citation Panel 交互化

| 字段 | 值 |
|------|-----|
| **name** | T5: Citation Panel 按 paper 分组 + 点击跳转源 |
| **files** | `apps/web/src/features/chat/components/citation-panel/CitationPanel.tsx`, `apps/web/src/features/chat/components/citation-panel/CitationGroup.tsx`（新建）, `apps/web/src/features/chat/components/citation-panel/useCitationNavigation.ts`（新建） |
| **action** | 1. 将 CitationPanel 从 33 行薄包装升级为独立交互组件<br>2. 新建 `CitationGroup.tsx`：按 paper 分组展示 citations，每个 paper 一个折叠组<br>3. 新建 `useCitationNavigation.ts`：点击 citation 时跳转到 Read 页对应位置，复用 `useEvidenceNavigation.jumpToSource`<br>4. citation_jump_url 做 allowlist 校验：仅允许同源 `/read?paperId=xxx&page=yyy` 格式，拒绝外部 URL<br>5. 支持 citation 过滤：按 paper 名称搜索<br>6. 保留 EvidencePanel 的独立存在（不合并），但建立 citation → evidence 的视觉关联 |
| **verify** | `npm run type-check` 通过；新增 `CitationPanel.test.tsx` 覆盖分组、过滤、跳转；跳转 URL 校验测试覆盖恶意 URL 场景 |
| **done** | CitationPanel 按 paper 分组展示；点击 citation 跳转到 Read 页；allowlist 校验拒绝外部 URL |
| **type** | feat |

#### Task 2.3 -- Composer 多行编辑增强

| 字段 | 值 |
|------|-----|
| **name** | T6: Composer 多行 auto-height + Markdown 预览 toggle |
| **files** | `apps/web/src/features/chat/components/composer-input/ComposerInput.tsx`, `apps/web/src/features/chat/components/composer-input/MarkdownPreview.tsx`（新建） |
| **action** | 1. textarea auto-height 已有基础，确保 max-height 限制（200px）后出现内部滚动<br>2. 新建 `MarkdownPreview.tsx`：toggle 按钮切换编辑/预览模式，预览使用 `react-markdown` 渲染<br>3. 预览模式下禁用 textarea 编辑，显示渲染后的 Markdown<br>4. 输入区域底部显示字符计数（`{n}/10000`）<br>5. 保持现有 auto-height 行为不变 |
| **verify** | `npm run type-check` 通过；手动验证 auto-height 上限、Markdown 预览切换、字符计数显示 |
| **done** | textarea 在 200px 后内部滚动；Markdown 预览 toggle 可用；字符计数显示 |
| **type** | feat |

---

### Wave 3: Visual Polish + SSE Systematization（可与 Wave 2 并行）

#### Task 3.1 -- CompareCard UI 重做

| 字段 | 值 |
|------|-----|
| **name** | T7: CompareCard 视觉重做对齐设计系统 v2 |
| **files** | `apps/web/src/features/chat/components/CompareCard.tsx`, `apps/web/src/features/chat/components/CompareCard.test.tsx` |
| **action** | 1. CompareCard 使用设计系统 v2 token（surface、accent、text semantic colors）<br>2. 表格布局改为 card-based 布局：每个 compared paper 一个 card，差异点用 accent 色高亮<br>3. 添加 hover/focus 状态（`transition: var(--duration-fast)`）<br>4. 保留现有数据接口（`CompareCardProps` 不变），仅改视觉层<br>5. 更新现有测试以匹配新 DOM 结构 |
| **verify** | `npm run type-check` 通过；`npm run test:run` 中 CompareCard 测试通过；视觉上对齐设计系统 v2 token |
| **done** | CompareCard 使用 v2 token；card-based 布局；hover/focus 状态就绪 |
| **type** | refactor |

#### Task 3.2 -- Reasoning/ToolTimeline 视觉升级

| 字段 | 值 |
|------|-----|
| **name** | T8: ReasoningPanel + ToolTimelinePanel 视觉与状态语义升级 |
| **files** | `apps/web/src/features/chat/components/reasoning-panel/ReasoningPanel.tsx`, `apps/web/src/features/chat/components/tool-timeline-panel/ToolTimelinePanel.tsx` |
| **action** | 1. ReasoningPanel 使用 v2 token，thinking 状态用 pulse 动画（`animation: var(--ease-out-expo)`）<br>2. ToolTimelinePanel 的步骤指示器从纯文本改为 stepper 组件（dot + line + dot）<br>3. 每个工具步骤状态（pending/running/done/error）用 semantic color 区分<br>4. 错误状态显示可展开的错误详情（默认折叠）<br>5. 保持现有 props 接口不变 |
| **verify** | `npm run type-check` 通过；手动验证四种状态的视觉区分；错误详情可展开/折叠 |
| **done** | 两个 panel 使用 v2 token；stepper 视觉就绪；错误状态可展开 |
| **type** | refactor |

#### Task 3.3 -- SSE 状态系统化

| 字段 | 值 |
|------|-----|
| **name** | T9: SSE 统一状态 overlay + toast + retry |
| **files** | `apps/web/src/features/chat/state/chatWorkspaceStore.ts`, `apps/web/src/features/chat/components/StreamStatusOverlay.tsx`（新建）, `apps/web/src/features/chat/components/StreamStatusToast.tsx`（新建） |
| **action** | 1. 在 `chatWorkspaceStore` 中新增 `streamStatus` 字段：`idle \| connecting \| streaming \| completed \| error \| cancelled \| retrying`<br>2. 新建 `StreamStatusOverlay.tsx`：streaming 期间在消息底部显示轻量状态条（"Thinking..." / "Searching papers..." / "Generating..."）<br>3. 新建 `StreamStatusToast.tsx`：error/cancelled 状态显示 toast，error toast 包含 retry 按钮<br>4. `useChatStreaming` 中的 SSE 事件映射到 `streamStatus` 状态机<br>5. error toast 不泄露后端内部错误详情，仅展示用户可理解消息（"Connection lost. Retrying..." / "Request failed. Please try again."）<br>6. 移除 `useChatStream.ts` 中的 `console.debug` 调用（lines 459, 461, 489, 625），改为 `if (import.meta.env.DEV)` 守卫 |
| **verify** | `npm run type-check` 通过；新增 `StreamStatusOverlay.test.tsx` 和 `StreamStatusToast.test.tsx`；手动验证 error → retry 流程 |
| **done** | streamStatus 状态机覆盖 7 种状态；overlay 在 streaming 时显示；toast 在 error 时显示且含 retry；console.debug 已守卫 |
| **type** | feat |

---

### Wave 4: A11y Baseline（贯穿全部 wave）

#### Task 4.1 -- Message List 无障碍基线

| 字段 | 值 |
|------|-----|
| **name** | T10: Message Feed a11y -- role="log" + aria-live + keyboard nav |
| **files** | `apps/web/src/features/chat/components/message-feed/MessageFeed.tsx`, `apps/web/src/features/chat/components/message-feed/VirtualizedMessageList.tsx` |
| **action** | 1. MessageFeed 容器添加 `role="log"` 和 `aria-live="polite"`（新消息到达时 screen reader 自动播报）<br>2. 每条消息添加 `role="article"` + `aria-label`（包含发送者和时间戳）<br>3. VirtualizedMessageList 的 off-screen items 设置 `aria-hidden="true"`<br>4. 键盘导航：`j/k` 在消息间移动焦点（复用 Read 页的键盘导航模式）<br>5. Composer dropdown（slash commands）添加 `role="menu"` / `role="menuitem"` + `aria-expanded` + 键盘上下导航 |
| **verify** | `npm run type-check` 通过；手动 screen reader 测试（VoiceOver）：新消息到达时自动播报；`j/k` 可在消息间移动；slash commands dropdown 可键盘操作 |
| **done** | `role="log"` + `aria-live="polite"` 已添加；`j/k` 键盘导航可用；dropdown 可键盘操作 |
| **type** | feat |

---

### Success Criteria

| # | 验收标准 | 验证方式 |
|---|---------|---------|
| SC1 | 200 条消息场景下 Message Feed 滚动无 jank，DOM 节点数 < 30 | 手动验证 + Performance tab profiling |
| SC2 | Streaming 期间消息高度无 layout shift（CLS < 0.1） | Lighthouse CLS 测量 |
| SC3 | Composer 5 个快捷键全部可用，slash commands 下拉可键盘导航 | 手动验证 + 单元测试 |
| SC4 | CitationPanel 按 paper 分组，点击跳转到 Read 页，allowlist 拒绝外部 URL | 手动验证 + 单元测试（含恶意 URL） |
| SC5 | CompareCard / ReasoningPanel / ToolTimelinePanel 使用设计系统 v2 token | 视觉审查 |
| SC6 | SSE 状态覆盖 7 种状态，error toast 含 retry 且不泄露后端详情 | 手动验证 + 单元测试 |
| SC7 | Message Feed 有 `role="log"` + `aria-live`，`j/k` 键盘导航可用 | VoiceOver 手动测试 |
| SC8 | `npm run type-check` 零错误；`npm run test:run` 无新增失败 | CI |
| SC9 | 新增测试文件 >= 6 个，覆盖 virtualization、shortcuts、citation、SSE 状态、a11y | 测试覆盖率报告 |
| SC10 | 所有新文件 < 400 行，所有修改文件 < 800 行 | `wc -l` 检查 |

### Known Risks

| 风险 | 级别 | 缓解 |
|------|------|------|
| react-window VariableSizeList 与 streaming 动态高度冲突 | 高 | T2 专门处理；备选：streaming 消息保持 DOM 渲染，仅已完成消息 virtualize |
| measureText 预估偏差 > 20% 导致 scrollbar 跳动 | 中 | T1 阶段做 PoC 验证，overscanCount=5 兜底 |
| LEGACY FREEZE 移除后引入回归 | 低 | ChatWorkspaceV2 仅移除注释，不改逻辑；新逻辑全在 extracted hooks |
| Composer 快捷键与浏览器原生快捷键冲突 | 低 | `Cmd+B/I/K` 在 textarea 中是标准 Markdown 快捷键，不与浏览器冲突 |

### Not in Scope (5.0-6b)

以下功能拆入 Phase 5.0-6b（Chat-Notes Bridge），依赖 5.0-7 后端 API：

1. Composer @ mention 笔记（需复用 5.0-5 MentionExtension，需后端 mention search API）
2. Chat→Notes "Push conclusion to notes"（需后端 notes mutation API）
3. Notes→Chat @ chat session 引用（需后端 chat session search API）
4. Notes 选中文本发送到 Chat（前端可独立做，但与桥接功能打包）

### Test Plan

| 测试文件 | 覆盖内容 | 类型 |
|----------|---------|------|
| `VirtualizedMessageList.test.tsx` | virtualization 切换阈值、itemSize 回调、overscan | unit |
| `useComposerShortcuts.test.ts` | 每个快捷键触发、slash commands 选择 | unit |
| `CitationPanel.test.tsx` | 分组、过滤、跳转 URL 校验 | unit |
| `StreamStatusOverlay.test.tsx` | 7 种状态渲染 | unit |
| `StreamStatusToast.test.tsx` | error toast + retry 按钮 | unit |
| `CompareCard.test.tsx` | 更新现有测试匹配新 DOM | unit |
| `chatWorkspaceStore.test.ts` | streamStatus 状态机转换 | unit |
| `message-feed-a11y.spec.ts` | role="log"、aria-live、j/k 导航 | e2e |

总计新增/修改测试文件 >= 8 个。
