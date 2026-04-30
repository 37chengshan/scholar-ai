---
标题：ScholarAI v3.0-C Span-level Citation + Claim Verification 研究文档
日期：2026-04-28
状态：research
范围：span-level citation、claim-level verification、evidence anchor、unsupported claim 可视化
前提：文档层假设 Phase A 与 Phase B 的结构性产物已完成并可复用；不等同于仓库当前代码状态已全部完成
---

# 1. 研究目标

本文件定义 ScholarAI `v3.0-C: Span-level Citation + Claim Verification` 的研究方案。

它回答的核心问题是：

```txt
怎样把当前“有 citation / 有 claim verification 雏形”的系统，
升级成真正能按 claim 审核、按证据回跳、按 unsupported 暴露风险的学术可信引用链。
```

本文件只定义目标闭环、系统边界、canonical 结构、产品语义和升级路径；不展开到逐文件 patch、OCR 细节或 verifier 参数调优。

# 2. 执行摘要

当前仓库并不是完全没有 citation / verification 能力，而是已经有一套可复用的早期基础：

1. 后端 API 契约已承认 `claimVerification`、`answerMode`、`unsupportedClaimRate` 等字段：
   - `docs/specs/architecture/api-contract.md`
2. 后端已有 claim / citation verifier 雏形：
   - `apps/api/app/core/claim_verifier.py`
   - `apps/api/app/core/citation_verifier.py`
3. 后端已有 evidence jump contract：
   - `apps/api/app/services/evidence_contract_service.py`
4. 前端已有 answer contract / evidence panel / citation jump UI：
   - `apps/web/src/features/chat/components/workspaceTypes.ts`
   - `apps/web/src/features/chat/components/evidence/*`
   - `apps/web/src/features/kb/components/KnowledgeReviewPanel.tsx`

这说明 `Phase C` 的正确方向不是新造第二套 citation 系统，而是：

```txt
把当前 page/chunk 级 citation 雏形，
升级成统一的 claim-first、evidence-anchor-first、UI 可修复的可信引用主链。
```

# 3. 前提假设

本文件写作时采用以下前提：

1. `Phase A` 已提供 claim / gold evidence / benchmark gate 的结构性基线。
2. `Phase B` 已把更多真实外部论文导入 KB，形成更复杂的 citation / verification 输入。
3. 这不表示当前仓库代码里 A/B 全部实现已交付，只表示 Phase C 文档默认可以消费它们定义好的结构边界。

换句话说：

```txt
Phase C 文档把 Phase A / B 当成“已定义并可复用的上游产物”，
不是把现实仓库状态误判成“所有前置工作都已完成”。
```

# 4. 当前基线盘点

## 4.1 前端基线

当前前端已经具备 evidence UI 基础：

1. `workspaceTypes.ts`
   - 已有 `CitationItem`
   - 已有 `AnswerClaim`
   - 已有 `EvidenceBlock`
2. `EvidencePanel`
   - 已能展示 claims、citations、evidence blocks
3. `ChatWorkspaceV2`
   - 已支持 `citation_jump_url`
   - 已支持 unsupported / partial 的基础状态表达
4. `KnowledgeReviewPanel`
   - 已能在 review draft 上展示 citation 与 evidence

这意味着：

1. 不需要再新造一套独立 citation 页面
2. 正确做法是增强现有 Chat / Read / Review 的 evidence contract

## 4.2 后端基线

当前后端已经具备：

1. `claim_verifier.py`
   - 已有 claim support report 雏形
2. `citation_verifier.py`
   - 已有 sentence-level citation coverage 校验
3. `evidence_contract_service.py`
   - 已有 `citation_jump_url`
   - 已有 `source_chunk_id -> page / section / content` 回查
4. `agentic_retrieval.py`
   - 已产出 `claimVerification`
   - 已产出 `citation_verification`
   - 已产出 `unsupportedClaimRate`

这说明：

1. Phase C 的难点不是“让系统第一次输出 citation”
2. 难点是把 citation 从 page/chunk 级提示，升级成 claim-level 的正式可信契约

## 4.3 当前不足

当前实现仍有四个关键缺口：

1. `CitationItem` 仍以 `page_num / source_chunk_id / section_path` 为主，没有正式 `quote_span / source_offset / bbox`
2. `claim_verifier.py` 主要基于 token overlap，是工程启发式，不是正式 evidence grounding
3. `citation_verifier.py` 主要校验句子有没有 citation，不能证明 citation 是否真的支撑该 claim
4. `ReviewDraft` 和 Chat 虽然已有 evidence 展示，但还没有“逐 claim 展开 -> 看证据 -> 重检索修复”的正式闭环

# 5. 为什么 Phase C 必须在 v3.0 中单独成立

## 5.1 只看 page-level citation 不够

对于学术工作流来说，“这段回答来自第 7 页”远远不够。用户真正需要知道的是：

1. 哪个 claim 被哪段原文支撑
2. 支撑是强还是弱
3. 如果不支撑，哪里断了

## 5.2 claim 才是用户真正审核的单位

用户审核综述、问答、比较结果时，不是按 page 审核，而是按论断审核。

所以 `Phase C` 的主语应从：

```txt
page / chunk citation
```

升级为：

```txt
claim
-> evidence anchor
-> verification result
-> repair action
```

## 5.3 它是 Review Draft 可审计化的前提

如果 Review Draft 仍然只到 paragraph-level citation，那么：

1. 段内多个 claim 无法区分哪些被支撑
2. unsupported claim 会被正文淹没
3. 用户无法只修一条错误 claim

# 6. Phase C 的正式目标

`Phase C` 需要同时满足以下六个目标：

1. `统一 claim 单元`
   - Chat answer 与 Review Draft 都要能拆成 claim
2. `统一 evidence anchor`
   - citation 统一绑定到 quote/span/offset，而不是只停留在 page
3. `统一 verification`
   - 每个 claim 有显式 support result
4. `统一暴露风险`
   - unsupported / weakly supported 必须在 UI 可见
5. `统一修复入口`
   - 用户可对单个 claim 重检索 / 重验证 / 修复 citation
6. `统一消费主链`
   - Chat、Read、Review 共享同一套 evidence contract，而不是各自维护一套

# 7. 产品主链定义

建议将 `Phase C` 的主链固定为：

```txt
retrieval results
-> normalized evidence anchors
-> claim segmentation
-> claim-to-evidence linking
-> claim verification
-> supported / weak / unsupported surfacing
-> user repair / retry
-> updated answer / updated draft
```

关键点：

1. citation 不再只是最终回答的装饰物
2. verification 不再只是后台分数，而是用户可见、可操作的审稿界面一部分

# 8. 推荐的系统边界

## 8.1 前端边界

前端负责：

1. 展示 claim 列表
2. 展示 claim support 状态
3. 展示 evidence anchor / quote / jump
4. 暴露单 claim repair CTA
5. 区分 supported / weak / unsupported

前端不负责：

1. claim 真源切分
2. support 真伪判定
3. bbox / offset 真源生成
4. 伪造 citation 修正结果

## 8.2 后端边界

后端负责：

1. claim segmentation
2. evidence anchor normalization
3. claim-to-evidence linking
4. verification result 生成
5. citation jump payload 生成
6. unsupported / repairable reason 生成

## 8.3 真源边界

统一真源：

1. claim 真源：answer/review pipeline 输出的 `ClaimUnit`
2. evidence 真源：retrieval source + chunk index + locator contract
3. verification 真源：claim verifier / citation verifier / review validator
4. 消费真源：Chat evidence panel、Read jump、Review Draft inspection

# 9. 当前系统最值得复用的资产

建议明确复用以下已有资产，而不是并行重写：

1. `claimVerification` API 字段契约
2. `EvidenceBlockDto` / `AnswerContractDto`
3. `citation_jump_url`
4. `EvidencePanel`、`CitationInline`、`KnowledgeReviewPanel`
5. `agentic_retrieval.py` 中已有的 claim / citation report 输出链

结论：

```txt
Phase C 不是重写聊天回答结构，
而是升级已有 answer contract 和 review contract 的证据粒度与可审计性。
```

# 10. Canonical 数据结构建议

## 10.1 ClaimUnit

建议引入统一 `ClaimUnit` 概念，作为 Chat 与 Review 共用的最小审核单元。

最小字段建议：

1. `claim_id`
2. `claim_text`
3. `claim_type`
   - `fact`
   - `comparison`
   - `numeric`
   - `limitation`
   - `interpretation`
4. `surface_context`
   - 所属回答句子或段落
5. `source_context`
   - `chat_answer | review_paragraph | compare_cell`
6. `position`
   - answer / paragraph 内相对顺序

## 10.2 EvidenceAnchor

建议把当前 citation 升级成正式 `EvidenceAnchor`。

最小字段建议：

1. `evidence_id`
2. `paper_id`
3. `source_chunk_id`
4. `page_num`
5. `section_path`
6. `content_type`
   - `text | table | figure`
7. `quote_text`
8. `quote_span`
   - `start_offset`
   - `end_offset`
9. `anchor_text`
10. `citation_jump_url`
11. `bbox`
   - 可选，P0 不强制全量存在

设计原则：

1. `quote_span / offset` 是 P0 正式主线
2. `bbox` 是高价值增强，不应阻塞整体 Phase C

## 10.3 ClaimCitationLink

建议引入 claim 与 evidence 的显式关联结构：

1. `claim_id`
2. `evidence_id`
3. `support_role`
   - `primary`
   - `secondary`
   - `contrast`
4. `support_score`
5. `verifier_notes`

## 10.4 ClaimVerificationResult

最小字段建议：

1. `claim_id`
2. `support_level`
   - `supported`
   - `weakly_supported`
   - `unsupported`
3. `support_score`
4. `evidence_ids[]`
5. `unsupported_reason`
6. `repairable`
7. `repair_actions[]`

# 11. 为什么 P0 应优先做 offset/span，而不是先追求 bbox 全覆盖

这是 `Phase C` 最关键的策略之一。

建议 P0 主线：

1. 先建立 `quote_text + source_offset + source_chunk_id` 的正式 locator
2. 再把 `citation_jump_url` 与 Read 页面联动稳定
3. `bbox` 作为增强字段，只在可稳定提取的文档上输出

原因：

1. 扫描版 PDF、公式密集 PDF、OCR 漂移会让 bbox 成本极高
2. 如果一开始就把全量 bbox 当作硬前提，Phase C 会被 PDF 定位工程拖死
3. `offset/span` 已足以支撑大部分 claim-level verification 与 UI 修复

# 12. Claim Verification 正式语义建议

当前系统已经有 `supported / weak / unsupported` 雏形，但 Phase C 要把它变成正式产品语义。

建议固定为：

1. `supported`
   - 有足够 evidence anchor 支撑 claim 主体
2. `weakly_supported`
   - 有相关 evidence，但支撑不完整、跨度过大、或只能支撑局部
3. `unsupported`
   - 当前 evidence 无法支撑 claim，或 citation 与 claim 明显错配

关键约束：

1. `unsupported` 不能只存在于日志或 trace 中
2. `weakly_supported` 不能被前端伪装成正常 citation
3. `supported` 也必须能展开看到具体 evidence

# 13. Chat / Review 的统一消费建议

## 13.1 Chat

Chat 中每次正式回答建议同时输出：

1. `claims[]`
2. `citations[]`
3. `evidence_blocks[]`
4. `claim_verification`

UI 最低要求：

1. 用户可展开每条 claim
2. 查看 claim 绑定 evidence
3. 对 unsupported claim 明确标红或降级提示

## 13.2 Review Draft

Review Draft 不应停留在 paragraph-level citation。

建议目标：

1. 段内关键 claim 可被枚举
2. 每条 claim 可查看其 support level
3. unsupported claim 可单独重新检索或触发局部重写

## 13.3 Read

Read 页的责任不是重新判断 support，而是承接跳转定位：

1. 跳到 page
2. 高亮 quote span
3. 在具备条件时展示 bbox 高亮

# 14. Phase C 的正式风险

最需要避免的 7 个错误：

1. 新造第二套 claim/citation 数据结构，不复用现有 answer contract
2. 把 sentence-level citation coverage 当成 claim verification
3. 把 page jump 误当成 span-level citation 已完成
4. 把 bbox 作为 P0 唯一主线，导致整体延期
5. unsupported claims 只存在后端日志，不在 UI 可见
6. Chat 与 Review 各自维护一套 verification 逻辑
7. 用户不能只修一条 claim，只能整段重跑

# 15. 与 Phase A / B / D / E 的关系

## 15.1 与 Phase A

Phase A 提供：

1. claim/gold evidence 的评测基线
2. blind benchmark 对 verification 改动的约束

## 15.2 与 Phase B

Phase B 提供：

1. 更多真实外部论文输入
2. `fulltext_ready` 论文可进入 citation / verification 主链

## 15.3 与 Phase D

Phase D 将验证：

1. 扫描版 PDF
2. 图表密集论文
3. 公式密集论文
4. 跨学科 KB

这些都是 Phase C 真正会暴露问题的场景。

## 15.4 与 Phase E

Phase E 会承接：

1. verifier latency
2. per-claim retry 成本
3. locator cache
4. trace / error state / cancellation

# 16. 正式建议

基于现有代码与 v3.0 主线，`Phase C` 的正式建议是：

1. 继续复用现有 answer/review evidence contract，不新造平行 citation 系统。
2. 先把 citation 真源升级到 `quote_text + source_offset + source_chunk_id`。
3. 把 `ClaimUnit` 作为 Chat 与 Review 的统一审核单元。
4. 把 `supported / weakly_supported / unsupported` 变成正式 UI 状态，而不是后台分数。
5. 让用户能对单条 claim 做 repair，而不是整段重跑。
6. `bbox` 作为高价值增强，不阻塞 P0 主链。

# 17. 结论

一句话总结：

```txt
Phase C 的本质，不是“把 citation 再做细一点”，
而是把 ScholarAI 从“有引用的回答系统”，
升级成“能按 claim 审核、按证据回跳、按 unsupported 暴露风险并允许修复”的学术可信工作流系统。
```
