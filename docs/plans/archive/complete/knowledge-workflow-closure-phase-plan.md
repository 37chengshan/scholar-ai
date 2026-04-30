# Knowledge Workflow Closure Phase Plan — ScholarAI 知识工作流闭环三主线执行计划

> 来源: docs/plans/archive/reports/2026-04-20_下一大迭代研究报告.md  
> 目标: 将 Upload -> Import -> KB -> Chat -> History 打造成稳定、可恢复、可验证的核心工作流  
> 周期建议: 3 周  
> 交付方式: 3 条主线推进，按依赖顺序分 wave 落地  
> 执行原则: 不新增平行实现路径，不把新业务逻辑继续塞回冻结中的大控制器

---

## 一、计划目标

本计划不再把下一轮工作拆成彼此竞争的 PR10 / PR19 / PR21-PR23 / PR7-PR8 局部主题，而是把它们重组为一个统一目标：

**让 ScholarAI 的知识工作流从“多个能力都已存在”，进入“用户可以连续完成关键任务且状态一致”的阶段。**

这一轮要完成的不是新故事，而是把以下关键任务真正打通：

1. 用户创建知识库并导入第一篇论文。
2. 上传中断后可以恢复并只续传缺失分片。
3. 文件处理完成后，知识库页面自动进入“可检索、可提问”的状态。
4. 用户在知识库作用域内提问时，流式消息、历史消息、会话状态完全一致。
5. 用户从 Search 导入到 KB 后，可以继续进入 KB 和 Chat，而不是掉回碎片化流程。

---

## 二、范围与非范围

### 2.1 本计划范围

1. Upload Session、ImportJob、KB Workspace、Chat Session 之间的闭环一致性。
2. 上传恢复、分片上传、秒传、队列状态恢复。
3. chat/session/upload/import 相关契约、持久化与 SSE 语义收口。
4. 围绕主链路的前端工作台状态下沉与页面级回归。

### 2.2 明确非范围

1. 不做大规模模型栈替换。
2. 不重写 FastAPI / Celery / Milvus 等基础设施。
3. 不进行第二轮以视觉为主的页面改版。
4. 不把 hybrid retrieval / claim-level synthesis 作为本轮 P0 交付目标。

---

## 三、三条主线总览

| 主线 | 优先级 | 核心目标 | 主要输出 | 依赖 |
|---|---|---|---|---|
| 主线 A：Upload / Import 闭环硬化 | P0 | 让上传、恢复、导入、KB 刷新形成完整闭环 | Upload Session 端到端稳定、前端恢复与分片上传可用 | 主线 B 的上传契约冻结部分先完成 |
| 主线 B：契约、持久化、SSE 收口 | P0 | 让 chat/session/upload/import 的真实行为与文档、持久化、SSE 统一 | 单一契约真相、消息唯一写口、SSE 语义硬化 | 无 |
| 主线 C：工作台编排与页面级闭环 | P1 | 让 KB / Chat / Search 只承接编排，不再靠大组件堆状态 | Chat / KB 状态下沉、北极星链路回归 | 主线 A、主线 B 的核心能力稳定后推进 |

---

## 四、北极星用户旅程

本计划所有验收都围绕以下 4 条旅程展开：

1. 创建知识库并上传第一篇论文。
2. 上传中断后恢复并成功导入。
3. 在知识库中检索并发起问答。
4. 从 Search 导入论文到目标 KB，并继续进入 KB / Chat 工作流。

---

## 五、主线 A：Upload / Import 闭环硬化

### 5.1 目标

把当前“后端 Upload Session 已有骨架、前端上传队列基本可跑”的状态，推进到“用户可以稳定上传、恢复、导入、看到结果自动联动”的产品能力。

### 5.2 关键文件范围

优先涉及：

1. `apps/api/app/services/upload_session_service.py`
2. `apps/api/app/api/imports/upload_sessions.py`
3. `apps/api/app/models/upload_session.py`
4. `packages/types/src/kb/import.ts`
5. `packages/sdk/src/kb/import.ts`
6. `apps/web/src/features/uploads/hooks/useChunkUpload.ts`
7. `apps/web/src/features/uploads/hooks/useUploadRecovery.ts`
8. `apps/web/src/features/uploads/hooks/useUploadWorkspace.ts`
9. `apps/web/src/features/uploads/components/*`
10. `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`
11. `apps/web/src/features/kb/hooks/useKnowledgeBaseWorkspace.ts`
12. `apps/web/src/features/kb/hooks/useImportWorkflow.ts`
13. `tests/integration/*upload*`
14. `apps/web/src/features/uploads/**/*.test.ts`

### 5.3 执行项

1. 核对 Upload Session 的请求、响应、状态字段，与前端和 SDK 的实际消费保持单一真相。
2. 为分片上传补齐并发上传、失败分片重试、取消上传、超时控制，避免串行全量重来。
3. 为前端补齐刷新恢复、本地队列恢复、断网恢复，确保恢复后只上传缺失分片。
4. 将 Upload Workspace 与 KB Workspace 的“导入完成后刷新”从多路 callback，改为更明确的状态驱动联动。
5. 增加 Upload Session 集成测试与页面级测试，覆盖秒传、缺失分片恢复、complete、abort。

### 5.4 验收标准

- AC-A1  
  Given 已存在未完成的 Upload Session 且存在缺失分片  
  When 用户刷新页面后恢复上传队列  
  Then 前端只续传缺失分片，恢复后的进度与服务端状态一致。

- AC-A2  
  Given 用户上传的文件与已存在文件在 sha256 和 size 上完全匹配  
  When 前端创建 Upload Session  
  Then 服务端返回 `instantImport=true`，前端不再上传分片，并把任务推进到后续导入流程。

- AC-A3  
  Given 某个分片上传失败  
  When 用户点击重试或自动重试触发  
  Then 系统只重传失败分片，不重置整个上传任务，也不生成重复 ImportJob。

- AC-A4  
  Given 用户在 KB Workspace 中完成一轮上传并导入成功  
  When 导入状态进入 completed  
  Then Import Status、Papers、Knowledge Base 概览和 Run History 都会更新，且无需手工刷新页面。

- AC-A5  
  Given 用户主动取消一个上传会话  
  When 用户重新进入 Upload Workspace 或 KB 页面  
  Then 已取消任务不会继续推进到后台导入流程，页面状态与服务端状态保持一致。

### 5.5 验证命令

1. `cd apps/api && pytest -q tests/integration/test_upload_session*.py --maxfail=1`
2. `cd apps/web && npx vitest run src/features/uploads/**/*.test.ts`
3. `cd apps/web && npm run type-check`
4. `bash scripts/check-contract-gate.sh`

### 5.6 边界

1. 不在本主线中修改 Celery 运行模型。
2. 不在本主线中引入新的存储系统或 CDN。
3. 不重做 KB 页面视觉风格，只处理闭环所需的状态与交互。

---

## 六、主线 B：契约、持久化、SSE 收口

### 6.1 目标

把当前“message persistence、session messages、SSE replay 和 message_id 都已有骨架”的状态，推进到“端到端行为被验证、契约被锁定、脏数据入口被关闭”的阶段。

### 6.2 关键文件范围

优先涉及：

1. `docs/specs/architecture/api-contract.md`
2. `docs/specs/domain/resources.md`
3. `docs/specs/architecture/system-overview.md`
4. `docs/specs/governance/fallback-register.yaml`
5. `apps/api/app/api/chat.py`
6. `apps/api/app/api/session.py`
7. `apps/api/app/api/parse.py`
8. `apps/api/app/services/message_service.py`
9. `apps/api/app/services/chat_orchestrator.py`
10. `apps/web/src/services/sseService.ts`
11. `apps/web/src/features/chat/adapters/sseEventAdapter.ts`
12. `packages/sdk/src/chat/stream.ts`
13. `tests/integration/*chat*`
14. `tests/integration/*session*`

### 6.3 执行项

1. 冻结 upload/chat/session/parse 对外契约，确保文档、SDK、前端 service、后端 request/response 模型一致。
2. 锁定 assistant message 和 tool message 的唯一写口，禁止旧写口继续制造空 assistant 或伪 tool 记录。
3. 硬化 SSE canonical event types、`message_id` 约束、replay-only 语义、done/error 收束规则。
4. 为 `chat/stream -> sessions/{id}/messages` 增加集成测试，验证真实链路而不是局部单测。
5. 同步更新文档与 fallback 台账，保证治理脚本能反映真实状态。

### 6.4 验收标准

- AC-B1  
  Given 用户成功完成一轮 chat stream 交互  
  When 通过 `GET /sessions/{id}/messages` 读取历史消息  
  Then 会话中只存在一条对应的 assistant 最终消息，内容完整且没有重复落库。

- AC-B2  
  Given chat 过程中发生 tool call  
  When 持久化与历史读取完成  
  Then tool message 的 `tool_name`、内容和时序正确，且不出现 `unknown` 或空内容伪记录。

- AC-B3  
  Given 前后端发生任一业务 SSE 事件  
  When 事件到达前端适配层  
  Then 除 heartbeat 外每个事件都携带 `message_id`，且不依赖 legacy alias 才能被消费。

- AC-B4  
  Given 客户端使用 `Last-Event-ID` 进行重连  
  When 服务端进入 replay 流程  
  Then 重连只重放事件、不重新执行业务，也不会导致重复持久化或重复执行 agent 流程。

- AC-B5  
  Given 本主线完成  
  When 运行契约、文档、fallback 相关检查  
  Then 文档、实现、治理脚本的结果一致，且不存在过期 active fallback 项。

### 6.5 验证命令

1. `cd apps/api && pytest -q tests/integration/test_chat_* tests/integration/test_session_* --maxfail=1`
2. `cd apps/web && npx vitest run src/features/chat/**/*.test.ts* src/services/*.test.ts`
3. `cd apps/web && npm run type-check`
4. `bash scripts/check-contract-gate.sh`
5. `bash scripts/check-fallback-expiry.sh`
6. `bash scripts/check-doc-governance.sh`

### 6.6 边界

1. 不在本主线中推进 hybrid retrieval 和 claim-level synthesis。
2. Parse 相关工作仅做契约收口与接口决策，不扩展成新的大范围解析工程。
3. 不在本主线中进行第二轮前端页面视觉优化。

---

## 七、主线 C：工作台编排与页面级闭环

### 7.1 目标

让 KB / Chat / Search 真正承接工作流编排，而不是继续依赖冻结中的大控制器和多路 callback 刷新。该主线不是“再开新壳”，而是把已存在的 workspace 壳层变成真正的业务入口。

### 7.2 关键文件范围

优先涉及：

1. `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`
2. `apps/web/src/features/chat/hooks/useChatWorkspace.ts`
3. `apps/web/src/features/chat/hooks/useChatStreaming.ts`
4. `apps/web/src/features/chat/hooks/useChatSend.ts`
5. `apps/web/src/features/chat/hooks/useChatMessagesViewModel.ts`
6. `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`
7. `apps/web/src/features/kb/hooks/useKnowledgeBaseWorkspace.ts`
8. `apps/web/src/features/search/components/SearchWorkspace.tsx`
9. `apps/web/src/features/search/hooks/useSearchImportFlow.ts`
10. `tests/e2e/*`
11. `apps/web/src/features/chat/**/*.test.tsx`
12. `apps/web/src/features/kb/**/*.test.tsx`

### 7.3 执行项

1. 将 ChatWorkspaceV2 中仍然承担的 session、scope、stream、placeholder、删除确认等控制逻辑继续下沉到 hook / store 层。
2. 将 KB Workspace 中导入完成后的多路 fan-out 刷新，收束成更清晰的状态转换和单点更新策略。
3. 仅围绕闭环优化 Search 到 KB 的导入连续性，不继续扩展 Search 右侧分析面板。
4. 为 4 条北极星旅程补齐页面级回归和 E2E 验证。
5. 在代码边界上明确冻结文件只允许“拆出逻辑”，不允许继续往里堆新状态。

### 7.4 验收标准

- AC-C1  
  Given 用户在 KB 作用域内发起一次问答  
  When 流式过程进入 streaming、completed、error 或 cancelled 任一终态  
  Then placeholder、会话历史、scope banner、右侧过程面板的状态都保持一致，不出现幽灵消息或残留占位。

- AC-C2  
  Given 用户停留在 Knowledge Workspace 且后台 ImportJob 从 running 进入 completed  
  When 工作台收到状态变化  
  Then Papers、Import Status、Knowledge Base 概览与 Run History 能自动完成联动更新，且用户不需要手工刷新。

- AC-C3  
  Given 用户在 Search 中把论文导入到目标知识库  
  When 导入成功后继续进入 KB 或 Chat  
  Then 目标知识库上下文不会丢失，用户可以继续沿同一工作流操作。

- AC-C4  
  Given 用户在流式过程中切换会话、切换 scope 或重连  
  When 旧流的事件到达当前页面  
  Then stale event 会被丢弃，不污染当前 session，也不会生成重复消息。

- AC-C5  
  Given 本主线完成  
  When 执行北极星旅程的页面级回归和 E2E 测试  
  Then 4 条关键旅程都可以稳定通过，且不会依赖人工补刷新或控制台干预。

### 7.5 验证命令

1. `cd apps/web && npx vitest run src/features/chat/**/*.test.tsx src/features/kb/**/*.test.tsx src/features/search/**/*.test.tsx`
2. `cd apps/web && npm run type-check`
3. `bash scripts/check-e2e-gate.sh --mode manifest`
4. `bash scripts/check-governance.sh`

### 7.6 边界

1. 不在本主线中新增第二套 Chat 或 KB 实现路径。
2. 不以“临时页面状态修补”代替 hook / store 下沉。
3. 不把新的流程控制逻辑继续堆回 `ChatWorkspaceV2.tsx` 或其他冻结中的单体文件。

---

## 八、推荐依赖顺序

### Wave 0：冻结真相面

先启动主线 B 中最靠前的工作：

1. 冻结 upload/chat/session/parse 契约。
2. 明确 message_id、replay、done/error 的统一语义。
3. 建立端到端验证基线。

原因：没有真相面，后续 Upload 和 Workspace 收口会持续返工。

### Wave 1：打通 Upload / Import

主线 A 在 Wave 0 完成后立即推进：

1. 补齐上传并发、恢复、重试。
2. 打通 Upload Workspace 与 KB Workspace 联动。
3. 用集成测试和页面测试固定行为。

### Wave 2：收口页面编排

主线 C 在 A、B 的核心能力稳定后推进：

1. 下沉 Chat / KB 状态。
2. 收束 Search 到 KB 的连续性。
3. 补齐 E2E 北极星旅程。

依赖图：

`主线 B(契约冻结与链路验证) -> 主线 A(上传导入闭环) -> 主线 C(工作台编排闭环)`

其中：

1. 主线 A 的前端恢复和上传队列实现，可在主线 B 的上传契约冻结完成后并行推进。
2. 主线 B 的 message persistence / SSE 硬化，可与主线 A 的前端上传体验并行。
3. 主线 C 不建议先做，否则容易在未稳定的契约和上传链路之上做二次拆分。

---

## 九、关键风险与防控

### 风险 1：范围再次扩散成“顺手重构整个系统”

防控：

1. 每条主线都只围绕 Upload -> Import -> KB -> Chat -> History 闭环。
2. 任何与此闭环无直接关系的视觉优化、模型替换、分析面板扩写都不进入本轮 P0。

### 风险 2：文档继续落后于代码

防控：

1. 本计划落地时，同步更新 `PLAN_STATUS.md`、契约文档和回填记录。
2. 每条主线完成后 24 小时内补 `last_verified_at` 与 `evidence_commits`。

### 风险 3：只做表面拆分，不做状态真源收口

防控：

1. 验收不以“文件变小”为主，而以“状态一致、链路稳定、测试覆盖”为主。
2. 任何新逻辑默认进入 hook / store / service，而不是回填到冻结单体组件里。

### 风险 4：测试补得太晚，导致后期难回归

防控：

1. 每条主线都要先补基线测试，再推进实现。
2. 至少保留单测、集成测试、E2E 三层验证中的两层；对北极星旅程必须有浏览器级验证。

---

## 十、完成定义

当且仅当以下条件同时满足，才视为本 phase 完成：

1. 上传、导入、知识库、Chat、历史消息这条主链路具备端到端自动化验证。
2. Upload Session、chat/session、SSE 三类契约在文档、SDK、前后端实现中没有漂移。
3. KB 和 Chat Workspace 的关键状态不再依赖多路 callback 拼接或冻结单体控制器承载。
4. 4 条北极星旅程全部通过页面级回归，其中关键路径至少一条通过 E2E 验证。
5. 治理脚本、契约脚本、fallback 脚本和类型检查全部通过。

---

## 十一、建议的第一步执行切片

如果要立刻开始执行，建议先从以下顺序切第一批任务：

1. 主线 B / Slice 1：冻结 upload/chat/session 契约，补 chat/session 集成基线。
2. 主线 A / Slice 1：补 Upload Session 集成测试，明确秒传、恢复、abort 的真实行为。
3. 主线 A / Slice 2：实现前端分片上传并发、重试、恢复。
4. 主线 C / Slice 1：把 KB Workspace 的导入完成联动从 fan-out callback 改为状态驱动。

这样做的收益是：

1. 第一周内就能获得真实验证信号。
2. 后续 Workspace 下沉不会建立在漂移契约上。
3. 每一步都能单独回归，不需要等到最后一周才知道闭环是否成立。