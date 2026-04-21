# Milvus 继续演进的文件级改造清单 + Qdrant 实验分支实施顺序

## 0. 前提

已完成 PR #41：

- **统一 runtime 主链路**
- **收口 Notes ownership 边界**
- **分离 Chat / Read / Notes 对系统摘要与用户笔记的职责**

这一步的含义不是“继续重构页面”，而是：

> **后续检索引擎演进，默认不再返工 Chat / Read / Notes 的 ownership 边界。**

PR #41 已明确影响范围包括：

- `apps/api/app/api/notes.py`
- `apps/api/app/services/reading_notes_service.py`
- `apps/api/app/workers/notes_worker.py`
- `apps/web/src/app/pages/Chat.tsx`
- `apps/web/src/app/pages/Notes.tsx`
- `apps/web/src/app/pages/Read.tsx`
- `apps/web/src/features/notes/ownership.ts`

因此下一阶段要遵守一个硬规则：

> **检索引擎演进优先落在 retrieval / provider / config / benchmark / adapter 层，不再把页面层重新拉回到职责重构。**

---

## 1. 本阶段目标

本阶段不做“再一次 runtime 重构”，而是做两件事：

### 主线
**继续使用 Milvus，完成检索工程化升级**

### 支线
**开 Qdrant 实验分支，按同一 benchmark 做对比验证**

一句话：

> **主线稳住，旁路验证。**

---

## 2. 这批改造不要再优先碰的文件

除非为了适配统一 retrieval contract，否则下列文件本阶段不应再成为主战场：

### 前端页面壳层
- `apps/web/src/app/pages/Chat.tsx`
- `apps/web/src/app/pages/Notes.tsx`
- `apps/web/src/app/pages/Read.tsx`

### Notes ownership 边界
- `apps/web/src/features/notes/ownership.ts`
- `apps/api/app/api/notes.py`
- `apps/api/app/services/reading_notes_service.py`
- `apps/api/app/workers/notes_worker.py`

### 原因
这些文件刚在 PR #41 收过口。  
当前更大的收益，不来自再次调整 ownership，而来自：

- embedding / reranker provider 对齐
- retrieval contract 稳定
- vector store 抽象
- benchmark
- adapter 验证

---

## 3. Milvus 主线继续演进：文件级改造清单

---

## 3.1 第一批：先把模型栈对齐

### 目标
把当前实际检索链从：

- `Qwen3-VL-Embedding-2B`
- `BGE-Reranker-large`

推进到你希望的基线：

- `Qwen3-VL-Embedding-2B`
- `Qwen3-VL-Reranker-2B`

并为后续 `9B` 留出切换位。

### 必改文件

#### 1）`apps/api/app/config.py`
**改造目标：**
- 把 embedding / reranker 变成真正可切换配置
- 支持 `2B / 9B`
- 支持 provider 名称，而不是只有模型路径和维度

**建议新增配置：**
- `EMBEDDING_PROVIDER=qwen3vl`
- `RERANKER_PROVIDER=qwen3vl`
- `EMBEDDING_VARIANT=2b|9b`
- `RERANKER_VARIANT=2b|9b`
- `VECTOR_STORE_BACKEND=milvus|qdrant`
- `RETRIEVAL_BENCH_PROFILE=dev|full`

---

#### 2）`apps/api/app/core/qwen3vl_service.py`
**改造目标：**
- 保持它作为默认 embedding provider
- 抽出统一 provider 接口，不让上层直接绑定具体实现
- 把 2B / 9B 切换统一放到 provider 层

**建议动作：**
- 当前文件保留为 `Qwen3VLEmbeddingProvider` 实现
- 不让 `MultimodalSearchService` 直接依赖它的具体类名
- 增加 provider factory

---

#### 3）`apps/api/app/core/reranker_service.py`
**改造目标：**
- 从 `BGE-Reranker-large` 切到 `Qwen3-VL-Reranker-2B`
- 保留 BGE 作为 fallback/对照组，而不是直接删光

**建议动作：**
- 不要在这个文件里继续硬编码 `BAAI/bge-reranker-large`
- 先改成统一 `RerankerProvider`
- 提供：
  - `Qwen3VLRerankerProvider`
  - `BGERerankerProvider`
- 用配置切换默认实现

### 建议新增文件
- `apps/api/app/core/providers/embedding_provider.py`
- `apps/api/app/core/providers/reranker_provider.py`
- `apps/api/app/core/providers/provider_factory.py`

### 第一批退出条件
- 不改动页面层
- provider 层完成统一
- 2B/9B 可配置
- reranker 不再和 BGE 强绑定

---

## 3.2 第二批：把 Milvus 从“直连实现”提升成“可替换后端”

### 目标
把当前 `MilvusService` 从“直接被搜索服务使用”改成“向量后端实现之一”。

### 必改文件

#### 4）`apps/api/app/core/milvus_service.py`
**改造目标：**
- 继续保留现有逻辑
- 但从“唯一实现”改成“Milvus adapter”
- 把检索、插入、删除、过滤表达式构建，收束到统一接口之下

**建议动作：**
- 不直接暴露 Milvus 细节给 `MultimodalSearchService`
- 提供标准方法：
  - `search()`
  - `insert_batch()`
  - `delete_by_paper()`
  - `ensure_collections()`
  - `healthcheck()`

---

#### 5）`apps/api/app/core/multimodal_search_service.py`
**改造目标：**
- 变成 retrieval orchestration 层
- 不直接绑死 Milvus
- 只依赖 `VectorStoreRepository`

**建议动作：**
- 保留：
  - query planning
  - intent detection
  - metadata filter compile
  - fusion
  - rerank
- 拆掉：
  - 对 `MilvusService` 的直接耦合
- 改为：
  - `vector_store.search(...)`

---

#### 6）`apps/api/app/models/retrieval.py`
**改造目标：**
- 让 `RetrievedChunk / CitationSource / SearchConstraints` 成为真正跨引擎的 retrieval contract
- 不再显式写“来自 Milvus Raw Hit”的思维

**建议动作：**
- 保留当前 unified schema
- 新增：
  - `backend: milvus|qdrant`
  - `vector_score`
  - `sparse_score`
  - `hybrid_score`
  - `reranker_score`
  - `retrieval_trace_id`

这样后面做 benchmark 和 A/B 才能追踪。

---

### 建议新增文件
- `apps/api/app/core/vector_store_repository.py`
- `apps/api/app/core/vector_store_types.py`

### 第二批退出条件
- `MultimodalSearchService` 不再直连 Milvus
- retrieval contract 跨后端可复用
- 现有功能不退化

---

## 3.3 第三批：把 hybrid retrieval 做正式

### 目标
把当前“轻量 BM25-style scorer”升级成可观测、可比较、可调参的 hybrid pipeline。

### 必改文件

#### 7）`apps/api/app/core/bm25_service.py`
**改造目标：**
- 不再只是“轻量补丁 scorer”
- 明确成为 sparse scoring module

**建议动作：**
- 输出统一 sparse score
- 支持 batch 计算
- 保留当前轻量实现，但把参数放到配置中
- 增加 debug 输出，便于 benchmark 记录

---

#### 8）`apps/api/app/core/multimodal_search_service.py`
**改造目标：**
- 显式记录：
  - `vector_score`
  - `sparse_score`
  - `hybrid_score`
  - `reranker_score`
- 将 fusion 和 rerank 变成标准步骤

### 建议新增文件
- `apps/api/app/core/retrieval_scoring.py`
- `apps/api/app/core/retrieval_trace.py`

### 第三批退出条件
- 搜索结果带全链路得分
- hybrid 权重可配置
- benchmark 可复现

---

## 3.4 第四批：补 benchmark 和验证层

### 目标
在不迁移主线的前提下，先证明 Milvus 当前上限和短板。

### 优先改的文件

#### 9）已有脚本优先接管
优先检查并继续扩展：

- `scripts/eval_retrieval.py`
- `scripts/evals/run_rag_eval.py`

#### 10）测试与集成验证
建议新增或补齐：

- `apps/api/tests/integration/test_retrieval_backend_milvus.py`
- `apps/api/tests/integration/test_retrieval_scoring_pipeline.py`
- `apps/api/tests/integration/test_multimodal_retrieval_benchmark.py`

### benchmark 至少覆盖
- 1万 / 10万 / 100万 chunk
- text / image / table / mixed
- topk=20 / 50 / 100
- dense only / dense+sparse / dense+sparse+rerank
- 2B vs 9B

### 第四批退出条件
拿到真实对比数据，而不是主观判断。

---

## 3.5 第五批：Milvus 参数治理与运维清单

### 目标
把当前固定索引参数推进到“可比较、可治理”。

### 必改文件

#### 11）`apps/api/app/core/milvus_service.py`
**改造目标：**
- 不再硬编码唯一索引策略
- 把索引参数配置化
- 为不同 collection / profile 提供不同参数

#### 12）`apps/api/app/config.py`
**建议新增配置：**
- `MILVUS_INDEX_TYPE`
- `MILVUS_METRIC_TYPE`
- `MILVUS_NLIST`
- `MILVUS_NPROBE`
- `MILVUS_BATCH_SIZE`
- `MILVUS_SEARCH_PROFILE`

### 建议新增脚本
- `scripts/bench/rebuild_milvus_indexes.py`
- `scripts/bench/run_vector_backend_benchmark.py`

---

## 4. Qdrant 实验分支：实施顺序

Qdrant **现在不是主线替换**，而是旁路验证分支。

---

## 4.1 开分支前提

必须满足以下条件再开分支：

1. PR #41 边界不再返工
2. provider 已统一
3. `VectorStoreRepository` 已抽出
4. benchmark 脚手架已存在

如果这四条没满足，先做 Qdrant 分支只会让复杂度翻倍。

---

## 4.2 Qdrant 分支实施顺序

### Step 1：只新增 adapter，不动页面
#### 新增文件
- `apps/api/app/core/qdrant_service.py`
- `apps/api/app/core/qdrant_mapper.py`
- `apps/api/app/core/qdrant_filter_compiler.py`

#### 原则
- 不碰：
  - `Chat.tsx`
  - `Read.tsx`
  - `Notes.tsx`
- 不重做 runtime 主链
- 只在后端 adapter 层接入

---

### Step 2：接入统一 repository
#### 必改文件
- `apps/api/app/core/vector_store_repository.py`
- `apps/api/app/core/providers/provider_factory.py`
- `apps/api/app/config.py`

#### 动作
- 通过 `VECTOR_STORE_BACKEND=qdrant` 切换后端
- 保证上层 orchestration 完全不感知底层变更

---

### Step 3：迁移最小集合，不迁移全量页面链路
#### 实验范围
只先覆盖：

- `paper_contents_v2`
- dense search
- metadata filter
- topk retrieval

不要一开始就做：

- 全量 worker
- 全量 import pipeline
- 全量历史数据迁移
- 全量多模态回灌

---

### Step 4：复用同一 benchmark
#### 必做对比
- recall@k
- rerank 后质量
- latency
- ingest speed
- filter correctness
- 本地开发体验
- 资源占用

#### 测试文件建议新增
- `apps/api/tests/integration/test_retrieval_backend_qdrant.py`
- `apps/api/tests/integration/test_qdrant_filter_parity.py`
- `apps/api/tests/integration/test_backend_parity_milvus_vs_qdrant.py`

---

### Step 5：只在实验分支写迁移脚本
#### 建议新增
- `scripts/migration/export_milvus_points.py`
- `scripts/migration/import_qdrant_points.py`
- `scripts/migration/verify_backend_parity.py`

注意：
**不要在主线先写全量数据迁移。**
先证明值得迁。

---

## 5. 推荐分阶段提交顺序

### PR-A：模型 provider 对齐
改：
- `apps/api/app/config.py`
- `apps/api/app/core/qwen3vl_service.py`
- `apps/api/app/core/reranker_service.py`

新增：
- `apps/api/app/core/providers/*`

---

### PR-B：抽 retrieval repository
改：
- `apps/api/app/core/multimodal_search_service.py`
- `apps/api/app/core/milvus_service.py`
- `apps/api/app/models/retrieval.py`

新增：
- `apps/api/app/core/vector_store_repository.py`

---

### PR-C：hybrid scoring 正式化
改：
- `apps/api/app/core/bm25_service.py`
- `apps/api/app/core/multimodal_search_service.py`

新增：
- `apps/api/app/core/retrieval_scoring.py`
- `apps/api/app/core/retrieval_trace.py`

---

### PR-D：benchmark 与集成验证
改/增：
- `scripts/eval_retrieval.py`
- `scripts/evals/run_rag_eval.py`
- `apps/api/tests/integration/test_retrieval_*`

---

### PR-E：Qdrant adapter 实验分支
新增：
- `apps/api/app/core/qdrant_service.py`
- `apps/api/app/core/qdrant_mapper.py`
- `apps/api/app/core/qdrant_filter_compiler.py`

改：
- `apps/api/app/config.py`
- `apps/api/app/core/vector_store_repository.py`

---

## 6. 当前最合理的执行顺序

结合你刚完成的 PR #41，我给出的顺序是：

> **先稳定 Notes ownership 成果，不再返工页面职责**  
> **再做 provider 对齐**  
> **再抽 vector store repository**  
> **再补 benchmark**  
> **最后做 Qdrant 实验分支**

即：

**PR #41 完成后 → PR-A → PR-B → PR-C → PR-D → PR-E**

---

## 7. 最终结论

### 现在不该做
- 不该再次把 Chat / Read / Notes 拉回 ownership 重构
- 不该现在就全量迁移 Qdrant
- 不该在没有 benchmark 的前提下判断 Milvus 落后

### 现在最该做
- 先把检索栈从“Milvus 直连实现”升级为“可替换后端架构”
- 先把 reranker 切到你的目标路线
- 先让 benchmark 成为决策依据

### 一句话版
> **PR #41 之后，主战场已经从页面职责收口，切换到 retrieval 内核工程化；Milvus 继续演进是主线，Qdrant 只做并行实验分支。**
