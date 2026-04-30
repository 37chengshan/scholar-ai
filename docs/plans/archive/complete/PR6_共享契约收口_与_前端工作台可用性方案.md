---
owner: app-foundation
status: superseded
depends_on:
  - PR5
last_verified_at: 2026-04-17
evidence_commits: []
superseded_by: PR5_共享契约收口_与_前端工作台可用性方案
---

# PR-6：共享契约收口 → 前端工作台可用性（已废弃）

> 状态说明：本计划已被 [docs/plans/PR5_共享契约收口_与_前端工作台可用性方案.md](docs/plans/PR5_共享契约收口_与_前端工作台可用性方案.md) 取代，不再作为 active 执行入口。

## 1. 文档目的

这份文档用于指导 **PR-5** 的实施。它承接：

- **PR #4**：物理迁移到 `apps/web` 与 `apps/api`
- **PR #4**：迁移后稳定化

当前仓库已经完成目录真源切换与治理加固，下一步不应继续围绕目录治理，而应进入：

1. **共享契约收口**：把分散在 `apps/web/src/services/*`、`apps/web/src/types/*`、`apps/api/app/schemas/*` 的接口契约收口到 `packages/types` 与 `packages/sdk`
2. **前端工作台可用性**：把 KB 与 Chat 从“重页面 + 多真相源状态”推进到“workspace + query/store/stream 分层”的稳定工作台

本计划不是原则说明，而是面向当前仓库实际代码结构的可执行方案。

---

## 2. 当前代码现状（基于主线）

### 2.1 已完成的基础

- 真实代码主路径已切换到：
  - `apps/web`
  - `apps/api`
- 迁移后稳定化已完成，治理与验收脚本可跑
- 后端已具备基础分层：
  - `apps/api/app/api/`
  - `apps/api/app/services/`
  - `apps/api/app/schemas/`
  - `apps/api/app/repositories/`

### 2.2 当前最关键的问题

#### 问题 A：`packages/types` 与 `packages/sdk` 仍然只是占位目录

当前：
- `packages/types/README.md`
- `packages/sdk/README.md`

都只写了承接边界说明，但没有真实代码。

影响：
- 契约仍然散落在 `apps/web` 与 `apps/api`
- 无法形成共享真源
- 页面工作台化时会被接口漂移反复打断

#### 问题 B：Chat 契约仍在前端本地定义

当前文件：
- `apps/web/src/services/chatApi.ts`
- `apps/web/src/services/sessionsApi.ts`
- `apps/web/src/types/chat.ts`

已知现状：
- `chatApi.ts` 本地定义 `ChatMode`、`ChatScope`
- 仍直接以 `Session` / `Message` 作为返回主类型

影响：
- chat 契约没有共享真源
- Chat 页面重构时容易出现 service / store / page 各自理解不同的问题

#### 问题 C：SSE / Stream 契约完全在前端本地

当前文件：
- `apps/web/src/services/sseService.ts`
- `apps/web/src/types/sse.ts`
- `apps/web/src/utils/sseParser.ts`

已知现状：
- `sseService.ts` 内定义了完整 `SSEEventType`、`SSEEventEnvelope`、event data 结构
- 这是前端本地协议，不是共享协议

影响：
- Chat 工作台的 stream state machine 无法建立稳定真源
- 后端 stream 输出一旦调整，前端极易漂移

#### 问题 D：KB 契约也仍在前端 service 本地

当前文件：
- `apps/web/src/services/kbApi.ts`
- `apps/web/src/services/importApi.ts`
- `apps/web/src/hooks/useKnowledgeBases.ts`

已知现状：
- `kbApi.ts` 本地定义了 `KnowledgeBase`、`KBListResponse`、`KBSearchResult`、`KBPaperListItem`、`KBUploadHistoryRecord`、`KBStorageStats`
- 返回壳不统一：`knowledgeBases`、`papers`、`records`、`results`、`answer`

影响：
- KB 页面无法稳定构建工作台级状态流
- service 层会继续膨胀为兼容层

#### 问题 E：KB 和 Chat 页面仍然过重

当前前端关键文件：
- `apps/web/src/app/pages/KnowledgeBaseDetail.tsx`
- `apps/web/src/app/pages/Chat.tsx`
- `apps/web/src/app/hooks/useChatStream.ts`
- `apps/web/src/app/hooks/useSessions.ts`
- `apps/web/src/stores/chatStore.ts`

已知现状：
- `Chat.tsx` 体量接近 50KB，明显过重
- `KnowledgeBaseDetail.tsx` 也仍在承载较多流程逻辑
- `useChatStream.ts` 与 `useSessions.ts` 说明 Chat 状态仍然是“页面 + hook + service + store”多点分散模式

影响：
- 切会话、断流恢复、导入联动、页面刷新后的状态连贯性都难稳定

---

## 3. 本期目标

本期结束后，必须达到以下状态：

### 3.1 契约层目标

1. `packages/types` 首批真实落地
2. `packages/sdk` 首批真实落地
3. KB / Chat / Import / Sessions / Stream 的核心 DTO 有共享真源
4. 前端 service 不再承担主契约定义职责
5. 后端对外 schema 与共享契约开始对齐

### 3.2 前端可用性目标

1. KB 页面具备工作台能力：
   - 导入 → 进度 → 论文出现 → 搜索 / quick chat 连贯
2. Chat 页面具备稳定会话工作流：
   - session 切换稳定
   - 单一消息真相源
   - stream 断流可恢复
   - scope 显式可见
3. 页面组件职责收口：
   - page 只做 shell
   - workspace 负责业务组织
   - hooks 负责 query / workflow / streaming
   - store 只保存交互状态，不保存重复远端真相

---

## 4. 选定的最佳实践方案

### 4.1 不做的事

本期明确不做：

- 不全量抽所有资源域类型到 `packages/types`
- 不全量重写所有 service 到 SDK
- 不一次性重做所有页面
- 不进入 RAG 解析 / 检索链路深改
- 不把 `packages/ui` 做成真实 UI 组件库

### 4.2 本期必须做的事

> **先让契约成为真源，再让 KB / Chat 成为稳定工作台。**

顺序是：

1. 通用 response / meta / error 契约
2. Chat stream 契约
3. KB / Import / Session / Message DTO
4. `packages/sdk` 提供最薄 typed client
5. KB Workspace
6. Chat Workspace

---

## 5. 执行顺序与依赖关系

### 5.1 依赖图

```text
A. 创建 packages/types 与 packages/sdk 基础骨架
    ↓
B. 收口 common response / pagination / errors
    ↓
C. 收口 chat/session/message/stream 契约
    ↓
D. 收口 kb/import 契约
    ↓
E. 前端 service 改为依赖共享 types / sdk
    ↓
F. 后端 schema 与 stream 输出对齐共享契约
    ↓
G. KB Workspace 落地
    ↓
H. Chat Workspace 落地
    ↓
I. 测试、验收、文档更新
```

### 5.2 关键依赖说明

| 依赖 | 原因 |
|------|------|
| A → B | 没有 `packages/types` / `packages/sdk` 基础骨架，后续无处承接共享契约 |
| B → C/D | Common response / meta / error 是其它 DTO 的底座 |
| C → H | Chat Workspace 必须先有统一 stream / session / message 契约 |
| D → G | KB Workspace 必须先有统一 KB / Import / Search DTO |
| E → G/H | 页面重构不能继续依赖旧的本地漂移契约 |
| F → G/H | 只有后端输出与共享契约对齐，前端工作台才不会被兼容补丁拖垮 |

### 5.3 并行建议

可并行的部分：

- `packages/types` 与 `packages/sdk` 初始化可并行
- KB DTO 与 Chat DTO 可并行
- KB Workspace 与 Chat Workspace 可分两人并行

不建议并行：

- **先改页面再补契约**
- **前端接了共享类型但后端输出还没对齐**

---

## 6. 子阶段 A：共享契约收口

## 6.1 目标

把当前散在：

- `apps/web/src/services/*`
- `apps/web/src/types/*`
- `apps/api/app/schemas/*`
- `apps/api/app/core/streaming.py`
- `apps/api/app/core/sse_event_buffer.py`

里的契约，收口成：

- `packages/types`
- `packages/sdk`

## 6.2 目录设计

### `packages/types`

```text
packages/types/
  package.json
  tsconfig.json
  src/
    common/
      response.ts
      pagination.ts
      errors.ts
    chat/
      dto.ts
      stream.ts
    kb/
      dto.ts
      import.ts
    papers/
      dto.ts
    index.ts
```

### `packages/sdk`

```text
packages/sdk/
  package.json
  tsconfig.json
  src/
    client/
      http.ts
      stream.ts
    chat/
      api.ts
      sessions.ts
      stream.ts
    kb/
      api.ts
      import.ts
    papers/
      api.ts
    index.ts
```

## 6.3 优先收口的共享契约

### P0：通用壳

#### 统一 response shell

新增：
- `packages/types/src/common/response.ts`
- `packages/types/src/common/pagination.ts`
- `packages/types/src/common/errors.ts`

建议定义：

```ts
export type ApiSuccess<T> = {
  success: true;
  data: T;
  meta?: ListMeta;
};

export type ApiFailure = {
  success: false;
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
};

export type ListMeta = {
  limit: number;
  offset: number;
  total: number;
};
```

#### 当前相关文件

前端：
- `apps/web/src/services/kbApi.ts`
- `apps/web/src/services/papersApi.ts`
- `apps/web/src/services/importApi.ts`
- `apps/web/src/services/chatApi.ts`

后端：
- `apps/api/app/schemas/common.py`
- 相关 route 输出 schema

---

### P0：Chat / Session / Message / Stream 契约

#### 新增
- `packages/types/src/chat/dto.ts`
- `packages/types/src/chat/stream.ts`

#### 首批收口对象

从当前文件抽取：
- `apps/web/src/services/chatApi.ts`
- `apps/web/src/services/sessionsApi.ts`
- `apps/web/src/types/chat.ts`
- `apps/web/src/services/sseService.ts`
- `apps/web/src/types/sse.ts`

收口为：
- `ChatMode`
- `ChatScope`
- `SessionSummaryDto`
- `MessageDto`
- `CitationDto`
- `StreamEventType`
- `StreamEventEnvelope<T>`
- `SessionStartEventData`
- `RoutingDecisionEventData`
- `ReasoningEventData`
- `MessageEventData`
- `ToolCallEventData`
- `ToolResultEventData`
- `DoneEventData`
- `ErrorEventData`

#### 原则

- `apps/web/src/services/sseService.ts` 不再定义主协议，只负责：
  - connect / disconnect
  - heartbeat
  - reconnect
  - raw line parser 与 runtime transport
- `apps/web/src/types/sse.ts` 改为：
  - re-export 共享契约
  - 或保留极少数 UI-only 派生类型

#### 后端对齐文件

- `apps/api/app/core/streaming.py`
- `apps/api/app/core/sse_event_buffer.py`
- 如有 Chat / Session schema：
  - `apps/api/app/schemas/session.py`
  - （建议新增）`apps/api/app/schemas/chat.py`

---

### P0：KB / Import 契约

#### 新增
- `packages/types/src/kb/dto.ts`
- `packages/types/src/kb/import.ts`

#### 从当前文件抽取
- `apps/web/src/services/kbApi.ts`
- `apps/web/src/services/importApi.ts`
- `apps/web/src/hooks/useKnowledgeBases.ts`

首批收口：
- `KnowledgeBaseDto`
- `KnowledgeBaseListItemDto`
- `KnowledgeBaseListParams`
- `KnowledgeBasePaperDto`
- `KnowledgeBaseSearchHitDto`
- `ImportJobDto`
- `ImportJobStatus`
- `UploadHistoryRecordDto`
- `StorageStatsDto`

#### 原则

- `kbApi.ts` 不再承担主 DTO 定义，只保留 typed 调用
- 统一列表类 meta 到 `limit + offset + total`
- 减少 `knowledgeBases` / `papers` / `records` / `results` 各自自定义壳

#### 后端对齐文件

建议新增或补充：
- `apps/api/app/schemas/kb.py`
- `apps/api/app/schemas/import_jobs.py`
- 对应 API：
  - `apps/api/app/api/kb/kb_crud.py`
  - `apps/api/app/api/kb/kb_papers.py`
  - `apps/api/app/api/kb/kb_import.py`
  - （如果存在）`kb_search.py` / `kb_query.py`

---

### P1：`packages/sdk` 首批 typed client

#### 原则

不一次性删掉 `apps/web/src/services/*`，而是让它们先变成薄适配层。

#### 新增文件

- `packages/sdk/src/client/http.ts`
- `packages/sdk/src/client/stream.ts`
- `packages/sdk/src/chat/api.ts`
- `packages/sdk/src/chat/sessions.ts`
- `packages/sdk/src/chat/stream.ts`
- `packages/sdk/src/kb/api.ts`
- `packages/sdk/src/kb/import.ts`

#### 首批接入文件

前端：
- `apps/web/src/services/chatApi.ts`
- `apps/web/src/services/sessionsApi.ts`
- `apps/web/src/services/sseService.ts`
- `apps/web/src/services/kbApi.ts`
- `apps/web/src/services/importApi.ts`

要求：
- 页面不直接用 SDK
- 页面仍通过 `apps/web/src/services/*`
- 但 service 实现内部逐步转向 `packages/sdk`

---

## 6.4 共享契约收口的具体修改文件

### 新增

#### `packages/types`
- `packages/types/package.json`
- `packages/types/tsconfig.json`
- `packages/types/src/index.ts`
- `packages/types/src/common/response.ts`
- `packages/types/src/common/pagination.ts`
- `packages/types/src/common/errors.ts`
- `packages/types/src/chat/dto.ts`
- `packages/types/src/chat/stream.ts`
- `packages/types/src/kb/dto.ts`
- `packages/types/src/kb/import.ts`
- `packages/types/src/papers/dto.ts`

#### `packages/sdk`
- `packages/sdk/package.json`
- `packages/sdk/tsconfig.json`
- `packages/sdk/src/index.ts`
- `packages/sdk/src/client/http.ts`
- `packages/sdk/src/client/stream.ts`
- `packages/sdk/src/chat/api.ts`
- `packages/sdk/src/chat/sessions.ts`
- `packages/sdk/src/chat/stream.ts`
- `packages/sdk/src/kb/api.ts`
- `packages/sdk/src/kb/import.ts`
- `packages/sdk/src/papers/api.ts`

### 修改

#### 前端
- `apps/web/package.json`
- `apps/web/tsconfig.json`
- `apps/web/vite.config.ts`
- `apps/web/src/services/chatApi.ts`
- `apps/web/src/services/sessionsApi.ts`
- `apps/web/src/services/sseService.ts`
- `apps/web/src/services/kbApi.ts`
- `apps/web/src/services/importApi.ts`
- `apps/web/src/types/chat.ts`
- `apps/web/src/types/sse.ts`
- `apps/web/src/types/index.ts`
- `apps/web/src/services/index.ts`

#### 后端
- `apps/api/app/schemas/common.py`
- `apps/api/app/schemas/session.py`
- `apps/api/app/schemas/papers.py`
- `apps/api/app/schemas/__init__.py`
- （建议新增）`apps/api/app/schemas/chat.py`
- （建议新增）`apps/api/app/schemas/kb.py`
- （建议新增）`apps/api/app/schemas/import_jobs.py`
- `apps/api/app/core/streaming.py`
- `apps/api/app/core/sse_event_buffer.py`
- 对应 API 路由文件

#### 文档
- `docs/specs/architecture/api-contract.md`
- `docs/specs/development/coding-standards.md`
- `architecture.md`

---

## 6.5 共享契约收口的交付清单

### 必交付

1. `packages/types` 首批可用
2. `packages/sdk` 首批可用
3. common response shell / pagination / errors 已共享
4. Chat / Session / Message / Stream 契约已共享
5. KB / Import 契约已共享
6. `apps/web` 关键 service 使用共享契约
7. `apps/api` stream 与 schema 对齐共享契约
8. 契约文档更新完毕

### 验收标准

- `packages/types` / `packages/sdk` 不再是 README-only 占位
- `apps/web/src/services/chatApi.ts` 不再本地定义主契约
- `apps/web/src/services/sseService.ts` 不再承担主协议定义职责
- `apps/web/src/services/kbApi.ts` 中本地 DTO 大幅减少
- 后端 stream 输出字段与共享协议一致
- 至少 KB 与 Chat 两个大域已接入共享契约

---

## 7. 子阶段 B：前端工作台可用性

## 7.1 总体策略

本期只重构两页：

1. **KB Workspace**
2. **Chat Workspace**

不要顺手大改：
- Search 页面
- Dashboard 页面
- Notes 页面
- Settings 页面

目标是集中火力把最核心的学术工作流页面打稳。

---

## 8. KB 工作台：实现方案

## 8.1 目标

把当前 `KnowledgeBaseDetail.tsx` 从“重页面”推进为：

- Page Shell
- KB Workspace
- query / workflow / store 分层
- 导入 → 论文 → 搜索 → quick chat 连续工作流

## 8.2 当前相关文件

- `apps/web/src/app/pages/KnowledgeBaseDetail.tsx`
- `apps/web/src/app/pages/KnowledgeBaseDetail.test.tsx`
- `apps/web/src/app/pages/KnowledgeBaseList.tsx`
- `apps/web/src/services/kbApi.ts`
- `apps/web/src/services/importApi.ts`
- `apps/web/src/hooks/useKnowledgeBases.ts`
- `apps/web/src/services/uploadHistoryApi.ts`

## 8.3 目标结构

新增：

```text
apps/web/src/features/kb/
  hooks/
    useKnowledgeBaseWorkspace.ts
    useImportJobsPolling.ts
    useImportWorkflow.ts
  state/
    kbWorkspaceStore.ts
  components/
    KnowledgeBaseWorkspace.tsx
    KnowledgeBaseHeader.tsx
    KnowledgeBaseTabs.tsx
    KnowledgeBasePapersPanel.tsx
    KnowledgeBaseImportPanel.tsx
    KnowledgeBaseSearchPanel.tsx
    KnowledgeBaseQuickChatPanel.tsx
```

页面层：
- `apps/web/src/app/pages/KnowledgeBaseDetail.tsx` 保留，但只做 shell

## 8.4 状态分层

### React Query 管
- KB detail
- KB papers
- KB upload history / import jobs
- KB search
- storage stats

### Zustand/store 管
- activeTab
- import dialog open
- selected paper ids
- selected import job
- side panel state
- search draft

### Workflow hooks 管
- import submit
- import polling
- import complete invalidate
- retry / cancel / resolve batch

## 8.5 KB 必做能力

### A. 导入工作流连续化
用户在同一页完成：
- 打开导入
- 上传 / URL / arXiv 导入
- 看任务进度
- 处理失败 / resolve batch
- 看到论文出现在列表中

### B. 顶部持久导入状态
要有 Active Imports Summary，而不是只在弹窗里看。

### C. Papers / Import 联动
- processing 占位
- completed 自动出现
- failed 直接 retry

### D. Search 与 Quick Chat 分离
- Search：证据检索
- Quick Chat：带 citations 的回答

### E. 页面刷新后状态不完全丢失
至少保留：
- 当前 KB
- 当前 tab
- 正在进行的 import jobs

## 8.6 KB 具体修改文件

### 新增
- `apps/web/src/features/kb/hooks/useKnowledgeBaseWorkspace.ts`
- `apps/web/src/features/kb/hooks/useImportJobsPolling.ts`
- `apps/web/src/features/kb/hooks/useImportWorkflow.ts`
- `apps/web/src/features/kb/state/kbWorkspaceStore.ts`
- `apps/web/src/features/kb/components/KnowledgeBaseWorkspace.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseHeader.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseTabs.tsx`
- `apps/web/src/features/kb/components/KnowledgeBasePapersPanel.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseImportPanel.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseSearchPanel.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseQuickChatPanel.tsx`

### 修改
- `apps/web/src/app/pages/KnowledgeBaseDetail.tsx`
- `apps/web/src/app/pages/KnowledgeBaseDetail.test.tsx`
- `apps/web/src/services/kbApi.ts`
- `apps/web/src/services/importApi.ts`
- `apps/web/src/hooks/useKnowledgeBases.ts`
- 相关导入/上传历史组件与测试文件

## 8.7 KB 交付清单

1. KB 页面 shell 化
2. `KnowledgeBaseWorkspace` 落地
3. import workflow 独立 hook
4. import polling 独立 hook
5. papers / import / search / quick chat 分 panel
6. 顶部 active imports summary
7. import → papers 自动联动
8. 刷新后工作流基本连续

### 验收标准
- `KnowledgeBaseDetail.tsx` 体量和职责明显缩小
- 页面不再手写大量副作用与轮询
- 用户可在同一页面连续完成导入与问答
- `KnowledgeBaseDetail.test.tsx` 覆盖新工作台行为

---

## 9. Chat 工作台：实现方案

## 9.1 目标

把当前 `Chat.tsx` 从“重页面 + 多状态源”推进为：

- Chat Page Shell
- Chat Workspace
- 单一消息真相源
- stream state machine
- session / message / scope / side panel 分层

## 9.2 当前相关文件

- `apps/web/src/app/pages/Chat.tsx`
- `apps/web/src/app/pages/Chat.test.tsx`
- `apps/web/src/app/hooks/useChatStream.ts`
- `apps/web/src/app/hooks/useSessions.ts`
- `apps/web/src/app/hooks/useSSE.ts`
- `apps/web/src/services/chatApi.ts`
- `apps/web/src/services/sessionsApi.ts`
- `apps/web/src/services/sseService.ts`
- `apps/web/src/stores/chatStore.ts`
- `apps/web/src/types/chat.ts`
- `apps/web/src/types/sse.ts`

## 9.3 目标结构

新增：

```text
apps/web/src/features/chat/
  hooks/
    useChatWorkspace.ts
    useChatSession.ts
    useChatStreaming.ts
  state/
    chatWorkspaceStore.ts
  components/
    ChatWorkspace.tsx
    SessionSidebar.tsx
    ChatMessageList.tsx
    ChatComposer.tsx
    ChatRightPanel.tsx
    ScopeHeader.tsx
```

页面层：
- `apps/web/src/app/pages/Chat.tsx` 保留，但只做 shell

## 9.4 状态分层

### Query 管
- sessions list
- current session
- messages history

### Store 管
- selected session id
- selected message id
- current scope
- composer draft
- right panel open state
- pending delete confirm

### Stream hook 管
- send
- stop
- retry
- streaming assistant message
- stream status
- citations
- reasoning
- usage
- error

## 9.5 Chat 必做能力

### A. 单一消息真相源
推荐：
- 历史消息来自 query cache
- 当前流式 assistant message 为 optimistic transient item
- `done` 后合并回 cache

禁止继续长期维持：
- localMessages 一套
- sessionMessages 一套
- streamBuffer 一套

### B. Scope 显式化
头部必须明确显示：
- global / knowledge base / paper
- 当前对象名
- 一键退出 scope

### C. Stop / Retry / 断流恢复
必须支持：
- stop 当前流
- retry 上一个 prompt
- 中途断流后保留已生成内容并标记 incomplete
- 网络恢复后可重发/续问

### D. 右侧面板只读派生
citations / reasoning / tool timeline 不允许再维护自己的消息状态。

## 9.6 Chat 具体修改文件

### 新增
- `apps/web/src/features/chat/hooks/useChatWorkspace.ts`
- `apps/web/src/features/chat/hooks/useChatSession.ts`
- `apps/web/src/features/chat/hooks/useChatStreaming.ts`
- `apps/web/src/features/chat/state/chatWorkspaceStore.ts`
- `apps/web/src/features/chat/components/ChatWorkspace.tsx`
- `apps/web/src/features/chat/components/SessionSidebar.tsx`
- `apps/web/src/features/chat/components/ChatMessageList.tsx`
- `apps/web/src/features/chat/components/ChatComposer.tsx`
- `apps/web/src/features/chat/components/ChatRightPanel.tsx`
- `apps/web/src/features/chat/components/ScopeHeader.tsx`

### 修改
- `apps/web/src/app/pages/Chat.tsx`
- `apps/web/src/app/pages/Chat.test.tsx`
- `apps/web/src/app/hooks/useChatStream.ts`
- `apps/web/src/app/hooks/useSessions.ts`
- `apps/web/src/app/hooks/useSSE.ts`
- `apps/web/src/services/chatApi.ts`
- `apps/web/src/services/sessionsApi.ts`
- `apps/web/src/services/sseService.ts`
- `apps/web/src/stores/chatStore.ts`
- `apps/web/src/types/chat.ts`
- `apps/web/src/types/sse.ts`

## 9.7 Chat 交付清单

1. Chat 页面 shell 化
2. `ChatWorkspace` 落地
3. 单一消息真相源
4. `useChatStreaming` 收口
5. scope header 显式化
6. stop / retry / 断流恢复闭环
7. session 切换稳定
8. right panel 只读派生

### 验收标准
- `Chat.tsx` 体量和职责显著下降
- 不再靠多套消息状态互相补丁
- 切 session 稳定
- stream 断开后用户可恢复
- `Chat.test.tsx` 覆盖新工作台行为

---

## 10. 推荐 PR 划分

### 方案 A：推荐方案（更稳）

#### PR-5A：共享契约收口
范围：
- `packages/types`
- `packages/sdk`
- `apps/web` service 契约改造
- `apps/api` schema / stream 对齐

#### PR-5B：KB Workspace
范围：
- KB 页面 shell 化
- import / papers / search / quick chat 工作流打通

#### PR-5C：Chat Workspace
范围：
- Chat 页面 shell 化
- stream / session / message 状态收口

### 方案 B：一次性多做一点

如果你坚持加量，建议合并成：

#### 一个大 PR：PR-5
包含：
1. 共享契约收口
2. KB Workspace
3. Chat Workspace 骨架 + 最小稳定化

但不建议在同一 PR 里再加入：
- Search 页面重构
- Dashboard 页面重构
- RAG 检索 / 解析升级

---

## 11. 最终交付清单（汇总）

### 契约层
- [ ] `packages/types` 首批落地
- [ ] `packages/sdk` 首批落地
- [ ] response / pagination / errors 共享
- [ ] Chat / Session / Message / Stream 契约共享
- [ ] KB / Import 契约共享
- [ ] `apps/api` 输出与共享契约对齐

### KB 工作台
- [ ] `KnowledgeBaseWorkspace` 落地
- [ ] 页面 shell 化
- [ ] import workflow 与 polling 独立
- [ ] 顶部 active imports summary
- [ ] papers / import / search / quick chat 分 panel
- [ ] import → papers 自动联动

### Chat 工作台
- [ ] `ChatWorkspace` 落地
- [ ] 页面 shell 化
- [ ] 单一消息真相源
- [ ] stream state 收口
- [ ] scope header 显式化
- [ ] stop / retry / 断流恢复
- [ ] side panel 只读派生

### 文档与测试
- [ ] API contract 文档更新
- [ ] coding standards 文档更新
- [ ] KB / Chat 测试补齐
- [ ] types / sse parser / service 测试补齐

---

## 12. 验收命令

### 12.1 结构与契约

```bash
bash scripts/check-doc-governance.sh
bash scripts/check-structure-boundaries.sh
bash scripts/check-code-boundaries.sh
bash scripts/check-governance.sh
```

### 12.2 前端

```bash
cd apps/web && npm install
cd apps/web && npm run type-check
cd apps/web && npm run test:run
cd ../..
```

### 12.3 后端

```bash
cd apps/api && pytest -x --tb=short
cd apps/api && pytest -q tests/unit/test_services.py --maxfail=1
cd apps/api && pytest -q tests/test_unified_search.py --maxfail=1
cd ../..
```

### 12.4 packages

如引入 workspace build，建议增加：

```bash
cd packages/types && npm run build
cd packages/sdk && npm run build
cd ../..
```

### 12.5 全量

```bash
bash scripts/verify-all-phases.sh
```

---

## 13. Definition of Done

本期完成的标准不是“文档写完”，而是同时满足：

1. `packages/types` 与 `packages/sdk` 不再是空壳目录
2. KB / Chat 主契约有共享真源
3. `apps/web/src/services/chatApi.ts`、`kbApi.ts`、`sseService.ts` 不再承担主契约定义职责
4. KB 页面具备工作台式连续体验
5. Chat 页面具备稳定 session/stream 工作流
6. 现有治理脚本、前端测试、后端关键测试全部通过

---

## 14. 最后建议

如果目标是“既推进共享契约，又尽快改善用户体感”，最优顺序是：

1. 先做 `packages/types` + Chat stream + KB DTO
2. 然后立刻做 KB Workspace
3. 最后做 Chat Workspace

不要反过来先拆大页面，否则页面会在契约未收口时反复返工。
