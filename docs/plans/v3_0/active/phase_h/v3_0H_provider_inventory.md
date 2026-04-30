# v3.0H Provider Inventory

> 日期：2026-04-30  
> 状态：freeze-draft  
> 上游：`docs/plans/v3_0/active/phase_h/2026-04-30_v3_0H_RAG_Online_Transition_研究文档.md`  
> 目的：冻结 `Phase H` 的 provider inventory、plane 划分、默认覆盖范围与后续 benchmark 待裁决项。

## 1. 冻结结论

当前按产品约束，先冻结为双平面模型栈：

```txt
retrieval plane
- embedding: Qwen flash / Qwen pro（按场景分层）
- rerank: Qwen rerank（先覆盖所有正式 retrieval 主链）
- vector store: Milvus

generation plane
- llm: glm-4.5-air（暂时主线）
```

当前不在 `Phase H` 里提前决定：

1. `Qwen flash` 或 `Qwen pro` 哪个成为最终唯一默认 embedding 基线
2. `Qwen rerank` 是否应长期覆盖全部 retrieval 场景
3. `glm-4.5-air` 是否继续保留为长期 generation 主线

这些都交由后续 benchmark 裁决。

## 2. Plane 原则

## 2.1 Retrieval Plane

负责：

1. query embedding
2. document embedding / index build
3. retrieval rerank
4. retrieval trace

不负责：

1. 最终自然语言生成
2. review prose polishing
3. answer rewriting

## 2.2 Generation Plane

负责：

1. answer synthesis
2. review paragraph synthesis
3. repair / rewrite text generation
4. final natural language output

不负责：

1. 向量生成
2. rerank
3. retrieval candidate scoring

## 3. 当前默认策略冻结

## 3.1 Embedding 策略

当前先按场景分层：

1. `Qwen flash`
   - 默认低成本主链
   - 适合：
     - Search / Chat 普通 query
     - Import 后常规问答
     - 单篇论文局部问题
2. `Qwen pro`
   - 高价值 / 高复杂度主链
   - 适合：
     - review generation
     - compare
     - conflicting evidence
     - related work / survey / hard query

冻结规则：

1. 当前不强行二选一。
2. benchmark 前允许按 query family / workflow path 分层。
3. benchmark 后再决定是否统一到单一 embedding baseline。

## 3.2 Rerank 策略

当前冻结为：

1. `Qwen rerank` 先覆盖所有正式 retrieval 主链

覆盖范围包括：

1. Search / Chat 正式 retrieval 主链
2. Compare
3. Review Draft
4. High-value KB query

暂不排除后续 benchmark 证明某些轻量路径不必默认 rerank，但在 `Phase H` 冻结期内先全覆盖，以便口径一致。

## 3.3 Generation 策略

当前冻结为：

1. `glm-4.5-air` 暂时作为 generation plane 主线

适用范围：

1. chat answer synthesis
2. review draft prose generation
3. repair / rewrite generation

约束：

1. 不能侵入 retrieval plane
2. 不能写死到 academic kernel
3. 后续可替换，但替换不应要求重写 evidence / claim / compare / review kernel

## 4. Provider Inventory 表

| scope | current_state | target_state | plane | default_model_policy | benchmark_decision_needed | notes |
|---|---|---|---|---|---|---|
| query embedding | mixed local qwen + shim + partial online | online-only | retrieval | flash default, pro for hard paths | yes | benchmark 后决定是否统一 |
| document embedding | local qwen dominant | online-only | retrieval | flash for normal ingest, pro for high-value ingest | yes | 必须记录 collection dimension |
| rerank | mixed / partial / some bypass | online-only | retrieval | Qwen rerank all formal retrieval paths | yes | 后续 benchmark 决定是否对轻路径降级 |
| compare retrieval | pseudo-online shim path | true online | retrieval | pro + rerank preferred | yes | compare 对证据质量更敏感 |
| review retrieval | local-heavy / mixed | true online | retrieval | pro + rerank preferred | yes | review 是高价值复杂任务 |
| answer generation | online | online | generation | glm-4.5-air | yes | 暂为主线，后续可替换 |
| review prose generation | online / mixed assumptions | online | generation | glm-4.5-air | yes | 必须与 retrieval plane 分离记录 |
| claim repair rewrite | mixed | online | generation | glm-4.5-air | yes | repair 结果必须保留 claim trace |

## 5. Query Family 到模型策略映射

| query_family / workflow | embedding | rerank | generation | status |
|---|---|---|---|---|
| fact | Qwen flash | Qwen rerank | glm-4.5-air | provisional |
| method | Qwen flash | Qwen rerank | glm-4.5-air | provisional |
| table | Qwen flash | Qwen rerank | glm-4.5-air | provisional |
| figure | Qwen flash | Qwen rerank | glm-4.5-air | provisional |
| numeric | Qwen pro | Qwen rerank | glm-4.5-air | provisional |
| compare | Qwen pro | Qwen rerank | glm-4.5-air | provisional |
| cross_paper | Qwen pro | Qwen rerank | glm-4.5-air | provisional |
| survey / related_work | Qwen pro | Qwen rerank | glm-4.5-air | provisional |
| conflicting_evidence | Qwen pro | Qwen rerank | glm-4.5-air | provisional |
| review_draft | Qwen pro | Qwen rerank | glm-4.5-air | provisional |

## 6. 显式禁止事项

1. 不允许再把 `local qwen singleton` 当作默认正式主链。
2. 不允许把 `model_gateway` deterministic shim 记成 online provider。
3. 不允许在 report 里只写 “online model” 而不写具体是 `Qwen flash`、`Qwen pro`、`Qwen rerank`、`glm-4.5-air`。
4. 不允许让 generation plane 的切换影响 retrieval plane 的 truth 口径。

## 7. 待 benchmark 裁决项

以下项在 `Phase H` 不拍板，统一交由 `Phase J`：

1. `Qwen flash` 是否足以覆盖大多数普通 retrieval query
2. `Qwen pro` 是否值得长期作为高复杂度默认
3. `Qwen rerank` 是否值得全链路默认开启
4. `glm-4.5-air` 是否继续作为 generation 主线
5. retrieval plane 是否需要按任务族分成更细的 policy bucket

## 8. 后续依赖

本文件之后，至少要补：

1. `v3_0H_contract_freeze.md`
2. `v3_0H_runtime_validation_matrix.md`
3. `v3_0I_framework_decision_matrix.md`
