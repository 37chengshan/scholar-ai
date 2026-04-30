# v3.0I Claim Truthfulness Spec

> 日期：2026-04-30  
> 状态：freeze  
> 目标：冻结 Phase I 首批 `claim-centered truthfulness` substrate 的对象、职责与返回契约。

## 1. 组件职责

1. `ClaimExtractor`
2. `ClaimLinker`
3. `ClaimVerifier`
4. `ClaimRepairer`
5. `TruthfulnessReportBuilder`

## 2. Support 语义冻结

支持等级固定为四档：

1. `supported`
2. `weakly_supported`
3. `partially_supported`
4. `unsupported`

第一版 baseline verifier 允许继续采用 lexical overlap，但禁止只返回通过/失败。

## 3. 返回契约

`truthfulness_report` 最小字段：

1. `totalClaims`
2. `supportedClaimCount`
3. `weaklySupportedClaimCount`
4. `partiallySupportedClaimCount`
5. `unsupportedClaimCount`
6. `unsupportedClaimRate`
7. `answerMode`
8. `results[]`

`results[]` 每条最小字段：

1. `claim_id`
2. `text`
3. `claim_type`
4. `support_level`
5. `support_score`
6. `evidence_ids[]`
7. `reason`

## 4. Repair Contract

`repair_claim` 首批输出必须复用同一 truthfulness 结构，并补：

1. `repairable`
2. `repair_hint`

## 5. 首批接入边界

1. `rag/chat`：返回 `task_family / execution_mode / truthfulness_required / truthfulness_summary / truthfulness_report`
2. `compare`：compare contract 增加 claim-level truthfulness summary
3. `review`：paragraph `claim_verification` 与 `truthfulness_summary` 均走统一 substrate
4. `Phase J`：消费 `truthfulness_report_summary` 与 route metadata，不要求本轮跑完整 benchmark
