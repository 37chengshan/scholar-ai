---
owner: web-platform
status: in-progress
depends_on:
  - PR5
last_verified_at: 2026-04-17
evidence_commits:
  - 9a7332e
  - 9208b73
  - cecfccf
  - wip-review-2026-04-17
---

# PR10：KB / Chat / Search 从 shell migration 推进成真正的 workspace 分层与稳定化

## 1. 目标

本 PR10 的目标不是继续“换皮”或继续堆功能，而是把当前已经完成的 **page shell migration**，推进成真正可维护、可扩展、可稳定演进的 **workspace 分层架构**，并顺手消化一批已经明显暴露出来的技术债。

本 PR 覆盖三条主线：

1. **KB Workspace 深拆**
2. **Chat Workspace 深拆**
3. **Search Workspace 建立**
4. **顺手解决技术债**：legacy 组件过大、轮询粗糙、状态源重复、service/hook 边界不清、shared contracts 使用不彻底

---

## 2. 基于当前仓库的真实判断

### 2.1 已完成的基础

当前主线已经完成：

- `apps/web` / `apps/api` 成为主路径
- `packages/types` 和 `packages/sdk` 已经落地为真实包
- `Chat.tsx` 与 `KnowledgeBaseDetail.tsx` 已经 shell 化
- 最近主线已经合并了：
  - 共享契约 + KB/Chat workspace shell migration
  - RAG QA contract upgrade
  - RAG parsing stability
  - UI optimization

### 2.2 当前最核心的结构性问题

#### A. Workspace 还只是壳，legacy 仍然直接承接全部复杂度

已确认：

- `apps/web/src/app/pages/Chat.tsx` → `ChatWorkspace`
- `apps/web/src/features/chat/components/ChatWorkspace.tsx` → 直接返回 `ChatLegacy`
- `apps/web/src/app/pages/KnowledgeBaseDetail.tsx` → `KnowledgeBaseWorkspace`
- `apps/web/src/features/kb/components/KnowledgeBaseWorkspace.tsx` → 直接返回 `KnowledgeBaseDetailLegacy`

这说明当前只是：
- page shell 化了

但没有完成：
- workspace 真正接管 query / workflow / store / panel 分层

#### B. ChatLegacy 仍然是超大单体控制器

`apps/web/src/features/chat/components/ChatLegacy.tsx` 仍然同时承担：

- session 管理
- scope 解析与校验
- SSE 生命周期管理
- placeholder message 机制
- stream 状态写入
- agent 面板
- citations / thinking / token 使用统计
- confirmation flow
- 删除会话确认
- 输入框与停止逻辑

这已经是当前 Chat 稳定性的最大技术债。

#### C. KnowledgeBaseDetailLegacy 仍然承担页面级业务编排

`apps/web/src/features/kb/components/KnowledgeBaseDetailLegacy.tsx` 仍然同时承担：

- KB detail 加载
- papers 加载
- import jobs 加载
- 轮询
- import 完成后联动刷新
- search
- tab 状态
- import modal
- 各类页面跳转

这也是典型的“controller + workflow + view 混写”。

#### D. Search 还没有进入 workspace 体系

当前 Search 仍然是：

- `apps/web/src/app/pages/Search.tsx`
- `apps/web/src/hooks/useSearch.ts`
- `apps/web/src/services/searchApi.ts`

没有 `features/search/*`，也没有 query/store/panel/workflow 分层。  
它现在还是典型的旧路径写法。

#### E. features 下的 hook/store 目前多是“桥接壳”，还不是主实现

当前已存在但很薄：

- `apps/web/src/features/chat/hooks/useChatWorkspace.ts`
- `apps/web/src/features/chat/hooks/useChatSession.ts`
- `apps/web/src/features/chat/hooks/useChatStreaming.ts`
- `apps/web/src/features/kb/hooks/useKnowledgeBaseWorkspace.ts`
- `apps/web/src/features/kb/hooks/useImportWorkflow.ts`
- `apps/web/src/features/kb/hooks/useImportJobsPolling.ts`
- `apps/web/src/features/chat/state/chatWorkspaceStore.ts`
- `apps/web/src/features/kb/state/kbWorkspaceStore.ts`

这些文件方向是对的，但目前仍然偏壳化，尚未真正承接复杂业务。

---

## 3. 本 PR 的边界

## 本 PR 要做
- 让 KB / Chat / Search 真正进入 workspace 分层
- 让 legacy 大组件瘦身或拆散
- 让 query / workflow / store / presentational components 职责清晰
- 让 shared contracts/sdk 真正成为业务真源的一部分，而不是“落地但未吃透”
- 解决最影响稳定性的技术债

## 本 PR 不做
- 不新开一轮 RAG 架构大改
- 不大规模修改 Milvus / embedding / reranker 核心算法
- 不重新定义全部后端 API
- 不做完整 observability/harness 落地（可为后续 PR 留接口）
- 不大范围美化 UI 样式

---

## 4. 目标架构

### 4.1 KB

```text
apps/web/src/features/kb/
  components/
    KnowledgeBaseWorkspace.tsx
    KnowledgeBaseHeader.tsx
    KnowledgeBaseTabs.tsx
    KnowledgeBasePapersPanel.tsx
    KnowledgeBaseImportPanel.tsx
    KnowledgeBaseSearchPanel.tsx
    KnowledgeBaseQuickChatPanel.tsx
    KnowledgeBaseEmptyState.tsx
    KnowledgeBaseErrorState.tsx
    KnowledgeBaseDetailLegacy.tsx   # 逐步退役
  hooks/
    useKnowledgeBaseWorkspace.ts
    useKnowledgeBaseQueries.ts      # 新增
    useImportJobsPolling.ts
    useImportWorkflow.ts
    useKnowledgeBaseSearch.ts       # 新增
  state/
    kbWorkspaceStore.ts
```

### 4.2 Chat

```text
apps/web/src/features/chat/
  components/
    ChatWorkspace.tsx
    ChatHeader.tsx
    SessionSidebar.tsx
    ChatMessageList.tsx
    ChatComposer.tsx
    ChatRightPanel.tsx
    ScopeHeader.tsx
    ChatEmptyState.tsx
    ChatLegacy.tsx                  # 逐步退役
  hooks/
    useChatWorkspace.ts
    useChatSession.ts
    useChatStreaming.ts
    useChatScope.ts                 # 新增
    useChatMessagesViewModel.ts     # 新增
  state/
    chatWorkspaceStore.ts
```

### 4.3 Search

```text
apps/web/src/features/search/
  components/
    SearchWorkspace.tsx
    SearchToolbar.tsx
    SearchResultsPanel.tsx
    SearchSidebar.tsx
    SearchPagination.tsx
    SearchAuthorPanel.tsx
    SearchKnowledgeBaseImportModal.tsx
  hooks/
    useSearchWorkspace.ts
    useUnifiedSearch.ts
    useAuthorSearch.ts
    useSearchImportFlow.ts
  state/
    searchWorkspaceStore.ts
```

---

## 5. Phase 执行顺序与依赖关系

## 总原则
顺序必须是：

1. **先拆 Chat / KB / Search 的数据与状态源**
2. **再拆 UI 组件**
3. **最后清理 legacy 残留**

否则会出现：
- 组件拆了，但状态还在 legacy 里
- query 没收口，组件越拆越乱
- 后期又只能回到 legacy 文件补洞

---

## Phase 0：基线冻结与清点
**依赖：无**

### 目标
冻结当前 legacy 行为，避免 PR10 重构期间“功能悄悄变了但没人发现”。

### 动作
1. 补齐现有 shell/legacy 页面测试快照或行为测试
2. 记录当前关键行为：
   - Chat：新建会话、切会话、发送消息、停止、确认、scope banner
   - KB：导入、轮询、搜索、进入 chat、进入 read
   - Search：查询、翻页、作者搜索、导入知识库
3. 对 legacy 文件加注释标记“正在拆分，不再新增新逻辑”

### 修改文件
- `apps/web/src/app/pages/Chat.test.tsx`
- `apps/web/src/app/pages/KnowledgeBaseDetail.test.tsx`
- `apps/web/src/app/pages/KnowledgeBaseDetail.shell.test.tsx`
- `apps/web/src/services/chatApi.test.ts`
- `apps/web/src/services/sseService.test.ts`
- （可能新增）`apps/web/src/app/pages/Search.test.tsx`【当前未确认存在，建议新增】

### 交付
- PR10 的“行为基线”测试
- Legacy 文件顶部标记说明

---

## Phase 1：先把 KB / Chat / Search 的数据与状态源收口
**依赖：Phase 0**

这是整个 PR10 的核心阶段。

### 1A. Chat 状态收口

#### 当前问题
- `ChatLegacy.tsx` 内部自己维护大量本地状态
- `useSessions` 仍然是旧 app/hooks 路径
- `useChatStream` 仍然是旧 app/hooks 路径
- `features/chat/hooks` 目前只是把旧 hook 包一层

#### 目标
让 `features/chat/*` 成为真正的业务入口，旧 `app/hooks/*` 降级为内部实现或被吸收。

#### 具体动作
1. 扩展 `chatWorkspaceStore.ts`
   - 增加：
     - `selectedSessionId`
     - `selectedMessageId`
     - `scope`
     - `mode`
     - `composerDraft`
     - `rightPanelOpen`
     - `showDeleteConfirm`
     - `pendingDeleteSessionId`
2. 重写 `useChatWorkspace.ts`
   - 不再只读 URL 参数
   - 负责整合：
     - scope
     - mode
     - right panel
     - delete confirm
3. 重写 `useChatSession.ts`
   - 包装 `useSessions`
   - 对外只暴露 workspace 需要的最小接口
   - 统一 current session / sessions list / messages 查询入口
4. 重写 `useChatStreaming.ts`
   - 包装 `useChatStream`
   - 统一 send / stop / confirmation / onDone / onError
   - 处理 placeholder → final assistant message 合并
5. 设计 `useChatScope.ts`【新增】
   - 专管 URL params → scope validate → scope state
   - 把 `paperId/kbId` 校验逻辑从 `ChatLegacy.tsx` 搬出去
6. 设计 `useChatMessagesViewModel.ts`【新增】
   - 把 ExtendedChatMessage 派生计算（isStreaming、citations、toolTimeline、render data）移出 UI 组件

#### 文件级改动
##### 修改
- `apps/web/src/features/chat/state/chatWorkspaceStore.ts`
- `apps/web/src/features/chat/hooks/useChatWorkspace.ts`
- `apps/web/src/features/chat/hooks/useChatSession.ts`
- `apps/web/src/features/chat/hooks/useChatStreaming.ts`
- `apps/web/src/app/hooks/useSessions.ts`
- `apps/web/src/app/hooks/useChatStream.ts`

##### 新增
- `apps/web/src/features/chat/hooks/useChatScope.ts`
- `apps/web/src/features/chat/hooks/useChatMessagesViewModel.ts`

---

### 1B. KB 状态收口
**依赖：Phase 1A 可并行，无强依赖**

#### 当前问题
- `KnowledgeBaseDetailLegacy.tsx` 自己维护 query + tab + polling + refresh
- `useKnowledgeBaseWorkspace.ts` 现在只返回 `activeTab`
- `useImportWorkflow.ts` / `useImportJobsPolling.ts` 太薄
- 轮询逻辑仍然写在 legacy 组件里

#### 目标
KB 页面改成真正的 workspace controller，不再让 legacy 组件承担业务编排。

#### 具体动作
1. 扩展 `kbWorkspaceStore.ts`
   - 增加：
     - `activeTab`
     - `isImportDialogOpen`
     - `selectedPaperIds`
     - `searchDraft`
     - `searchResults`
     - `selectedImportJobId`
2. 重写 `useKnowledgeBaseWorkspace.ts`
   - 负责：
     - 读取 kbId
     - tab 同步
     - 汇总 kb/papers/import/search 状态
     - 对外暴露 refreshAll
3. 新增 `useKnowledgeBaseQueries.ts`
   - 管理：
     - kb detail
     - papers
     - import jobs
     - upload history（如需要）
4. 强化 `useImportJobsPolling.ts`
   - 从“固定 setInterval”升级为：
     - 有运行中任务才轮询
     - 全部完成就停止
     - 页面不可见时暂停（可选）
5. 强化 `useImportWorkflow.ts`
   - 抽出：
     - onImportComplete
     - onImportRetry
     - onImportCancel（如果后端支持）
6. 新增 `useKnowledgeBaseSearch.ts`
   - 管理 KB search state，不再让 legacy 组件自己维护 query/results/loading

#### 文件级改动
##### 修改
- `apps/web/src/features/kb/state/kbWorkspaceStore.ts`
- `apps/web/src/features/kb/hooks/useKnowledgeBaseWorkspace.ts`
- `apps/web/src/features/kb/hooks/useImportJobsPolling.ts`
- `apps/web/src/features/kb/hooks/useImportWorkflow.ts`

##### 新增
- `apps/web/src/features/kb/hooks/useKnowledgeBaseQueries.ts`
- `apps/web/src/features/kb/hooks/useKnowledgeBaseSearch.ts`

##### 可能需要调整
- `apps/web/src/services/kbApi.ts`
- `apps/web/src/services/importApi.ts`

---

### 1C. Search 状态收口
**依赖：Phase 1A/1B 可并行**

#### 当前问题
Search 仍然完全不在 workspace 体系内：
- `Search.tsx` 很重
- `useSearch.ts` 偏旧式 hook
- 作者搜索、结果分页、导入 KB 等 workflow 都混在页面里

#### 目标
给 Search 建立最小可用 workspace 分层，而不是继续让它游离在体系外。

#### 具体动作
1. 新增 `features/search/state/searchWorkspaceStore.ts`
   - 保存：
     - active source
     - sort/filter
     - selected author
     - pending import paper
     - selected KB for import
2. 新增 `useSearchWorkspace.ts`
   - 统一 URL state + local workspace state
3. 保留 `useSearch.ts`，但降级为底层数据 hook
4. 新增 `useUnifiedSearch.ts`
   - 包装 `useSearch.ts`
   - 负责 query / page / filters 协调
5. 新增 `useAuthorSearch.ts`
   - 把作者搜索逻辑从页面移出
6. 新增 `useSearchImportFlow.ts`
   - 管理“搜索结果导入到 KB”的流程

#### 文件级改动
##### 新增
- `apps/web/src/features/search/state/searchWorkspaceStore.ts`
- `apps/web/src/features/search/hooks/useSearchWorkspace.ts`
- `apps/web/src/features/search/hooks/useUnifiedSearch.ts`
- `apps/web/src/features/search/hooks/useAuthorSearch.ts`
- `apps/web/src/features/search/hooks/useSearchImportFlow.ts`
- `apps/web/src/features/search/components/SearchWorkspace.tsx`

##### 修改
- `apps/web/src/app/pages/Search.tsx`
- `apps/web/src/hooks/useSearch.ts`
- `apps/web/src/services/searchApi.ts`

---

## Phase 2：拆 UI 组件，减小 legacy 体积
**依赖：Phase 1 完成**

这一阶段才拆 UI，否则拆了也只是在搬砖。

### 2A. Chat 组件拆分

#### 目标
把 `ChatLegacy.tsx` 拆成组合式 workspace UI。

#### 拆分建议
##### 新增组件
- `apps/web/src/features/chat/components/ChatHeader.tsx`
- `apps/web/src/features/chat/components/SessionSidebar.tsx`
- `apps/web/src/features/chat/components/ChatMessageList.tsx`
- `apps/web/src/features/chat/components/ChatComposer.tsx`
- `apps/web/src/features/chat/components/ChatRightPanel.tsx`
- `apps/web/src/features/chat/components/ScopeHeader.tsx`
- `apps/web/src/features/chat/components/ChatEmptyState.tsx`

##### 调整
- `apps/web/src/features/chat/components/ChatWorkspace.tsx`
  - 真正拼装 workspace
- `apps/web/src/features/chat/components/ChatLegacy.tsx`
  - 缩小为：
    - 仅保留桥接逻辑
    - 或完全删除（视拆分完成度）

#### 拆分原则
- `ChatWorkspace.tsx`：只拼装
- hooks：只提供状态和动作
- 子组件：只渲染，不直接调 service

---

### 2B. KB 组件拆分

#### 新增组件
- `apps/web/src/features/kb/components/KnowledgeBaseHeader.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseTabs.tsx`
- `apps/web/src/features/kb/components/KnowledgeBasePapersPanel.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseImportPanel.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseSearchPanel.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseQuickChatPanel.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseEmptyState.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseErrorState.tsx`

#### 调整
- `apps/web/src/features/kb/components/KnowledgeBaseWorkspace.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseDetailLegacy.tsx`

#### 目标
把：
- tab
- import panel
- papers panel
- search panel
- quick chat panel

拆出来，legacy 文件只保留过渡桥接或被删除。

---

### 2C. Search 组件拆分

#### 新增组件
- `apps/web/src/features/search/components/SearchWorkspace.tsx`
- `apps/web/src/features/search/components/SearchToolbar.tsx`
- `apps/web/src/features/search/components/SearchSidebar.tsx`
- `apps/web/src/features/search/components/SearchResultsPanel.tsx`
- `apps/web/src/features/search/components/SearchPagination.tsx`
- `apps/web/src/features/search/components/SearchAuthorPanel.tsx`
- `apps/web/src/features/search/components/SearchKnowledgeBaseImportModal.tsx`

#### 调整
- `apps/web/src/app/pages/Search.tsx`
  - 变成 shell：`return <SearchWorkspace />`

---

## Phase 3：清理 legacy 路径与技术债
**依赖：Phase 2**

### 3A. 旧 hooks 降级/收口
当前旧 hooks 还在：
- `apps/web/src/app/hooks/useSessions.ts`
- `apps/web/src/app/hooks/useChatStream.ts`
- `apps/web/src/app/hooks/useSSE.ts`

#### 目标
- 能迁则迁到 `features/chat/hooks/*`
- 不能迁则明确标记为 internal legacy implementation
- 不允许页面再直接消费这些旧 hooks

#### 具体动作
- 页面与 workspace 只从 `features/*` 引入
- `app/hooks/*` 只作为兼容层，后续可删

---

### 3B. service 侧技术债清理
#### 重点文件
- `apps/web/src/services/chatApi.ts`
- `apps/web/src/services/sessionsApi.ts`
- `apps/web/src/services/sseService.ts`
- `apps/web/src/services/kbApi.ts`
- `apps/web/src/services/importApi.ts`
- `apps/web/src/services/searchApi.ts`

#### 目标
- 页面组件不直接感知旧式 service 细节
- features hooks 只消费稳定 service/sdk 接口
- 对返回值进行统一 normalize 的地方尽量集中

---

### 3C. Search / KB / Chat 跳转与 scope 技术债
#### 目标
统一处理：
- `paperId`
- `kbId`
- `tab`
- `source`
- `q`
- `page`

避免每个页面自己解析 URL。

#### 建议新增（可选）
- `apps/web/src/features/shared/hooks/useRouteScope.ts`【可选，不确定是否在本 PR 引入】
- `apps/web/src/features/shared/hooks/useWorkspaceUrlState.ts`【可选】

> 这两个属于“适度多做一点”的内容。  
> 若 PR10 不想过大，可先不做，只在 Chat/KB/Search 内局部实现。

---

## 6. 需要顺手解决的技术债

### 技术债 1：固定 5 秒轮询过于粗糙
当前 KB import 轮询逻辑是页面内固定 interval。  
应改成：
- 仅在存在 running/queued job 时轮询
- import 全部完成后自动停止
- 页面不可见时可暂停（可选）

### 技术债 2：Chat 的多状态源风险
虽然现在功能能跑，但 ChatLegacy 仍然存在：
- placeholder state
- localMessages
- sessionMessages
- streamState
- currentMessageIdRef

这些逻辑至少要从 UI 组件里抽走，进入 hooks/workspace controller 层。

### 技术债 3：Search 没有纳入 features 架构
这会导致：
- KB / Chat 开始稳定化了
- Search 仍然是“旧风格页面”
- 以后 Search 继续成为另一个孤岛

### 技术债 4：Workspace store 过薄
当前 `chatWorkspaceStore.ts` 与 `kbWorkspaceStore.ts` 都过薄，基本没有承接实际业务状态。  
PR10 必须让 store 变成真实的 workspace state，而不是占位。

### 技术债 5：legacy 文件继续吸收新逻辑的风险
必须在 PR10 中明确约束：
- `ChatLegacy.tsx` 不再新增新业务
- `KnowledgeBaseDetailLegacy.tsx` 不再新增新业务
- Search 迁入 workspace 后，`Search.tsx` 只做 shell

---

## 7. 文件级落地清单

## 7.1 前端必须修改文件

### 页面 shell
- `apps/web/src/app/pages/Chat.tsx`
- `apps/web/src/app/pages/KnowledgeBaseDetail.tsx`
- `apps/web/src/app/pages/Search.tsx`

### Chat
- `apps/web/src/features/chat/components/ChatWorkspace.tsx`
- `apps/web/src/features/chat/components/ChatLegacy.tsx`
- `apps/web/src/features/chat/hooks/useChatWorkspace.ts`
- `apps/web/src/features/chat/hooks/useChatSession.ts`
- `apps/web/src/features/chat/hooks/useChatStreaming.ts`
- `apps/web/src/features/chat/state/chatWorkspaceStore.ts`

### KB
- `apps/web/src/features/kb/components/KnowledgeBaseWorkspace.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseDetailLegacy.tsx`
- `apps/web/src/features/kb/hooks/useKnowledgeBaseWorkspace.ts`
- `apps/web/src/features/kb/hooks/useImportWorkflow.ts`
- `apps/web/src/features/kb/hooks/useImportJobsPolling.ts`
- `apps/web/src/features/kb/state/kbWorkspaceStore.ts`

### Search
- `apps/web/src/hooks/useSearch.ts`
- `apps/web/src/services/searchApi.ts`

### 旧 hooks / service
- `apps/web/src/app/hooks/useSessions.ts`
- `apps/web/src/app/hooks/useChatStream.ts`
- `apps/web/src/app/hooks/useSSE.ts`
- `apps/web/src/services/chatApi.ts`
- `apps/web/src/services/sessionsApi.ts`
- `apps/web/src/services/sseService.ts`
- `apps/web/src/services/kbApi.ts`
- `apps/web/src/services/importApi.ts`

### 测试
- `apps/web/src/app/pages/Chat.test.tsx`
- `apps/web/src/app/pages/KnowledgeBaseDetail.test.tsx`
- `apps/web/src/app/pages/KnowledgeBaseDetail.shell.test.tsx`
- `apps/web/src/services/chatApi.test.ts`
- `apps/web/src/services/sseService.test.ts`
- （建议新增）`apps/web/src/app/pages/Search.test.tsx`

---

## 7.2 前端新增文件

### Chat
- `apps/web/src/features/chat/hooks/useChatScope.ts`
- `apps/web/src/features/chat/hooks/useChatMessagesViewModel.ts`
- `apps/web/src/features/chat/components/ChatHeader.tsx`
- `apps/web/src/features/chat/components/SessionSidebar.tsx`
- `apps/web/src/features/chat/components/ChatMessageList.tsx`
- `apps/web/src/features/chat/components/ChatComposer.tsx`
- `apps/web/src/features/chat/components/ChatRightPanel.tsx`
- `apps/web/src/features/chat/components/ScopeHeader.tsx`
- `apps/web/src/features/chat/components/ChatEmptyState.tsx`

### KB
- `apps/web/src/features/kb/hooks/useKnowledgeBaseQueries.ts`
- `apps/web/src/features/kb/hooks/useKnowledgeBaseSearch.ts`
- `apps/web/src/features/kb/components/KnowledgeBaseHeader.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseTabs.tsx`
- `apps/web/src/features/kb/components/KnowledgeBasePapersPanel.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseImportPanel.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseSearchPanel.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseQuickChatPanel.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseEmptyState.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseErrorState.tsx`

### Search
- `apps/web/src/features/search/state/searchWorkspaceStore.ts`
- `apps/web/src/features/search/hooks/useSearchWorkspace.ts`
- `apps/web/src/features/search/hooks/useUnifiedSearch.ts`
- `apps/web/src/features/search/hooks/useAuthorSearch.ts`
- `apps/web/src/features/search/hooks/useSearchImportFlow.ts`
- `apps/web/src/features/search/components/SearchWorkspace.tsx`
- `apps/web/src/features/search/components/SearchToolbar.tsx`
- `apps/web/src/features/search/components/SearchSidebar.tsx`
- `apps/web/src/features/search/components/SearchResultsPanel.tsx`
- `apps/web/src/features/search/components/SearchPagination.tsx`
- `apps/web/src/features/search/components/SearchAuthorPanel.tsx`
- `apps/web/src/features/search/components/SearchKnowledgeBaseImportModal.tsx`

### 可选/不确定（按你本次 PR 体量决定）
- `apps/web/src/features/shared/hooks/useRouteScope.ts`
- `apps/web/src/features/shared/hooks/useWorkspaceUrlState.ts`

---

## 7.3 后端可能需要调整的文件（按需要，非必做）

这些不是 PR10 主体，但如果前端重构时暴露契约/轮询/搜索细节不合理，允许顺手调整。

### KB / Search / Chat
- `apps/api/app/api/kb/kb_crud.py`
- `apps/api/app/api/kb/kb_papers.py`
- `apps/api/app/api/kb/kb_import.py`
- `apps/api/app/api/imports/jobs.py`
- `apps/api/app/api/search/library.py`
- `apps/api/app/api/search/external.py`
- `apps/api/app/api/search/shared.py`
- `apps/api/app/api/chat.py`
- `apps/api/app/api/session.py`

### schema
- `apps/api/app/schemas/kb.py`
- `apps/api/app/schemas/import_jobs.py`
- `apps/api/app/schemas/chat.py`
- `apps/api/app/schemas/session.py`
- `apps/api/app/schemas/common.py`

> 标记为“可能需要调整”，因为是否修改取决于前端拆分过程中是否发现：
> - import jobs DTO 仍不够稳定
> - search 响应结构不够统一
> - chat/session 返回模型仍有 legacy 兼容负担

---

## 8. 推荐 commit 拆分

### Commit 1：test + boundary freeze
- 增加/修补 Search 测试
- 给 legacy 文件加“冻结说明”
- 明确 PR10 不在 legacy 中新增业务

### Commit 2：chat state/workflow extraction
- 重写 `useChatWorkspace`
- 重写 `useChatSession`
- 重写 `useChatStreaming`
- 扩展 `chatWorkspaceStore`

### Commit 3：kb state/workflow extraction
- 重写 `useKnowledgeBaseWorkspace`
- 增强 `useImportJobsPolling`
- 增强 `useImportWorkflow`
- 新增 `useKnowledgeBaseQueries` / `useKnowledgeBaseSearch`

### Commit 4：search workspace introduction
- 新建 `features/search/*`
- `Search.tsx` 壳化
- 把 `useSearch` 降级为底层数据 hook

### Commit 5：chat UI split
- 新增 Chat 子组件
- `ChatWorkspace` 真正接管 legacy 逻辑
- 缩减 `ChatLegacy.tsx`

### Commit 6：kb UI split
- 新增 KB 子组件
- `KnowledgeBaseWorkspace` 真正接管 legacy 逻辑
- 缩减 `KnowledgeBaseDetailLegacy.tsx`

### Commit 7：cleanup + docs + tests
- 清理 legacy 残留
- 更新测试
- 更新文档（如有）

---

## 9. 交付清单

## 必交付
1. Chat / KB / Search 三个页面都进入 workspace 分层
2. `Chat.tsx` / `KnowledgeBaseDetail.tsx` / `Search.tsx` 都变成真正的 shell
3. `ChatWorkspace` / `KnowledgeBaseWorkspace` / `SearchWorkspace` 成为真实业务入口
4. `ChatLegacy.tsx` 和 `KnowledgeBaseDetailLegacy.tsx` 大幅瘦身，且不再承接新增业务
5. Search 被迁入 `features/search/*`
6. KB 的轮询从页面内 setInterval 改成 hook/workflow 驱动
7. Chat 的 scope / session / streaming / message 逻辑从大组件中拆出
8. 测试覆盖壳化后的核心行为

## 质量交付
1. 页面级组件不再直接调 service
2. features hook 成为页面唯一业务入口
3. store 真正承接 workspace 状态
4. legacy 文件被标记为过渡态，不再扩展

---

## 10. 验收标准

### Chat
- `apps/web/src/app/pages/Chat.tsx` 只渲染 workspace
- `ChatWorkspace.tsx` 不再直接 `return <ChatLegacy />`
- `ChatLegacy.tsx` 行数和职责显著下降
- scope 校验逻辑已搬出大组件
- session/stream/message 逻辑至少 70% 已进入 features hooks

### KB
- `KnowledgeBaseWorkspace.tsx` 不再直接 `return <KnowledgeBaseDetailLegacy />`
- `KnowledgeBaseDetailLegacy.tsx` 行数和职责显著下降
- import polling 不再在页面内硬编码 interval
- search/query/import/papers 状态不再全部挤在同一组件

### Search
- `Search.tsx` 只渲染 workspace
- `features/search/*` 已建立
- 作者搜索 / 导入知识库流程从页面中拆出
- `useSearch.ts` 降为底层 hook，而不是页面控制器

### 全局
- 类型检查通过
- 现有前端测试通过
- 新增的 Search shell/workspace 测试通过
- 没有出现新的重复 hook / 平行实现目录

---

## 11. 执行风险与控制

### 风险 1：PR 体量过大
#### 控制
- 严格按 phase 和 commit 顺序提交
- 先做状态收口，再拆 UI

### 风险 2：ChatLegacy 拆一半后行为回归
#### 控制
- 先补行为基线测试
- 每个子阶段都跑 Chat 核心测试

### 风险 3：Search 引入 workspace 后 URL 状态混乱
#### 控制
- 保持 `useUrlState` 仍然存在
- 先把它包进 `useSearchWorkspace`

### 风险 4：后端契约被迫修改导致 PR 扩散
#### 控制
- 后端只做“必要修补”
- 不在 PR10 内开新的后端大方向

---

## 12. 最终建议

PR10 的最优完成标准不是“把所有 legacy 全删掉”，而是：

- **让 KB / Chat / Search 的真实业务入口已经转移到 workspace 层**
- **让 legacy 文件退化成过渡桥接层**
- **让之后 PR11/PR12 可以直接基于 workspace 做 observability、agent-native UX、benchmark**

一句话说：

> PR10 的成功标准，不是 UI 更好看，而是 **从“壳化迁移”真正走到“分层可演进”**。
