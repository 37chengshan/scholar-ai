# 09 v3.0-C 执行计划：Span-level Citation + Claim Verification

> 日期：2026-04-28  
> 状态：execution-plan  
> 上游研究：`docs/plans/v3_0/active/phase_c/2026-04-28_v3_0C_Span_Citation_Claim_Verification_研究文档.md`  
> 文档前提：按“Phase A / Phase B 结构性产物已完成并可复用”来组织执行，不代表仓库当前代码状态已完全完成

## 1. 目标

`Phase C` 的执行目标是把当前 citation / evidence / claim report 雏形，收口成真正可实施的 claim-first 可信引用主链，形成：

```txt
retrieval
-> evidence anchor normalization
-> claim segmentation
-> claim-to-evidence linking
-> verification
-> supported / weak / unsupported surfacing
-> repair / retry
-> updated answer / updated draft
```

## 2. 执行前先读什么

执行者开始前，按以下顺序读取：

1. `docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md`
2. `docs/plans/v3_0/active/phase_c/2026-04-28_v3_0C_Span_Citation_Claim_Verification_研究文档.md`
3. `docs/plans/v3_0/active/phase_b/08_v3_0B_execution_plan.md`
4. `docs/plans/v3_0/active/phase_a/07_v3_0A_execution_plan.md`
5. `docs/specs/architecture/api-contract.md`
6. `docs/specs/domain/resources.md`
7. `apps/api/app/services/evidence_contract_service.py`
8. `apps/api/app/core/claim_verifier.py`
9. `apps/api/app/core/citation_verifier.py`
10. `apps/web/src/features/chat/components/workspaceTypes.ts`

执行规则：

1. 先复用现有 answer / review evidence contract，再补 claim-first 缺口。
2. 先冻结 claim unit 与 evidence anchor 语义，再补 verifier 和 UI repair。
3. 任何实现都不得新造第二套 citation / claim 数据结构。

## 3. Work Packages

## WP0：Canonical Contract Freeze

目标：

1. 冻结 `ClaimUnit`
2. 冻结 `EvidenceAnchor`
3. 冻结 `ClaimVerificationResult`

执行方式：

1. 以 Phase C 研究文档为准定义 claim / evidence / verification 最小字段
2. 让 Chat answer、Review Draft、Evidence panel 共享同一套 canonical 语义

验收：

1. 前后端不再各自维护一套 claim / citation shape。

## WP1：Evidence Anchor Upgrade

目标：

1. 把 citation 从 page / chunk 提示升级成正式 anchor contract
2. 建立 `quote_text + source_offset + source_chunk_id` 主线

执行方式：

1. 复用 `evidence_contract_service.py`
2. 保留 `citation_jump_url` 主链
3. 先以 `offset/span` 为 P0，`bbox` 只作为增强字段

验收：

1. evidence anchor 不再只剩 page 跳转语义。

## WP2：Claim Segmentation Unification

目标：

1. 让 Chat 和 Review 都使用同一 `ClaimUnit`
2. 让 claim 成为正式审核单元

执行方式：

1. 复用现有 `claimVerification` 输出链
2. 统一 Chat answer / Review paragraph 的 claim 结构
3. 不允许 Review 单独维护一套 claim 模型

验收：

1. claim 可被稳定枚举，且可回链到 answer / paragraph 上下文。

## WP3：Verifier Hardening

目标：

1. 把现有启发式 verifier 升级成正式 Phase C 主链的一部分
2. 明确 `supported / weakly_supported / unsupported` 的产品语义

执行方式：

1. 复用 `claim_verifier.py`
2. 复用 `citation_verifier.py`
3. 不把 sentence-level coverage 冒充成 claim-level support

验收：

1. verifier 输出可直接支撑 UI 的 support 状态展示。

## WP4：Unsupported Surfacing

目标：

1. 让 unsupported / weak claims 在 UI 中真实可见
2. 不让 unsupported claim 只留在 trace 或日志中

执行方式：

1. 复用 `EvidencePanel`、`ClaimSupportList`、`KnowledgeReviewPanel`
2. 将 verifier 结果映射为用户可理解的 badge / state / warning
3. Chat 与 Review 使用同一套 support 状态语义

验收：

1. 用户能在 Chat / Review 中明确看到 claim 支撑强弱。

## WP5：Claim Repair Loop

目标：

1. 用户可针对单条 claim 做 repair，而不是整段重跑
2. 建立重检索 / 重验证 / 修复 citation 的最小闭环

执行方式：

1. 单 claim 作为 repair 入口单位
2. repair 结果回写到 answer / draft 的 canonical contract
3. 不新造独立 repair 数据模型

验收：

1. 单条 claim 可触发局部修复，不必整段重生成。

## WP6：Chat / Review / Read 主链接入

目标：

1. 让 Phase C 真正进入主工作流，而不是停留在后端报告字段

执行方式：

1. Chat 使用统一 `claims[] + citations[] + evidence_blocks[] + claim_verification`
2. Review Draft 使用同一 verifier 语义
3. Read 页承接 `citation_jump_url + quote anchor` 的落点定位

验收：

1. Chat / Review / Read 的 evidence 体验保持一致，不再各说各话。

## 4. 实际执行顺序

执行者按以下顺序推进：

1. `WP0 Canonical Contract Freeze`
2. `WP1 Evidence Anchor Upgrade`
3. `WP2 Claim Segmentation Unification`
4. `WP3 Verifier Hardening`
5. `WP4 Unsupported Surfacing`
6. `WP5 Claim Repair Loop`
7. `WP6 Chat / Review / Read 主链接入`

原因：

1. contract 不冻，前后端会继续各写一套 claim / citation 字段。
2. evidence anchor 不升级，后续 verification 仍然只会停留在 page-level 幻觉。
3. verifier 不收口，UI 只能展示零散字段，不能形成正式审稿工作流。

## 5. 下层文档

当前 Phase C 已有：

1. `docs/plans/v3_0/active/phase_c/2026-04-28_v3_0C_Span_Citation_Claim_Verification_研究文档.md`

后续建议补齐：

1. `v3_0C_kickoff_freeze.md`
2. `v3_0C_claim_locator_contract.md`
3. `v3_0C_repair_loop_design.md`
4. `v3_0C_execution_plan_review.md`

## 6. 验收标准

Phase C P0 可视为完成，当且仅当：

1. claim 成为 Chat / Review 的正式审核单元。
2. citation 真源升级到 `quote_text + source_offset + source_chunk_id` 主线。
3. `supported / weakly_supported / unsupported` 成为正式 UI 状态。
4. unsupported claims 在 Chat / Review 中可见。
5. 单条 claim 可触发局部 repair / retry。
6. 实现没有新造平行 citation 系统或平行 claim 数据结构。

## 7. 风险

1. 若 canonical contract 不冻结，Chat 和 Review 会继续分叉。
2. 若 bbox 被当成 P0 硬前提，Phase C 会被 PDF 定位工程拖慢。
3. 若 verifier 仍停留在句子级 coverage，用户会误以为 claim 已被真正验证。
4. 若 unsupported claim 不可见，Phase C 会退化成“字段更多但可信度没提升”。
