---
owner: ai-runtime
status: asset-ready
depends_on:
  - 2026-05-11_v4_0_phase_6_academic_rag_optimization_research
  - 24_v4_0_phase_6_execution_plan
last_verified_at: 2026-05-12
evidence_commits:
  - working-tree-v4-0-phase-6-doc-restore
---

# v4.0 Phase 6 Citation And Verification Contract

## 1. 目的

本文件定义 Chat、Compare、Review 在 Phase 6 内共享的 citation / claim verification contract，避免三个面继续各说各话。

## 2. Contract 目标

统一 contract 至少要回答四件事：

1. 当前回答或段落有哪些 claim
2. 每个 claim 是否被支持
3. 对应 citation / evidence 在哪里
4. 如果不被支持，下一步应该做什么

## 3. 最低字段集

### 3.1 claim-level

每个 claim 至少应表达：

1. `claim_id`
2. `claim_text`
3. `support_status`
4. `repair_hint`
5. `recovery_actions`

### 3.2 citation-level

每个 citation 至少应表达：

1. `paper_id`
2. `source_chunk_id`
3. `section_or_page`
4. `anchor_text` 或等效 evidence 摘要
5. `citation_jump` 或等效跳转能力

### 3.3 response-level

每个响应面至少应表达：

1. `answer_mode`
2. `unsupported_claims`
3. `recoveryActions` 或 `recovery_actions`
4. `degraded` 或等效状态

## 4. 三条链的对齐方式

### 4.1 Chat

Chat 是最直接的回答面，要求：

1. 显式暴露 recovery action
2. unsupported claim 不得只留在内部日志

### 4.2 Compare

Compare 的矩阵或结论不允许脱离 claim/citation 体系：

1. 若某个比较结论支撑不足，必须能落回 claim repair
2. `recovery_actions` 语义应与 RAG 主链一致

### 4.3 Review

Review 段落级 contract 至少应做到：

1. claim rows 有 support judgment
2. unsupported rows 有 repair hint
3. 段落或 claim 级能给出 recovery action

## 5. 明确禁止

1. Chat 使用一套 recovery 术语，Compare / Review 再自创一套
2. Compare 只有 prose judgement，没有 claim support
3. Review 只有 `repair_hint`，却没有可执行下一步动作
4. graph/global synthesis 输出绕开 citation grounding

## 6. 契约演进顺序

Phase 6 第一批真源优先级：

1. response-level recovery action
2. compare recovery_actions
3. review claim-level recovery_actions
4. 文档与资源契约同步承认这些字段

## 7. 结论

Phase 6 的 citation / verification contract 不是“多加几个字段”，而是把三条链的 truthfulness 与 recovery 语言统一到同一真源下。