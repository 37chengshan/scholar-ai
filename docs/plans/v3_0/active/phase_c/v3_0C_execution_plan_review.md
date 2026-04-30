# v3.0C Execution Plan Review

日期：2026-04-28
状态：review
评审对象：docs/plans/v3_0/active/phase_c/09_v3_0C_execution_plan.md

## 1. 结论

执行计划方向正确，已满足 claim-first 与 evidence-anchor-first 的主线要求。

## 2. 覆盖性检查

- WP0 合理：先冻结 contract，避免前后端分叉。
- WP1 合理：先升级 anchor，再谈 verifier 强化。
- WP2 合理：统一 Chat/Review claim 单元，避免并行模型。
- WP3 合理：把 verifier 纳入正式主链，而非评分装饰。
- WP4 合理：把 unsupported 显式暴露到 UI。
- WP5 合理：单 claim repair 形成可操作闭环。
- WP6 合理：确保 Chat/Review/Read 进入同一主工作流。

## 3. 建议补充的执行检查点

### 3.1 Contract 检查点（WP0 后）

- packages/types 与 apps/api schema 的状态枚举一致。
- partially_supported 已统一兼容映射到 weakly_supported（写路径）。

### 3.2 Anchor 检查点（WP1 后）

- evidence_blocks 至少包含 quote_text/source_offset/source_chunk_id。
- citation_jump_url 在三端可点击。

### 3.3 Verifier 检查点（WP3 后）

- claim-level support 与 sentence-level coverage 分离展示。
- unsupportedClaimRate 与 claim_verification.results 同步。

### 3.4 UI 检查点（WP4/WP6 后）

- Chat 与 Review 的 badge 文案、颜色、语义一致。
- Read 页可回跳到 quote anchor 附近（最小为 chunk 定位）。

### 3.5 Repair 检查点（WP5 后）

- 单 claim repair 可重放并可回写。
- repair 失败不会污染旧 contract。

## 4. 风险复核

1. 若继续保留多套 status 命名，后续会持续出现映射漏洞。
2. 若 quote/offset 字段长期缺失，Phase C 会退化成“有 badge 无证据定位”。
3. 若 repair 做成整段重跑，将显著提高延迟与成本，且可解释性变差。

## 5. 建议验收用例

1. Chat 输出含 3 条 claims，其中 1 条 unsupported，UI 有明显标识。
2. Review Draft 同一语义下 status 与 Chat 一致。
3. 点击 citation_jump_url 可跳到 Read 落点。
4. 对 unsupported claim 执行 repair 后状态发生可解释变化。
