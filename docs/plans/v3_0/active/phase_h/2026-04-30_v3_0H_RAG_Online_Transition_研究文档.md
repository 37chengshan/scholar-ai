---
标题：ScholarAI v3.0-H RAG 全面转向线上研究文档
日期：2026-04-30
状态：research
范围：线上 provider 收口、RAG 主链去本地默认依赖、online-first contract、fallback 与验证边界
前提：本文件基于当前仓库真实代码状态书写，明确承认主链仍存在本地模型与兼容 shim；目标是定义收口方向，而不是假设线上化已完成
---

# 1. 研究目标

本文件定义 ScholarAI `v3.0-H: RAG Online-first Transition` 的研究方案。

它回答的核心问题是：

```txt
怎样把当前“部分线上、部分本地、部分兼容 shim”的 RAG 主链，
收敛成线上优先、真实可验证、可比较、可回滚的生产架构。
```

本文件只定义现状盘点、问题边界、目标结构、迁移原则、fallback 规则和验证框架；不直接展开到逐文件代码修改清单或供应商最终拍板。

## 1.1 当前已知线上模型栈假设

基于当前最新产品约束，本阶段默认采用以下线上模型栈假设：

1. 检索侧在线模型主线：
   - `Qwen flash/pro` 系列承担主检索侧在线模型能力
2. rerank 主线：
   - 使用 `Qwen rerank` 模型
3. 生成侧 LLM：
   - 暂时使用 `glm-4.5-air`

这意味着 `Phase H` 不是“所有模型统一一家”，而是：

```txt
retrieval / rerank plane 先按 Qwen 在线栈冻结，
generation plane 暂时保留 glm-4.5-air，
但两者都必须进入统一 provider contract 和 runtime trace。
```

# 2. 执行摘要

当前仓库的真实情况，不是“完全本地”，也不是“已经全面线上”。

而是三种状态并存：

1. `generation` 已有明确线上入口
   - `apps/api/app/config.py`
   - `LLM_API_BASE = https://open.bigmodel.cn/api/paas/v4`
2. `主检索 / 主索引 / review retrieval` 仍存在大量本地 Qwen 依赖
   - `apps/api/app/core/qwen3vl_service.py`
   - `apps/api/app/workers/storage_manager.py`
   - `apps/api/app/services/review_draft_service.py`
   - `apps/api/app/workers/pdf_coordinator.py`
3. `部分 v3 / compare / benchmark 路径` 已引入线上或伪线上 provider 入口，但尚未成为统一真源
   - `apps/api/app/rag_v3/main_path_service.py`
   - `apps/api/app/services/compare_service.py`
   - `apps/api/app/core/model_gateway.py`

这说明 `Phase H` 的正确方向不是一句“把模型切线上”，而是要系统回答：

```txt
1. 什么算生产默认路径
2. 哪些本地依赖必须从主链移除
3. 哪些 fallback 可以保留，但不能再伪装成默认主链
4. 怎样让线上化后的行为可验证、可 benchmark、可回滚
```

因此，`v3.0-H` 的定位应为：

```txt
在保留 Milvus 主线向量库的前提下，
把 ScholarAI 的 generation / embedding / reranker / retrieval wiring
统一进线上优先、可配置、可观测的 provider contract，
并终止本地实验模型作为生产默认真源。
```

这里需要额外强调：

1. `检索栈` 与 `生成栈` 不要求同一家模型供应商。
2. 但 `provider truth`、`runtime trace`、`fallback honesty` 必须统一。

# 3. 当前基线盘点

## 3.1 当前仓库里的线上信号

当前仓库并非没有线上模型基础。

明确存在的线上信号包括：

1. 文本生成主入口配置为线上 API
   - `apps/api/app/config.py`
   - `LLM_MODEL`
   - `LLM_API_BASE`
2. compare 路径已尝试按 provider 方式接 embedding
   - `apps/api/app/services/compare_service.py`
3. `rag_v3` 主路径也已经引入 `model_gateway`
   - `apps/api/app/rag_v3/main_path_service.py`

结论：

1. 仓库不是从零开始设计 online-first。
2. 但线上化还只是局部成立，不是系统性收口。

## 3.2 当前仓库里的本地默认依赖

当前主链仍有多类本地默认依赖：

1. 本地 embedding 模型路径
   - `apps/api/app/config.py`
   - `QWEN3VL_EMBEDDING_MODEL_PATH`
2. 本地 Qwen singleton 服务
   - `apps/api/app/core/qwen3vl_service.py`
   - `get_qwen3vl_service()`
3. 主索引路径直接调用本地 embedding
   - `apps/api/app/workers/storage_manager.py`
   - `self.qwen3vl_service.encode_text(...)`
4. review retrieval 仍直连本地 embedding
   - `apps/api/app/services/review_draft_service.py`
5. PDF / image / table / extraction 链路中仍有本地 Qwen 入口
   - `apps/api/app/workers/extraction_pipeline.py`
   - `apps/api/app/workers/pdf_worker.py`
   - `apps/api/app/core/image_extractor.py`
   - `apps/api/app/core/table_extractor.py`

结论：

```txt
当前真正阻碍线上化的，不只是一个 config 开关，
而是“多处业务路径仍把本地 Qwen service 当成隐式默认真源”。
```

## 3.3 当前仓库里的兼容 shim / 假线上问题

最危险的问题不是本地模型本身，而是“看起来像线上，实际上只是兼容壳”。

当前显著例子：

1. `apps/api/app/core/model_gateway.py`
   - `create_embedding_provider(...)` 当前返回的是 `_DeterministicEmbeddingProvider`
   - 它是本地 deterministic shim，不是真实远程 provider
2. `apps/api/app/rag_v3/main_path_service.py`
   - 名义上通过 provider 获取 embedding
   - 实际消费的是 `model_gateway` 兼容实现

这意味着：

1. 某些路径在代码形态上已经“像 provider 架构”
2. 但行为层还不是“真实线上 provider 架构”

对 `Phase H` 来说，这必须被明确分类，不能混为“已完成线上化”。

## 3.4 当前向量库事实基线

当前向量库主线仍是 Milvus：

1. `apps/api/app/config.py`
   - `VECTOR_STORE_BACKEND = "milvus"`
2. `apps/api/app/core/vector_store_repository.py`
3. `apps/api/app/core/milvus_service.py`

同时，当前仓库还存在 `Milvus Lite` fallback 逻辑：

1. `apps/api/app/core/milvus_service.py`
   - 明确包含 “switched to Milvus Lite” 分支

结论：

1. `Phase H` 不改变 Milvus 主线地位。
2. 但要把“Milvus 主线”和“本地模型默认路径”拆开处理。
3. `Milvus Lite` 最多只能作为开发/降级 fallback，不能继续污染生产默认验证口径。

# 4. 为什么必须单独成立 Phase H

## 4.1 线上 generation 不等于线上 RAG

如果只有 answer generation 走线上，而 embedding / reranker / retrieval 仍主要依赖本地实验模型，那么：

1. 真实主链结果仍受开发机状态影响。
2. benchmark 和 real-world validation 的可复现性会被削弱。
3. 成本、延迟、失败率无法按统一 provider 口径观测。

## 4.2 “部分 provider 化”不等于“生产默认路径收口”

当前有些路径已经用了 `factory` 或 `gateway`，但这不代表问题已解决。

因为：

1. factory 默认项仍可能指向本地模型实现
2. gateway 当前可能只是 deterministic shim
3. 业务层仍直接 import `get_qwen3vl_service()`

因此，`Phase H` 的目标不是“让代码看起来更抽象”，而是：

```txt
让生产默认路径真的只依赖线上 contract，
而不是只把本地依赖藏到更深一层。
```

## 4.3 Phase I / Phase J 都依赖 H

如果没有 `Phase H`：

1. `Phase I` 的框架研究会建立在不稳定的 runtime 真源上
2. `Phase J` 的 benchmark 会混合“本地实验模型结果”和“线上生产结果”
3. 后续任何“更强 / 更稳 / 更省”的比较都无法同口径解释

所以：

```txt
Phase H 是 v3.0 后续研究创新与 benchmark 体系成立的运行基线。
```

# 5. Phase H 的正式目标

`Phase H` 需要同时满足以下六个目标：

1. `统一生产默认真源`
   - 明确线上 provider 是默认主链，终止本地实验模型的默认地位
2. `统一 provider contract`
   - generation / embedding / reranker / retrieval wiring 使用同一套线上 contract 思维
3. `统一 fallback 语义`
   - 本地 fallback、lite fallback、deterministic shim 必须显式标识
4. `统一验证口径`
   - benchmark、Phase D、release gate 必须知道当前 run 用的是哪条模型链
5. `统一成本与延迟观测`
   - 线上 provider 的 latency、cost、error state 进入统一记录
6. `统一回滚路径`
   - provider 切换失败时有明确回退策略，但不把回退伪装成正常成功

# 6. 目标架构方向

## 6.1 Online-first provider stack

建议 Phase H 之后，默认生产路径在概念上收敛为：

```txt
user request
-> orchestrator / workflow
-> provider contract
-> online embedding / online reranker / online generation
-> Milvus retrieval
-> evidence / answer / review outputs
-> trace + cost + error_state
```

关键点：

1. Milvus 继续负责向量检索与索引存储
2. 模型调用统一通过 provider contract 走线上
3. provider identity、fallback identity、runtime mode 都必须可追踪
4. `retrieval plane` 与 `generation plane` 必须显式分层，不能混写成一个“大模型栈”

更具体地说，当前推荐表达应为：

```txt
retrieval plane:
Qwen flash/pro family + Qwen rerank + Milvus

generation plane:
glm-4.5-air
```

这两个 plane 可以暂时不同源，但不能共用模糊配置。

## 6.2 本地能力的新定位

本地模型与兼容 shim 不能再担任生产默认路径，只能退到以下角色：

1. 开发环境应急 fallback
2. benchmark 对照实验
3. 无网条件下的显式测试模式

它们必须满足：

1. 被显式配置启用
2. 被显式记录到 artifact / trace / report
3. 不参与默认 production-ready 结论

## 6.3 retrieval contract 的要求

`Phase H` 不要求一开始就替换整个 retrieval 框架，但要求：

1. query embedding 来源可明确切换到线上 provider
2. document embedding / index build 来源可明确切换到线上 provider
3. reranker 来源可明确切换到线上 provider
4. collection dimension、provider model、index version 三者关系可被记录

否则线上化只是“生成链线上”，不是“RAG 主链线上”。

额外优化点：

1. `query embedding`、`document embedding`、`rerank` 三者必须分别记录模型名，不允许只写一个“Qwen online”总标签。
2. `generation` 必须单独记录 `glm-4.5-air`，否则后续 benchmark 会误把生成栈和检索栈混成一条链。

# 7. 推荐的依赖分层

建议把线上化问题拆成四层，而不是一次性大替换：

## 7.1 Layer 1：Provider Identity Freeze

先回答：

1. 默认 embedding provider 是谁
2. 默认 reranker provider 是谁
3. 默认 generation provider 是谁
4. provider model 名称、版本、维度、限流方式如何记录

## 7.2 Layer 2：Business Entry Unification

再回答：

1. 哪些业务入口仍直连 `get_qwen3vl_service()`
2. 哪些入口改为统一 provider/factory/gateway
3. 哪些路径必须先删本地默认导入，再谈 provider 切换

## 7.3 Layer 3：Artifact and Trace Honesty

再回答：

1. 当前 run 是 online / local / shim / lite 哪种模式
2. 是否发生 fallback
3. 是否允许该 fallback 通过正式 gate

## 7.4 Layer 4：Benchmark and Release Consumption

最后回答：

1. benchmark 如何区分线上基线与候选链路
2. Phase D 如何记录 degraded condition
3. release gate 如何拒绝“伪线上成功”

# 8. Phase H 不做什么

1. 不在本阶段里直接做 `Phase I` 的框架创新选型。
2. 不把 Qdrant 或其他向量库切换纳入本阶段主目标。
3. 不默认把所有本地能力彻底删除。
4. 不把 deterministic shim 伪装成真实线上 provider。
5. 不允许通过修改文案或测试绕过“实际上还在跑本地链路”的事实。

# 9. 推荐的验证维度

## 9.1 Runtime Truth

必须验证：

1. 当前链路是否真的发起线上请求
2. 是否仍在消费本地权重 / 本地脚本
3. trace 中是否能识别 provider 身份

## 9.2 Functional Continuity

必须验证：

1. Search / Import / Chat / Review 在线上模型条件下仍可贯通
2. embedding 切换后不会破坏 Milvus collection 兼容性
3. reranker 切换后 review / compare 证据排序语义仍可解释

## 9.3 Cost and Latency

必须验证：

1. embedding latency
2. reranker latency
3. generation latency
4. per-run / per-query cost
5. fallback 触发率

## 9.4 Honesty

必须验证：

1. 若发生 local fallback，系统是否显式暴露
2. 若发生 Milvus Lite fallback，报告是否显式标注
3. benchmark / validation 报告是否准确声明 runtime mode

# 10. 研究结论

基于当前仓库真实状态，`Phase H` 的研究结论是：

1. ScholarAI 已具备线上 generation 基础，但未完成 RAG 主链全面线上化。
2. 当前最大的阻力不是缺少“provider 抽象”概念，而是业务入口仍广泛直连本地 Qwen service。
3. 当前 `model_gateway` 兼容 shim 不能被当成正式线上 provider 真源。
4. `Phase H` 必须先解决默认路径、fallback 语义和验证口径，再谈后续框架创新。
5. Milvus 可以继续作为主线向量库，但本地模型默认路径必须退出生产真源。

一句话结论：

```txt
Phase H 的本质不是“把几个模型名改成线上”，
而是把 ScholarAI 的 RAG 主链从实验态收口成真实 online-first runtime。
```

# 11. 后续文档

本文件之后，建议至少补齐：

1. `docs/plans/v3_0/active/phase_h/15_v3_0H_execution_plan.md`
2. provider inventory / contract freeze
3. online runtime validation matrix
4. fallback register extension for online/local/shim/lite modes
