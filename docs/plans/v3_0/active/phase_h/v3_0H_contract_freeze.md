# v3.0H Contract Freeze

> 日期：2026-04-30  
> 状态：freeze-draft  
> 上游：`docs/plans/v3_0/active/phase_h/v3_0H_provider_inventory.md`  
> 目的：冻结 `Phase H` 的 provider contract、runtime mode、trace 字段与 fallback honesty 口径。

## 1. 目标

本文件解决四件事：

1. 什么叫 `online-first` 的正式 contract
2. retrieval plane 与 generation plane 分别要暴露哪些字段
3. fallback / shim / lite 怎么记录
4. benchmark / Phase D / release gate 消费什么字段

## 2. 核心原则

1. 不允许只写“当前用了线上模型”。
2. 必须区分：
   - retrieval plane
   - generation plane
3. 必须区分：
   - online
   - local
   - shim
   - lite
4. 任一 run 如果发生 degraded condition，必须显式暴露，而不是静默成功。

## 3. Runtime Mode Freeze

## 3.1 顶层 mode

顶层 `runtime_mode` 冻结为：

1. `online`
   - retrieval plane 与 generation plane 都使用正式线上 provider
2. `local`
   - 至少一个 plane 使用本地正式模型实现
3. `shim`
   - 至少一个 plane 使用兼容或伪造 provider，如 deterministic shim
4. `lite`
   - 向量库或相关运行时进入 lite/degraded backend，例如 Milvus Lite
5. `mixed`
   - 不同 plane 使用不同 mode，且不属于纯 `online`

## 3.2 Plane-level mode

每个 plane 还必须独立记录：

1. `retrieval_plane_mode`
2. `generation_plane_mode`

取值同上：

1. `online`
2. `local`
3. `shim`
4. `lite`

## 4. Provider Identity Freeze

## 4.1 Retrieval Plane

必须显式记录：

1. `embedding_provider`
2. `embedding_model`
3. `embedding_variant`
4. `embedding_dimension`
5. `rerank_provider`
6. `rerank_model`
7. `vector_store_backend`
8. `vector_collection`
9. `vector_index_version`

## 4.2 Generation Plane

必须显式记录：

1. `generation_provider`
2. `generation_model`
3. `generation_variant`

## 4.3 当前冻结值

当前默认冻结值：

### Retrieval plane

1. `embedding_provider = qwen_online`
2. `embedding_model = qwen_flash | qwen_pro`
3. `rerank_provider = qwen_online`
4. `rerank_model = qwen_rerank`
5. `vector_store_backend = milvus`

### Generation plane

1. `generation_provider = glm_online`
2. `generation_model = glm-4.5-air`

## 5. Fallback Honesty Freeze

## 5.1 Fallback 事件分类

任一 run 中，以下事件必须独立记录：

1. `local_model_fallback`
2. `shim_provider_fallback`
3. `milvus_lite_fallback`
4. `rerank_bypass`
5. `generation_provider_fallback`

## 5.2 Fallback 严格规则

1. 若发生 `local_model_fallback`
   - 顶层 `runtime_mode` 不能再记为 `online`
2. 若发生 `shim_provider_fallback`
   - 顶层 `runtime_mode` 必须为 `shim` 或 `mixed`
3. 若发生 `milvus_lite_fallback`
   - 顶层 `runtime_mode` 必须为 `lite` 或 `mixed`
4. 若发生 `rerank_bypass`
   - 必须记录发生在哪个 query family / workflow step
5. 若发生任一 fallback
   - report 中必须出现 `degraded_conditions[]`

## 5.3 禁止事项

1. 不允许把 deterministic shim 记成 `online provider`
2. 不允许把 `Milvus Lite` 记成正常 `milvus`
3. 不允许 report 只写 `fallback_used = true` 而不说明具体 fallback 类型

## 6. Trace 字段冻结

## 6.1 Run-level trace

任一正式 run 至少要有以下字段：

| field | required | meaning |
|---|---|---|
| `run_id` | yes | 本次运行唯一 ID |
| `trace_id` | yes | 运行链路追踪 ID |
| `runtime_mode` | yes | 顶层 mode |
| `retrieval_plane_mode` | yes | retrieval plane mode |
| `generation_plane_mode` | yes | generation plane mode |
| `degraded_conditions` | yes | 所有退化条件列表 |
| `fallback_events` | yes | fallback 事件列表 |

## 6.2 Retrieval trace

任一 retrieval-heavy run 至少要有：

| field | required | meaning |
|---|---|---|
| `embedding_provider` | yes | query/document embedding provider |
| `embedding_model` | yes | flash/pro 具体模型 |
| `rerank_provider` | yes | rerank provider |
| `rerank_model` | yes | rerank model |
| `vector_store_backend` | yes | milvus / lite |
| `vector_collection` | yes | 使用的 collection |
| `query_family` | yes | 当前 query family |

## 6.3 Generation trace

任一 generation-heavy run 至少要有：

| field | required | meaning |
|---|---|---|
| `generation_provider` | yes | generation provider |
| `generation_model` | yes | 例如 glm-4.5-air |
| `generation_task_type` | yes | answer / review / repair |

## 7. Query Family Policy Freeze

以下是当前冻结的默认策略口径：

| query_family | embedding_model_policy | rerank | generation_model | notes |
|---|---|---|---|---|
| `fact` | qwen_flash | qwen_rerank | glm-4.5-air | 低成本默认 |
| `method` | qwen_flash | qwen_rerank | glm-4.5-air | 低成本默认 |
| `table` | qwen_flash | qwen_rerank | glm-4.5-air | 可后续 benchmark 复核 |
| `figure` | qwen_flash | qwen_rerank | glm-4.5-air | 可后续 benchmark 复核 |
| `numeric` | qwen_pro | qwen_rerank | glm-4.5-air | 高复杂度 |
| `compare` | qwen_pro | qwen_rerank | glm-4.5-air | 高价值 |
| `cross_paper` | qwen_pro | qwen_rerank | glm-4.5-air | 高价值 |
| `survey` | qwen_pro | qwen_rerank | glm-4.5-air | 高价值 |
| `related_work` | qwen_pro | qwen_rerank | glm-4.5-air | 高价值 |
| `conflicting_evidence` | qwen_pro | qwen_rerank | glm-4.5-air | 高复杂度 |
| `hard` | qwen_pro | qwen_rerank | glm-4.5-air | 高复杂度 |

## 8. 消费方约束

## 8.1 Phase D

Phase D 必须消费：

1. `runtime_mode`
2. `retrieval_plane_mode`
3. `generation_plane_mode`
4. `degraded_conditions`
5. `embedding_model`
6. `rerank_model`
7. `generation_model`

## 8.2 Phase J

Phase J comparative benchmark 必须消费：

1. 当前 baseline 的 per-plane model identity
2. candidate 与 baseline 的 mode parity
3. rerank 是否同口径开启
4. 是否发生 fallback

## 8.3 Release Gate

release gate 不允许：

1. 用 `mixed/shim/lite` 结果宣称正式 online baseline 成功
2. 用 fallback run 替换 baseline run

## 9. 后续依赖

本文件之后应补：

1. `v3_0H_runtime_validation_matrix.md`
2. 真实字段回填到验证产物和报告模板
