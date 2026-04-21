---
owner: ai-runtime
status: in-progress
depends_on:
   - PR5
   - PR10
last_verified_at: 2026-04-17
evidence_commits:
   - wip-pr7-pr8
   - wip-review-2026-04-17
---

# PR-7 ~ PR-8 实施方案：Chat 稳定性 / Agent-Native → RAG 解析升级 → RAG 问答升级

> 适用前提：
> - **PR #3**（物理迁移到 `apps/*`）已完成
> - **PR #4**（迁移后稳定化）已完成
> - 假设 **PR-5 共享契约收口 + 前端工作台可用性** 已完成
>
> 本文档给出后续三段工作的实现方案：
> 1. **Chat 稳定性 / Agent-Native 收口**
> 2. **RAG 解析链路升级**
> 3. **RAG 问答链路升级**
>
> 本文基于当前仓库代码结构撰写；若某些文件在 PR-5 后已被新结构替换，本文会明确标注“**若 PR-5 已迁移**”或“**待确认**”。

---

## 1. 当前代码现状摘要

### 1.1 Chat 侧已经具备的基础

当前主线代码里，Chat 相关能力已经分散落在以下文件：

- `apps/web/src/app/pages/Chat.tsx`
- `apps/web/src/app/hooks/useChatStream.ts`
- `apps/web/src/app/hooks/useSessions.ts`
- `apps/web/src/stores/chatStore.ts`
- `apps/web/src/services/chatApi.ts`
- `apps/web/src/services/sseService.ts`
- `apps/api/app/api/chat.py`
- `apps/api/app/services/chat_orchestrator.py`
- `apps/api/app/core/agent_runner.py`
- `apps/api/app/core/streaming.py`
- `apps/api/app/core/sse_event_buffer.py`
- `apps/api/app/models/chat.py`

从现有实现可以确认：

- `Chat.tsx` 仍然很重，内部定义了 `ToolTimelineItem`、`CitationItem`、`ExtendedChatMessage` 等页面级扩展状态。
- `useChatStream.ts` 已经实现了独立状态机、message_id 绑定、reasoning/content 双 buffer。
- `useSessions.ts` 仍自己维护 `ChatSession` / `ChatMessage` 类型与会话同步逻辑。
- `chatApi.ts` 仍本地定义 `ChatMode` / `ChatScope`，说明聊天契约虽然在 PR-5 预计会部分共享，但目前主链路仍依赖前端本地 service。
- `sseService.ts` 持有完整的 SSE 协议定义与重连逻辑，说明 transport 和协议层尚未完全分离。
- `chat.py` + `chat_orchestrator.py` + `agent_runner.py` 已经形成了 Agent 运行、SSE 流式输出、确认机制的基础骨架。

### 1.2 RAG 解析链路当前问题

当前解析与入库链路主要集中在：

- `apps/api/app/core/docling_service.py`
- `apps/api/app/workers/import_worker.py`
- `apps/api/app/workers/pdf_coordinator.py`（待确认细节）
- `apps/api/app/workers/storage_manager.py`
- `apps/api/app/workers/streaming_parser.py`（待确认在主链路中的使用程度）
- `apps/api/app/core/milvus_service.py`
- `apps/api/app/core/qwen3vl_service.py`

已经确认的关键问题：

- `DoclingParser` 中 section adaptive chunk 逻辑仍存在“统一 chunk_size 覆盖 section-specific size”的问题：
  - `adaptive_size = chunk_size`
  - `adaptive_size = chunk_size or section_params["size"]`
- `ParserConfig.do_ocr` 默认仍为 `True`，说明 born-digital PDF 默认也会走 OCR，存在性能和质量损失风险。
- `storage_manager.py` 已统一把 Milvus 写入字段规范到 `text / page_num / section / content_data / embedding`，这是好基础，但还未上升到“evidence node”层级。

### 1.3 RAG 问答链路当前问题

当前问答与检索主线集中在：

- `apps/api/app/api/rag.py`
- `apps/api/app/core/agentic_retrieval.py`
- `apps/api/app/core/multimodal_search_service.py`
- `apps/api/app/core/intent_rules.py`
- `apps/api/app/core/query_metadata_extractor.py`
- `apps/api/app/core/synonyms.py`
- `apps/api/app/core/reranker_service.py`
- `apps/api/app/services/chat_orchestrator.py`

已经确认的关键问题：

- `agentic_retrieval.py` 仍然混用 `score/similarity`、`page/page_num`、`content/content_data/text` 回退逻辑，说明 retrieval contract 还未真正统一。
- `multimodal_search_service.py` 已经做了字段统一映射：`content_data -> text`、`score -> score`、`page_num -> page_num`，说明它更接近新真源。
- `rag.py` 的 confidence 仍然按 `sources[:3].similarity` 计算，和当前统一字段方向不一致。
- 当前系统已经具备 weighted RRF、意图识别、metadata filter、reranker 等能力，但还不是完整的 claim-level evidence QA。

---

## 2. 总体目标与原则

### 2.1 总体目标

完成 PR-5 之后，下一阶段不再以“结构治理”为核心，而是以 **系统稳定性和能力上限** 为核心：

1. **Chat 稳定性 / Agent-Native 收口**
   - 从“可流式聊天”升级为“可恢复、可验证、可追踪的 Agent-Native 交互层”。
2. **RAG 解析升级**
   - 从“PDF 切块 + 向量化”升级为“结构化证据解析与分层索引”。
3. **RAG 问答升级**
   - 从“dense retrieval + answer generation”升级为“hybrid retrieval + evidence pack + claim-level answer”。

### 2.2 必须遵守的原则

结合你上传的《Agent-Native 架构开发指南》，下一阶段建议遵守四个关键原则：

- **Parity**：用户在 UI 中能做的检索、问答、确认、恢复，Agent 也要能通过工具和状态机完成。
- **Granularity**：工具与事件设计保持原子性，不用“大而全”的高层黑盒工具。
- **Determinism**：流式协议、状态机、确认恢复、citation 输出必须可预测、可调试。
- **Agency**：Agent 要能自主规划、重试、验证，而不是只做一轮 prompt-response。 

这些原则会直接影响 Chat 稳定性设计、SSE 事件模型、检索编排与回答校验。参见《Agent-Native 架构开发指南》关于核心原则、状态机、工具设计与 UX 模式的说明 fileciteturn32file0
这些原则会直接影响 Chat 稳定性设计、SSE 事件模型、检索编排与回答校验。实现时需与仓内现有 API 契约和事件语义保持一致，避免新增不可回放或不可验证的隐式状态。

---

## 3. Phase 依赖顺序

### 3.1 总依赖图

```text
Phase 6A  Chat 协议与状态机硬化
    ↓
Phase 6B  Chat Workspace / Agent 活动面板收口
    ↓
Phase 6C  Agent-Native 确认/恢复/验证闭环
    ↓
Phase 7A  解析路由与 OCR 策略升级
    ↓
Phase 7B  分层证据索引 / 图表绑定 / 入库升级
    ↓
Phase 7C  解析质量门控与评测基线
    ↓
Phase 8A  Retrieval contract 统一 + confidence 修复
    ↓
Phase 8B  Hybrid retrieval + structured rerank
    ↓
Phase 8C  Claim-level synthesis + citation verifier
```

### 3.2 并行关系

#### 可并行
- `Phase 6B` 与 `Phase 7A` 可小规模并行：
  - 一个偏前端/流式状态
  - 一个偏 PDF 解析/OCR 路由

#### 不能颠倒
- `Phase 8A` 必须等待 `Phase 7B` 至少完成核心字段统一后再做。
- `Phase 8C` 必须建立在 `Phase 8B` 的 retrieval 与 rerank 基础上。
- `Phase 6C` 应在 `Phase 6A/6B` 完成之后，否则确认恢复闭环会绑定到不稳定的 message/source-of-truth 上。

---

## 4. Phase 6：Chat 稳定性 / Agent-Native 收口

# 目标

把当前的 Chat 主链路从：

- “能流式输出”

升级到：

- “状态机稳定”
- “消息单真相源”
- “SSE/Agent 事件可恢复、可验证、可观测”
- “符合 Agent-Native 的计划 / 执行 / 验证 / 确认 UX”

---

## 4.1 Phase 6A：协议与状态机硬化

### 目标

统一 Chat 流式协议与页面状态机，消除以下问题：

- 页面内部再定义一套消息扩展状态
- `useChatStream.ts`、`Chat.tsx`、`sseService.ts` 三者各持一部分协议/状态
- 断流、done、error、cancel 的收束语义不够清晰

### 重点改造

#### A. 统一 SSE / Stream 契约的单一消费面
当前：
- `apps/web/src/services/sseService.ts` 既定义协议，又管理 transport
- `apps/web/src/app/hooks/useChatStream.ts` 再定义 stream state
- `apps/web/src/app/pages/Chat.tsx` 再定义 UI 扩展 message

目标：
- `packages/types`（假设 PR-5 已完成）承接协议类型
- `apps/web/src/services/sseService.ts` 只保留 transport / reconnect / heartbeat
- `useChatStream.ts` 成为唯一的流式状态机
- `Chat.tsx` 只消费状态，不再定义协议级结构

#### B. 收口 terminal states
必须明确：
- `done`
- `error`
- `cancel`
- `confirmation_required`（若流结束等待用户）

的 UI 表现和状态转移。

#### C. 把 `message_id` 变成真正硬约束
现有代码已经很强调 HARD RULE 0.2，但还需要补：
- stale event 统计
- mismatch event 丢弃日志
- reconnect 后 last message binding 验证

### 修改文件

#### 前端（确定）
- `apps/web/src/app/pages/Chat.tsx`
- `apps/web/src/app/hooks/useChatStream.ts`
- `apps/web/src/services/sseService.ts`
- `apps/web/src/services/chatApi.ts`
- `apps/web/src/stores/chatStore.ts`

#### 前端（若 PR-5 已创建 workspace，则优先改这些）
- `apps/web/src/features/chat/hooks/useChatStreaming.ts`（**若存在，优先于旧 `app/hooks/useChatStream.ts`**）
- `apps/web/src/features/chat/components/ChatWorkspace.tsx`（**待确认**）
- `apps/web/src/features/chat/state/chatWorkspaceStore.ts`（**待确认**）

#### 后端（确定）
- `apps/api/app/api/chat.py`
- `apps/api/app/models/chat.py`
- `apps/api/app/services/chat_orchestrator.py`
- `apps/api/app/core/sse_event_buffer.py`

#### 后端（可能需要）
- `apps/api/app/utils/sse_manager.py`（**待确认是否仍为主链路**）
- `apps/api/app/core/streaming.py`（**若保留旧式 token streaming helper，则需同步 event shape**）

### 实现要点

1. **定义统一的 stream lifecycle**
   - `idle -> connecting -> streaming -> awaiting_confirmation | completed | error | cancelled`
2. **前端只允许一个流式消息源**
   - query cache / current session messages 为历史源
   - `useChatStream` 中的 `streaming assistant item` 为唯一瞬时源
3. **done/error/cancel 强制 flush**
   - flush reasoning
   - flush content
   - flush citations / tool timeline
4. **重连必须带验证**
   - last event id
   - current message id
   - 是否允许 resume
5. **增加可观测性字段**
   - reconnect count
   - stale event count
   - terminal reason

### 交付清单

- 单一 stream state machine
- 断流 / 重连 / done / error / cancel 行为一致
- `Chat.tsx` 体积显著下降
- 事件协议只在共享类型 + stream hook 中维护
- SSE transport 与协议定义分离

---

## 4.2 Phase 6B：Chat Workspace / Agent 活动面板收口

### 目标

把当前 `Chat.tsx` 的大页面职责拆开，让 Agent 活动展示变成稳定的派生面板，而不是和主消息流抢状态。

### 重点改造

#### A. 页面壳化
页面只做：
- route param
- scope 读取
- layout shell
- workspace mount

#### B. 工具时间线 / citations / reasoning 派生化
当前 `Chat.tsx` 内定义了 `ToolTimelineItem`、`CitationItem`、`ExtendedChatMessage`，说明这些状态还没有从消息主流里分离。

目标：
- timeline 从 stream events 派生
- citations 从 stream / final answer 派生
- reasoning panel 从 reasoning buffer 派生

#### C. Session / message 单真相源
当前 `useSessions.ts` 还自己持有 `ChatSession` / `ChatMessage` 结构。

目标：
- Session list query
- Current session query
- Message history query
- streaming transient item

统一为一套 state graph。

### 修改文件

#### 前端（确定）
- `apps/web/src/app/pages/Chat.tsx`
- `apps/web/src/app/hooks/useSessions.ts`
- `apps/web/src/stores/chatStore.ts`

#### 前端（若 PR-5 已迁移，优先改）
- `apps/web/src/features/chat/hooks/useChatSession.ts`（**待确认**）
- `apps/web/src/features/chat/components/SessionSidebar.tsx`（**待确认**）
- `apps/web/src/features/chat/components/ChatRightPanel.tsx`（**待确认**）
- `apps/web/src/features/chat/components/ChatMessageList.tsx`（**待确认**）
- `apps/web/src/features/chat/components/ScopeHeader.tsx`（**待确认**）

### 实现要点

1. `Chat.tsx` 中删除本地协议类型定义，转成 UI 装配层
2. `useSessions.ts` 只负责 session 维度，不再和 stream state 混写
3. 工具时间线由 `tool_call/tool_result` 事件生成，不再由页面推断
4. scope banner/header 固化
5. 右侧面板只读，不再管理消息写入

### 交付清单

- Chat Workspace（若 PR-5 已创建）接管主页面
- Session 与 stream 分层
- 右侧面板派生只读化
- scope 显示和切换清晰
- 页面可维护性提升

---

## 4.3 Phase 6C：Agent-Native 确认 / 恢复 / 验证闭环

### 目标

让 Chat 交互更符合 Agent-Native：
- 计划
- 执行
- 工具调用
- 验证
- 需要时请求确认
- 恢复继续执行

### 当前基础

后端已有：
- `agent_runner.py`：具备 `THINKING / TOOL_SELECTION / TOOL_EXECUTION / WAITING_CONFIRMATION / VERIFYING / COMPLETED` 状态
- `chat.py`：有 `/api/v1/chat/confirm` 端点
- `chat_orchestrator.py`：已有确认请求与 Redis 恢复逻辑基础

这意味着不需要从零设计，而是要把 **前端 UX 闭环** 和 **后端验证事件** 补齐。

### 修改文件

#### 前端（确定）
- `apps/web/src/app/pages/Chat.tsx`
- `apps/web/src/services/chatApi.ts`
- `apps/web/src/services/sseService.ts`

#### 前端（若 PR-5 已迁移）
- `apps/web/src/features/chat/components/ConfirmationPanel.tsx`（**可能新增**）
- `apps/web/src/features/chat/hooks/useChatWorkspace.ts`（**待确认**）

#### 后端（确定）
- `apps/api/app/api/chat.py`
- `apps/api/app/services/chat_orchestrator.py`
- `apps/api/app/core/agent_runner.py`
- `apps/api/app/models/chat.py`

### 实现要点

1. **confirmation_required 成为正式状态**
   - UI 展示操作详情 / 风险级别 / approve / reject
2. **resume 不是重新开始，而是继续 execution**
3. **验证阶段可见化**
   - phase / tool / verifier 输出到 timeline
4. **失败恢复策略显式化**
   - retry same step
   - fallback tool
   - abort gracefully

### 交付清单

- confirmation UI 闭环
- resume execution 闭环
- agent phase 与 tool timeline 更可信
- Chat 交互更贴近 Agent-Native 运行模型

---

## 5. Phase 7：RAG 解析升级

# 目标

把当前解析链路从：

- `Docling -> chunks -> embeddings -> Milvus`

升级到：

- `Document routing -> structured parse -> evidence indexing -> quality gating`

---

## 5.1 Phase 7A：解析路由与 OCR 策略升级

### 当前已确认问题

#### A. adaptive chunk size 未真正生效
`docling_service.py` 里：
- `adaptive_size = chunk_size`
- `adaptive_size = chunk_size or section_params["size"]`

说明只要传了全局 `chunk_size`，section-specific size 实际就不会生效。

#### B. OCR 默认全开
`ParserConfig.do_ocr = True`

这会导致 born-digital PDF 也默认走 OCR，带来：
- 速度下降
- 文本顺序稳定性下降
- 解析噪声增加

### 修改文件

#### 确定
- `apps/api/app/core/docling_service.py`
- `apps/api/app/workers/import_worker.py`
- `apps/api/app/workers/pdf_coordinator.py`（**若其负责 parse routing，需同步**）

#### 可能需要
- `apps/api/app/core/settings.py` / `config.py`（**待确认 OCR/parse 参数定义位置**）
- `apps/api/app/schemas/papers.py`（**若需暴露 parse strategy 配置**）

### 实现要点

1. **chunk strategy 修正**
   - section-specific size 必须优先于默认值，除非显式 override
2. **OCR route 引入**
   - born-digital PDF：默认 native parse
   - scanned / image-heavy：启用 OCR
   - mixed pages：页级路由（可二期）
3. **解析策略记录到 metadata**
   - parser mode
   - ocr used
   - chunk strategy
   - parse warnings

### 交付清单

- adaptive chunking 真正生效
- OCR 不再全量默认开启
- parse mode 可追踪
- 解析耗时和质量改善

---

## 5.2 Phase 7B：分层证据索引与图表绑定

### 当前基础

`storage_manager.py` 已将文本写入 Milvus 时统一记录：
- `content_type`
- `page_num`
- `section`
- `text`
- `content_data`
- `embedding`

这是一个好起点，但仍然主要是“chunk storage”，还不是“evidence indexing”。

### 目标

把索引层升级为：
- section summary
- paragraph / evidence span
- table / figure evidence
- 图表与附近正文绑定

### 修改文件

#### 确定
- `apps/api/app/workers/storage_manager.py`
- `apps/api/app/core/milvus_service.py`
- `apps/api/app/core/qwen3vl_service.py`

#### 可能需要
- `apps/api/app/workers/streaming_parser.py`（**若负责 chunk-level parse/serialize**）
- `apps/api/app/workers/pdf_coordinator.py`（**若负责 parse stage composition**）
- `apps/api/app/core/neo4j_service.py`（**若要同步 section/chunk graph**）

### 实现要点

1. **新增 evidence-level metadata**
   - `content_subtype`
   - `section_path`
   - `anchor_text`
   - `figure_id/table_id`
   - `caption`
   - `nearby_explanation`
2. **文本与图表绑定**
   - 图 / 表 + caption + nearby paragraph 三元绑定
3. **多层索引视图**
   - section-level
   - evidence-level
   - figure/table-level

### 交付清单

- 文本与图表证据绑定增强
- 检索粒度从 chunk 提升到 evidence
- 多模态证据检索质量提高

---

## 5.3 Phase 7C：解析质量门控与评测基线

### 目标

不要让坏 chunk / 坏 OCR / 错位 section 无门槛进入主索引。

### 修改文件

#### 确定
- `apps/api/app/core/docling_service.py`
- `apps/api/app/workers/storage_manager.py`

#### 可能新增
- `apps/api/app/core/chunk_quality.py`（**建议新增**）
- `apps/api/tests/unit/test_docling_service.py`（**若已存在则扩充**）
- `tests/evals/` 下解析质量 fixture（**建议新增**）

### 实现要点

1. 质量门控指标：
   - chunk 长度分布
   - header/footer 噪声
   - OCR confidence
   - section completeness
   - table serialization 质量
2. 低质量 chunk：
   - 不入主索引
   - 或降级到 fallback index
3. 建解析评测 fixture：
   - born-digital
   - scanned
   - table-heavy
   - figure-heavy

### 交付清单

- parse quality report
- 低质量 chunk gate
- 解析 regression fixture

---

## 6. Phase 8：RAG 问答升级

# 目标

把当前问答链路从：

- intent + dense retrieval + weighted RRF + rerank + answer

升级到：

- unified retrieval contract + hybrid retrieval + structured evidence packs + claim-level synthesis + citation verification

---

## 6.1 Phase 8A：Retrieval contract 统一 + confidence 修复

### 当前已确认问题

- `multimodal_search_service.py` 已在向统一字段靠拢：
  - `content_data -> text`
  - `score -> score`
  - `page_num -> page_num`
- 但 `agentic_retrieval.py` 仍大量使用 fallback：
  - `score/similarity`
  - `page/page_num`
  - `content/content_data`
- `rag.py` 的 confidence 还在按 `similarity` 计算。

### 修改文件

#### 确定
- `apps/api/app/core/agentic_retrieval.py`
- `apps/api/app/core/multimodal_search_service.py`
- `apps/api/app/api/rag.py`

#### 可能需要
- `apps/api/app/schemas/rag.py`
- `apps/api/app/schemas/common.py`
- `packages/types` 中的 RAG DTO（**假设 PR-5 后已存在，可同步扩展**）

### 实现要点

1. **统一 retrieval contract**
   - `paper_id`
   - `paper_title`
   - `text`
   - `score`
   - `page_num`
   - `section`
   - `content_type`
2. **agentic_retrieval 去掉旧字段 fallback 的主路径依赖**
3. **confidence 重新计算**
   - 用 `score coverage + evidence diversity + answer support`
   - 不再只看 `similarity`

### 交付清单

- retrieval contract 真正统一
- confidence 逻辑修正
- sources/citations 字段更可信

---

## 6.2 Phase 8B：Hybrid retrieval + structured rerank

### 当前基础

你现在已经有：
- metadata filter
- synonyms expand
- intent rules
- weighted RRF
- reranker

但还缺：
- sparse lexical recall
- query planner
- structured rerank payload

### 修改文件

#### 确定
- `apps/api/app/core/multimodal_search_service.py`
- `apps/api/app/core/intent_rules.py`
- `apps/api/app/core/query_metadata_extractor.py`
- `apps/api/app/core/synonyms.py`
- `apps/api/app/core/reranker_service.py`
- `apps/api/app/core/milvus_service.py`

#### 可能新增
- `apps/api/app/core/bm25_service.py`（**建议新增，若当前无 sparse index**）
- `apps/api/app/core/query_planner.py`（**建议新增**）

### 实现要点

1. **多路 query planner**
   - raw query
   - keyword-heavy
   - entity-expanded
   - table/figure aware
   - comparison-aware
2. **dense + sparse hybrid**
3. **structured rerank input**
   - title
   - section
   - page
   - content_type
   - text/caption

### 交付清单

- hybrid retrieval
- query planner
- structured rerank
- top-k 纯度提升

---

## 6.3 Phase 8C：Claim-level synthesis + citation verifier

### 目标

把回答生成从“给模型一堆 chunk”升级为“给模型一组 evidence packs”。

### 修改文件

#### 确定
- `apps/api/app/core/agentic_retrieval.py`
- `apps/api/app/api/rag.py`
- `apps/api/app/services/chat_orchestrator.py`

#### 可能新增
- `apps/api/app/core/citation_verifier.py`（**建议新增**）
- `apps/api/app/core/claim_synthesizer.py`（**建议新增**）
- `tests/evals/rag_claims/`（**建议新增**）

### 实现要点

1. **evidence blocks -> evidence packs**
   - 按 claim 组织证据
2. **unsupported claim pruning**
3. **citation verifier**
   - 每句话都要能对齐来源
4. **answer judge / self-check**
   - 证据不足时降级
   - 不要硬答

### 交付清单

- claim-level answer generation
- citation verification
- unsupported claim pruning
- 更稳的学术问答输出

---

## 7. 推荐的 PR 拆分方式

### PR-6：Chat 稳定性 / Agent-Native 收口

#### 范围
- Chat 状态机
- SSE 协议消费面
- Session/message 单真相源
- 确认/恢复/验证闭环

#### 目标
- 让 Chat 真正稳定并且符合 Agent-Native 交互范式

---

### PR-7：RAG 解析升级

#### 范围
- Docling / OCR route
- adaptive chunking 修复
- evidence indexing
- parse quality gate

#### 目标
- 提高解析质量与检索上限

---

### PR-8：RAG 问答升级

#### 范围
- retrieval contract 统一
- hybrid retrieval
- rerank 结构化
- claim-level synthesis
- citation verifier

#### 目标
- 提高学术问答的命中率、可信度和稳定性

---

## 8. 最终交付总清单

### Chat 稳定性 / Agent-Native
- [ ] 单一 stream state machine
- [ ] Session / message 单真相源
- [ ] SSE transport 与协议定义分层
- [ ] confirmation / resume / verify UX 闭环
- [ ] Chat page 壳化 / workspace 化（若 PR-5 已迁移）

### RAG 解析升级
- [ ] adaptive chunking 修复
- [ ] OCR route 落地
- [ ] 证据层索引 metadata
- [ ] 图表-正文绑定增强
- [ ] parse quality gate
- [ ] parse regression fixture

### RAG 问答升级
- [ ] retrieval contract 统一
- [ ] confidence 逻辑修复
- [ ] hybrid retrieval
- [ ] query planner
- [ ] structured rerank
- [ ] claim-level synthesis
- [ ] citation verifier
- [ ] eval fixture / benchmark 初版

---

## 9. 一句话总结

假设 PR-5 已完成，后续最优路径不是继续做仓库治理，而是：

1. **先把 Chat 做稳定，收成真正的 Agent-Native 交互层**
2. **再把解析链路升级为 evidence-oriented parsing**
3. **最后把问答链路升级为 evidence-driven academic QA**

这是从“架构整理”走向“能力上限提升”的关键分界线。
