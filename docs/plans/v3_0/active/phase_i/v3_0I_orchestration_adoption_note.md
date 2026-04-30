# v3.0I Orchestration Adoption Note

> 日期：2026-04-30  
> 状态：freeze  
> 目标：冻结 LangGraph、STORM-lite、Adaptive-RAG 在 ScholarAI academic kernel 中的正式层级归属与消费方式。

## 1. 结论

ScholarAI 只吸收编排模式，不把外部编排框架提升为领域真源。

正式层级归属：

1. `Academic Kernel`
   - `Paper / EvidenceCandidate / EvidenceBlock / AnswerClaim / CompareMatrix / ReviewRun`
2. `Orchestration Layer`
   - `LangGraph-style durable execution`
   - `STORM-lite outline planner`
   - `checkpoint / resume / HITL`
3. `Runtime Policy Layer`
   - `Adaptive-RAG complexity routing`
   - `cost-aware depth control`
4. `Benchmark Hooks`
   - `Phase J comparative gate`

## 2. 正式消费方式

1. `LangGraph`
   - 只吸收 durable execution、checkpoint、resume、HITL 模式
   - 不得替代 `ReviewRun`、`AnswerClaim`、`EvidenceBlock`
2. `STORM-lite`
   - 作为 `global_review` 主链的默认综述编排模式
   - 固定为 `outline -> section retrieval -> evidence-backed section synthesis -> validation`
   - 不直接引入重型多 agent 堆栈
3. `Adaptive-RAG`
   - 作为 runtime policy 进入 `retrieval_plane_policy.routing_policy`
   - 当前只控制 retrieval depth、top_k、global/local kernel 切换
   - 不允许让模型自行重写 taxonomy

## 3. 当前主链映射

1. `local_evidence`
   - local kernel
   - citation-first
   - verifier backend: `rarr_cove_scifact_lite`
2. `local_compare`
   - dual kernel
   - matrix-first
   - verifier backend: `rarr_cove_scifact_lite`
3. `global_review`
   - global kernel
   - `storm_lite`
   - adaptive depth enabled
   - verifier backend: `rarr_cove_scifact_lite`

## 4. Phase J 消费字段

所有主链编排都必须输出：

1. `task_family`
2. `execution_mode`
3. `truthfulness_report_summary`
4. `retrieval_plane_policy`
5. `degraded_conditions`

## 5. 升级门槛

以下能力只有通过 `Phase J comparative gate` 才能升级：

1. `LangGraph` 从 pattern 吸收到真实 runtime dependency
2. `STORM-lite` 从 review 扩展到 long-form compare/survey 之外的任务
3. `Adaptive-RAG` 从 depth routing 扩展到 provider-level policy