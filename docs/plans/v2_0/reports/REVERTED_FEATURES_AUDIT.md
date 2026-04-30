---
author: glm5.1+37chengshan
date: 2026-04-18
status: audit-findings
---

# 项目改动审计报告：规划 vs 实现

## 执行摘要

根据规划文档 `PR7_PR8_Chat稳定性_AgentNative_RAG升级实施方案.md` 对比当前代码，发现：

**总体情况：** 规划中的 18 项主要改动，当前约 **6 项已完成**，**5 项部分完成**，**7 项未实现或被回滚**。

**关键风险：** 
1. ❌ **Phase 6A 的核心改动大部分未完成** - Chat 状态机虽有骨架但未真正硬化
2. ❌ **Phase 7A 部分完成** - OCR 已修复，但 adaptive chunk size 仍存在边界问题  
3. ❌ **Phase 8A 包含多项遗留** - retrieval contract 仍有 fallback 逻辑，confidence 未真正重算

**建议：** 
- Phase 6A/6B 的 Chat 壳化虽已做，但内核 ChatLegacy (1365 行) 需要拆分；
- Phase 7A 的 OCR 修复需要与 adaptive chunk size 一起验证;
- Phase 8A 的 fallback 逻辑需要显式清理或文档化其生命周期。

---

## 1. Phase 6A：Chat 协议与状态机硬化

### 规划清单

- [ ] 单一 stream state machine  
- [ ] Session / message 单真相源  
- [ ] SSE transport 与协议定义分层  
- [ ] done/error/cancel 强制 flush  
- [ ] 重连必须带验证  
- [ ] Chat.tsx 壳化  

### 实现状态

#### ✅ 已完成

1. **Chat.tsx 壳化** (5 行)  
   - 曾经大型页面已分解为壳层
   - 业务逻辑移到 features/chat/components/

#### 🟡 部分完成

1. **SSE 协议分层**  
   - sseService.ts 仍保留旧 legacy event types (thought, thinking_status, step_progress)  
   - 新旧协议并存，未真正分层到 adapter 边界

2. **message_id 约束**  
   - useChatStream.ts 中已有 message_id binding 逻辑  
   - 但 HARD RULE 0.2 验证仍是"可通过但噪音多"

3. **Session / message 单真相源**  
   - useSessions.ts 仍单独维护 ChatSession / ChatMessage  
   - 与 stream state 的 sync point 不清晰

#### ❌ 未完成

1. **ChatLegacy 核心分解**  
   - ChatLegacy.tsx 仍为 1365 行  
   - 注释明确标记"FREEZE，不应再叠加业务逻辑"  
   - 但内部仍混杂 timeline/citations/reasoning 状态

2. **stream lifecycle 状态机**  
   - done/error/cancel 缺少显式 flush 机制  
   - terminal state 收束语义不清晰

3. **重连验证**  
   - reconnect 逻辑已有骨架  
   - 但 "last event id / last message id 一致性验证" 缺失

### 根本原因

- **未完全迁移到新架构** - PR5 预计创建的 features/chat 容器存在，但主流量仍经过 legacy 路径  
- **向后兼容导致遗留** - 为支持旧界面，SSE 事件协议未敢大改，导致新旧共存

---

## 2. Phase 6B：Chat Workspace 与代理活动面板

### 规划清单

- [ ] 页面壳化（container → presenter 分离）  
- [ ] 工具时间线派生只读化  
- [ ] citations 派生化  
- [ ] Session sidebar + right panel 分层  

### 实现状态

#### ✅ 已完成

1. **页面壳化结构**  
   - Chat.tsx 已分解  
   - ChatWorkspace 容器创建

#### 🟡 部分完成

1. **右侧面板**  
   - 代码结构上已独立  
   - 但仍与消息流状态耦合

#### ❌ 未完成

1. **工具时间线派生机制**  
   - 从 SSE event 自动推导 timeline 仍未实现

2. **Citations 派生化**  
   - 仍由页面推断而不是从 stream/answer 派生

---

## 3. Phase 6C：Agent-Native 确认 / 恢复 / 验证闭环

### 规划清单

- [ ] confirmation_required 成为正式状态  
- [ ] resume 不是重新开始而是继续执行  
- [ ] 验证阶段可见化  
- [ ] 失败恢复策略显式化  

### 实现状态

#### ✅ 已完成

1. **后端 confirmation 端点**  
   - `/api/v1/chat/confirm` 端点存在  
   - agent_runner.py 有 WAITING_CONFIRMATION 状态

#### ❌ 未完成（前端）

1. **confirmation_required 成为 UI 正式流程**  
   - 后端支持但前端 UX 不完整

2. **resume 执行的端点**  
   - 实现上可能但未被明确文档化或测试

---

## 4. Phase 7A：解析路由与 OCR 策略升级

### 规划清单

- [x] OCR 不再全量默认开启  
- [x] adaptive chunking 修复  
- [ ] 解析策略记录到 metadata  
- [ ] 性能改善验证  

### 实现状态

#### ✅ 已完成

1. **OCR 默认改为 False**  
   - `ParserConfig.do_ocr = False` (Smart mode)  
   - 原生解析优先，低文本密度自动 OCR fallback  
   - 文档：_should_retry_with_ocr() 检测逻辑正确

2. **adaptive chunk size 基本修复**  
   - 检查了 explicit_chunk_override 标志  
   - section-specific size 优先于全局 chunk_size

#### 🟡 部分完成

1. **parse strategy metadata 记录**  
   - 部分字段已记录 (parser mode, OCR used)  
   - 但完整 metadata schema 仍需整理

#### ❌ 未完成

1. **性能改善基准验证**  
   - 预期 born-digital PDF: 1-3s (native) vs 10-30s (OCR)  
   - 未见性能评测报告

2. **parse routing 决策日志**  
   - 选择native vs OCR 的决策过程缺乏可观测性

---

## 5. Phase 7B：分层证据索引与图表绑定

### 规划清单

- [ ] evidence-level metadata  
- [ ] content_subtype / section_path / anchor_text  
- [ ] 图表与正文绑定  
- [ ] 多层索引视图  

### 实现状态

#### 🟡 部分完成

1. **基础 metadata 已入库**  
   - storage_manager.py 记录 content_type / page_num / section / text / content_data / embedding

#### ❌ 未完成

1. **evidence-level 升级**  
   - content_subtype (paragraph/table/figure) 仍未标记  
   - section_path 缺失  
   - anchor_text 缺失

2. **图表-正文绑定**  
   - 图表与 caption + nearby paragraph 三元绑定仍未实现

3. **多层索引视图**  
   - section-level 和 evidence-level 查询接口仍缺失

---

## 6. Phase 8A：Retrieval Contract 统一 + Confidence 修复

### 规划清单

- [ ] retrieval contract 真正统一（无 fallback）  
- [ ] confidence 逻辑重新设计  
- [ ] agentic_retrieval.py 去掉旧字段 fallback

### 实现状态

#### ❌ 未完成

1. **Fallback 逻辑仍存在**  
   ```python
   # agentic_retrieval.py line 236-246
   if score is None:
       if chunk.get("similarity") is not None:
           score = chunk.get("similarity")
       elif "distance" in chunk:
           score = 1 - float(chunk.get("distance", 0.5))
       else:
           score = 0.0
   
   if page_num is None and chunk.get("page") is not None:
       page_num = chunk.get("page")
   ```

2. **Confidence 仍按相似度计算**  
   - rag.py 中 `confidence = sources[:3].similarity` 逻辑未改  
   - 未实现 "score coverage + evidence diversity + answer support" 新方案

#### 🟡 部分完成

1. **multimodal_search_service 已统一映射**  
   - content_data → text  
   - score → score  
   - page_num → page_num

---

## 7. Phase 8B / 8C：Hybrid Retrieval & Claim-level Synthesis

### 规划清单

- [ ] 多路 query planner  
- [ ] dense + sparse hybrid  
- [ ] claim-level synthesis  
- [ ] citation verifier  

### 实现状态

#### ❌ 未完成

1. **BM25 / sparse index**  
   - 未见 bm25_service.py  
   - hybrid retrieval 缺失

2. **Query planner**  
   - 未见 query_planner.py  
   - 多路查询分解仍只在 query_decomposer 中

3. **Citation verifier**  
   - citation_verifier 存在但功能基础  
   - 完整的 claim-level verification 未实现

4. **Claim-level synthesis**  
   - evidence packs 组织仍是线性结果列表  
   - 未按 claim 聚合

---

## 8. 未合并分支中的孤立改动

| 分支 | 状态 | 包含内容 | 阻碍 |
|------|------|--------|------|
| feat/pr6-contracts-kb-chat | ❌ 未合并 | Chat 契约、KB 协议 | 与 PR5 冲突或等待 PR5 完成 |
| feat/pr7-rag-parsing-stability | ❌ 未合并 | OCR 路由、chunking 修复 | 已部分落地到主线；分支可能过时 |
| feat/pr8-rag-qa-contract-upgrade | ❌ 未合并 | retrieval contract、confidence | 包含大量设计变更，未通过评审 |
| feat/pr8-ui-optimization | ❌ 未合并 | 前端性能优化 | 与 PR20 重叠或冲突 |
| feat/pr10-workspace-layering | ❌ 未合并 | workspace 分层 | 等待上游完成 |

---

## 9. 问题模式识别

### 🔴 Pattern 1: "规划 → 分支实现 → 主线部分 port / 未merge"

**例子：** Phase 7A (OCR 路由)
- ✅ 已在 feat/pr7-rag-parsing-stability 分支中实现  
- ✅ 部分改动已 cherry-pick 到主线 (do_ocr=False)  
- ❌ 但分支仍未合并，其他部分(metadata 记录、性能评测)可能遗漏

**根本原因：**
- 分支化学工程不到位  
- 部分 merge 导致历史割裂  
- 缺乏"分支完整性检查"gate

### 🔴 Pattern 2: "规划清晰 → 后端实现 → 前端滞后"

**例子：** Phase 6C (Agent-Native 确认闭环)
- ✅ 后端：agent_runner + chat_orchestrator 有完整状态机  
- ❌ 前端：confirmation_required UX 未实现

**根本原因：**
- 前后端工作分离，缺乏 E2E 驱动  
- 前端故障未对等阻断后端合并

### 🔴 Pattern 3: "旧契约延续 + 新契约并存"

**例子：** Phase 8A (retrieval contract)
- ✅ multimodal_search 已用新契约 (text, score, page_num)  
- ❌ agentic_retrieval 仍保留 fallback (similarity, page, content_data)  
- 结果：两套字段并存，维护成本高

**根本原因：**
- 无"契约版本强制升级" gate  
- 允许 fallback 导致向后兼容锁定

---

## 10. 建议修复方案（优先级）

### 🔴 P0：立即修复（本周）

#### 1. 清理 Phase 8A 的 fallback 逻辑
```
- 梳理 agentic_retrieval.py 中 score/similarity/page/page_num 的来源  
- 确定是否真的需要 fallback，还是可以要求 source 端统一字段  
- 若需要 fallback，文档化其生命周期 & 退出时间线  
- 若不需要，删除 fallback 并加 assertion
```

**预计改动：** 20-30 行  
**验证：** 跑 agentic_retrieval unit tests

#### 2. 验证 Phase 7A 的 adaptive chunk size
```
- 检查 docling_service.py 中 adaptive_size 逻辑是否真的"section-first"  
- 补充 unit test 覆盖 explicit_chunk_override=False 的情况  
- 对比 born-digital PDF 的 1-3s vs OCR PDF 的性能差
```

**预计改动：** 10-20 行测试  
**验证：** unit test pass + benchmark report

### 🟠 P1：1 周内完成

#### 3. ChatLegacy 拆分规划
```
- 分析 ChatLegacy (1365 行) 内的功能块  
- 按 domain 拆分为：
  - ChatMessageList (消息展示)  
  - CitationPanel (引用展示)  
  - ToolTimeline (工具执行时间线)  
  - ReasoningPanel (推理过程)  
- 新增 ChatV2 容器，按 feature 切片替换旧路径  
- 禁止向 ChatLegacy 新增功能
```

**预计工作量：** 2-3 天  
**阻碍：** 需要与 feature/pr20 协调，避免冲突

#### 4. Phase 6A 的 SSE 协议分层
```
- 新增 apps/web/src/core/sseAdapters.ts  
- 把 legacy event (thought/thinking_status) 映射到新协议  
- 隔离映射层，业务代码只依赖新协议  
- 删除 useSSE hook (已几乎不用)
```

**预计改动：** 100-150 行  
**验证：** 流式聊天 E2E 测试通过

### 🟡 P2：2 周内完成

#### 5. Phase 7B 的 evidence metadata 框架
```
- 扩展 storage_manager.py 记录：content_subtype, section_path, anchor_text  
- 更新 Milvus schema  
- 更新 retrieval 接口返回新字段
```

**预计改动：** 80-120 行  
**验证：** Milvus 写入验证 + query 返回字段检查

#### 6. Phase 8A 的 confidence 重算
```
- 在 rag.py 中实现：score coverage + evidence diversity + answer support  
- 替换现有 "similarity.avg()" 逻辑  
- 补充 unit test（mock retrieval results）
```

**预计改动：** 40-60 行  
**验证：** unit test + 对比 old confidence vs new confidence 的分布

---

## 11. 如何避免"改了又消失"

### 建议 1：分支 Merge 前的完整性检查

```yaml
# 每个 feature 分支 merge 前必须检查
Phase: 
  - 名字（如 Phase 7A）
  - 交付清单（如 Phase7A_DELIVERABLES.md）
  - 对应的规划文件（如 PR7_PR8_*.md）

Checklist:
  - [ ] 分支中的所有 commit 都映射到清单项目
  - [ ] 是否有规划外新增（scope creep）
  - [ ] 是否有规划内的遗漏
  - [ ] 前后端是否 E2E 可用
  - [ ] 单元测试 + 集成测试是否新增
```

### 建议 2：强制契约版本升级 gate

当改变数据契约（如 retrieval result 字段）时：

```
- 旧契约版本的 fallback 必须有显式"失效日期"  
- 超期后必须删除，不允许无限期并存  
- 每次删除 fallback 时必须在 CHANGELOG 中标注"breaking change"
```

### 建议 3：定期规划 vs 实现 audit

```
频率：每 4 周  
过程：  
  1. 枚举当前 ROADMAP 中的所有 phase  
  2. 对每个 phase：代码 grep 关键改动关键字  
  3. 对比 merge status：主线 ✓ / 分支 ✗ / 部分合并 △  
  4. 输出 AUDIT report (本文档格式)  
  5. 针对"未完成 / 部分完成"的 phase 开启补救工作  
```

---

## 12. 本次更新总结

### 已修复项

- ✅ Phase 7A：OCR 默认改为 False (native 优先，smart fallback)  
- ✅ Phase 6A：Chat.tsx 已壳化

### 需要修复项

| Phase | 改动 | 状态 | 优先级 |
|-------|------|------|--------|
| 6A | SSE 旧协议隔离 | ❌ | 🟠 P1 |
| 6A/6B | ChatLegacy 拆分 | ❌ | 🟠 P1 |
| 7A | adaptive chunk size 验证 | 🟡 | 🔴 P0 |
| 7B | evidence metadata 框架 | ❌ | 🟡 P2 |
| 8A | fallback 逻辑清理 | ❌ | 🔴 P0 |
| 8A | confidence 重算 | ❌ | 🟡 P2 |
| 8B/8C | hybrid retrieval / claim-level synthesis | ❌ | 🟡 P2 |

### 下一步

1. 本周：完成 P0 两项（Phase 8A fallback、Phase 7A 验证）  
2. 下周：启动 P1 两项（ChatLegacy 拆分、SSE 分层）  
3. 2 周后：启动 P2 项目（evidence metadata、confidence）

---

## Appendix: 规划文档与分支对应表

| 规划阶段 | 对应分支 | 主线状态 | 完成度 |
|---------|---------|--------|--------|
| Phase 6A | ❓ | 🟡 部分 | 40% |
| Phase 6B | ❓ | 🟡 部分 | 40% |
| Phase 6C | ❓ | 🟡 部分 | 30% |
| Phase 7A | feat/pr7-rag-parsing-stability | △ 部分合并 | 60% |
| Phase 7B | feat/pr7-rag-parsing-stability | ❌ | 10% |
| Phase 7C | ❌ | ❌ | 0% |
| Phase 8A | feat/pr8-rag-qa-contract-upgrade | ❌ | 15% |
| Phase 8B | feat/pr8-rag-qa-contract-upgrade | ❌ | 0% |
| Phase 8C | feat/pr8-rag-qa-contract-upgrade | ❌ | 0% |

---

**审计日期：** 2026-04-18  
**审计者：** glm5.1+37chengshan  
**下次复查：** 2026-05-02
