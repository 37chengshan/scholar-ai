# v3.0C Repair Loop Design

日期：2026-04-28
状态：design

## 1. 设计目标

- 以单条 claim 为 repair 单位。
- 只重跑必要链路（局部检索/重验证），避免整段重生成。
- repair 结果回写到 canonical contract。

## 2. Repair 输入

```json
{
  "run_id": "string",
  "claim_id": "string",
  "user_instruction": "optional string",
  "strategy": "retry_retrieval|retry_verification|replace_evidence"
}
```

## 3. Repair 流程

1. 定位 claim_id 对应 ClaimUnit。
2. 读取当前 supporting_evidence_ids 和上下文 query。
3. 按 strategy 执行：
   - retry_retrieval：扩大召回窗口，重新打分，生成新 anchor。
   - retry_verification：固定 evidence，重新判定 support_status。
   - replace_evidence：替换低质量 anchor 后重验。
4. 回写：
   - claims[].support_status/support_score
   - evidence_blocks[]（必要时增量更新）
   - claim_verification.results[]
5. 产出 repair report（before/after diff）。

## 4. 失败恢复

- 若 retrieval 失败：保留旧证据，状态不降级，记录 warning。
- 若 verification 失败：claim 标记 unsupported，repairable=true。
- 若回写失败：不覆盖旧 contract，返回 error_state=repair_write_failed。

## 5. UI 交互

- Chat/Review 每条 claim 提供 Repair 按钮。
- 运行中状态：repairing。
- 完成后显示状态变化：
  - unsupported -> weakly_supported
  - weakly_supported -> supported
  - unchanged（含原因）

## 6. 验收

1. 可对单 claim 发起 repair。
2. repair 不触发整段重生成。
3. 结果能在 Chat/Review 立即可见。
4. 无平行 repair 数据结构。
