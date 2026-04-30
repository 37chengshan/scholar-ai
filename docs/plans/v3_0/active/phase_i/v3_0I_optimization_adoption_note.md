# v3.0I Optimization Adoption Note

> 日期：2026-04-30  
> 状态：freeze  
> 目标：冻结 DSPy、RARR/CoVe、SciFact-style verifier、RAPTOR 在优化层与实验层中的位置。

## 1. 结论

ScholarAI 的优化层只负责“调优已有 contract”，不负责“重定义 academic kernel”。

正式归属：

1. `DSPy`
   - optimization layer
   - 用于 synthesis prompt/program tuning、route threshold tuning、review critique tuning
2. `RARR/CoVe`
   - truthfulness optimization layer
   - 用于 claim re-check、citation repair、unsupported surfacing
3. `SciFact-style verifier`
   - truthfulness backend target
   - 当前先以 `rarr_cove_scifact_lite` 多信号后端实现第一版契约
4. `RAPTOR`
   - retrieval enhancement candidate
   - 先作为 hierarchical retrieval 主线候选，不直接替代 local kernel

## 2. 当前已落位置

1. verifier backend
   - 当前默认后端：`rarr_cove_scifact_lite`
   - 已进入 chat / compare / review 共用 substrate
2. review 主链
   - `STORM-lite + hierarchical retrieval hints`
3. runtime policy
   - `Adaptive-RAG` 当前落在 `retrieval_plane_policy.routing_policy`

## 3. 必须通过的比较门

任何优化路线进入主线前，必须满足：

1. `unsupported_claim_rate` 不回退
2. `citation_coverage` 不下降
3. `degraded_rate` 可控
4. `latency` 与 `cost` 回归在 `Phase J comparative gate` 允许范围内

## 4. 近期 adoption order

1. `rarr_cove_scifact_lite verifier`
2. `STORM-lite global review`
3. `RAPTOR-style hierarchical retrieval`
4. `DSPy-style tuning on review synthesis and route thresholds`
5. `GraphRAG / OpenScholar / IRCoT` 继续停留在实验 backlog