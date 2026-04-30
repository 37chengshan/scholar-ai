# v3.0C Kickoff Freeze

日期：2026-04-28
状态：freeze
范围：Phase C（Span-level Citation + Claim Verification）
上游：
- docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md
- docs/plans/v3_0/active/phase_c/09_v3_0C_execution_plan.md
- docs/plans/v3_0/active/phase_c/2026-04-28_v3_0C_Span_Citation_Claim_Verification_研究文档.md

## 1. 冻结目标

Phase C 只做 claim-first 可信引用主链，不新造平行结构。

主链冻结为：

retrieval -> evidence anchor normalization -> claim segmentation -> claim-to-evidence linking -> verification -> unsupported surfacing -> repair -> answer/review 回写

## 2. Freeze-条款

### Freeze-01：ClaimUnit 是唯一审核单元

- Chat 与 Review 都必须输出 claims[]。
- claim 必须可稳定枚举，并可回链到回答片段或段落上下文。

### Freeze-02：EvidenceAnchor 统一以 quote+offset+chunk 为主

- P0 必须字段：quote_text、source_offset_start、source_offset_end、source_chunk_id。
- page_num / section_path / citation_jump_url 为落点与可读性字段，不能替代 quote+offset。
- bbox 仅为增强字段（P1）。

### Freeze-03：Verification 语义统一

- 允许值固定：supported / weakly_supported / unsupported。
- 不允许 sentence-level coverage 直接冒充 claim-level support。

### Freeze-04：Unsupported 必须可见

- unsupported/weakly_supported 不能只在日志或 trace。
- Chat/Review UI 必须出现 badge 或 warning。

### Freeze-05：Repair 入口按单 claim

- repair 输入单位是 claim_id。
- repair 不新造独立模型，回写 canonical contract。

### Freeze-06：不新增第二套 citation/claim 结构

- 前后端共享同一契约。
- 历史字段可兼容，但新代码统一写入 canonical 字段。

## 3. Canonical 命名冻结

- claim status：supported | weakly_supported | unsupported
- evidence anchor：quote_text + source_offset_start + source_offset_end + source_chunk_id
- jump 字段：citation_jump_url

## 4. 执行顺序冻结

1. WP0 Canonical Contract Freeze
2. WP1 Evidence Anchor Upgrade
3. WP2 Claim Segmentation Unification
4. WP3 Verifier Hardening
5. WP4 Unsupported Surfacing
6. WP5 Claim Repair Loop
7. WP6 Chat/Review/Read 主链接入

## 5. 风险冻结

- 禁止把 bbox 作为 P0 阻塞项。
- 禁止仅依赖 page_num 作为证据定位。
- 禁止在 Review 单独维护一套 claim model。

## 6. 验收闸门

通过条件：

1. Chat/Review 都能展示 claim 列表及其 support 状态。
2. 每条 claim 可追到 evidence anchor（含 quote+offset+chunk）。
3. unsupported 在 UI 可见。
4. 单 claim repair 可触发，并回写主结构。
