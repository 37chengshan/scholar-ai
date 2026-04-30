---
owner: app-foundation
status: in-progress
depends_on: []
last_verified_at: 2026-04-21
evidence_commits:
  - bb7ef1f
---

# PR-A 到 PR-E 检索工程化升级与 Qdrant 实验五阶段执行计划

作者：GPT-5.4 + 37chengshan

## 目标

在继续使用 Milvus 作为主线向量后端的前提下，完成 ScholarAI 检索链路的工程化升级，并在独立实验分支上引入 Qdrant，使用同一套真实 benchmark 数据、同一套查询集和同一套指标完成可决策的对比验证。

本计划严格基于两类输入形成：

- 用户要求的五段式交付顺序：PR-A → PR-B → PR-C → PR-D → PR-E。
- 当前代码现状：主搜索链仍直连 Milvus 与旧 reranker service，但 embedding/reranker factory 已存在且在应用启动路径中可用。

## 当前基线

### Git 与基线提交

- 当前主线基点：origin/main @ bb7ef1f。
- 本阶段工作分支基于最新 main 拉起，不回滚既有页面 ownership 与 runtime 主链收口成果。

### 已确认的代码事实

1. 主搜索链入口是 apps/api/app/core/multimodal_search_service.py。
2. 该入口目前直接依赖 qwen3vl_service、milvus_service、旧版 reranker_service。
3. 仓库已存在可复用的模块化 reranker 实现：
   - apps/api/app/core/reranker/base.py
   - apps/api/app/core/reranker/bge_reranker.py
   - apps/api/app/core/reranker/qwen3vl_reranker.py
   - apps/api/app/core/reranker/factory.py
4. 应用启动路径 apps/api/app/main.py 已经通过 get_embedding_service() 与 get_reranker_service() 进行懒加载或预热，说明工厂不是新需求，而是主链尚未完全对齐。
5. 当前没有任何 qdrant_service、qdrant mapper 或 vector store repository 抽象文件。
6. 当前 benchmark 资产不能作为最终决策依据：
   - scripts/eval_retrieval.py 仍保留 mock_mode 路径。
   - scripts/evals/run_rag_eval.py 存在 mock answer fallback。
   - apps/api/tests/benchmarks/run_search_benchmark.py 使用 fixture + random latency 生成伪报告。

### 本阶段不做的事

- 不重做 apps/web 页面 ownership。
- 不返工已完成的 runtime 主链收口。
- 不在主线中提前切换默认后端到 Qdrant。
- 不把“真实 benchmark”继续建立在随机延迟或 mock fallback 之上。

## 统一交付原则

1. 每个 PR 都必须是可单独 review、可单独验证、可单独回退的最小闭环。
2. 每个 PR 完成后都执行一次代码审查、最小验证、push 和 PR 模板校验。
3. 改 contract surface 时同步更新：
   - docs/specs/architecture/api-contract.md
   - docs/specs/domain/resources.md
4. 改检索链路架构或运行方式时同步检查并必要时更新：
   - docs/specs/architecture/system-overview.md
   - architecture.md
5. 所有 benchmark 结论必须来自真实运行，且明确区分 cold start、warm start、trace on/off、Milvus/Qdrant。

## 执行顺序

1. PR-A：主链 provider 对齐与契约冻结
2. PR-B：Milvus repository 抽象与结果 contract 固化
3. PR-C：hybrid scoring 与 retrieval trace 工程化
4. PR-D：真实 benchmark 基线与评测脚本重写
5. PR-E：Qdrant 实验接入与同口径对比验证

## PR-A：主链 provider 对齐与契约冻结

### 目标

将主搜索链从“直接调用具体服务单例”对齐到现有 embedding/reranker factory，同时冻结本阶段检索结果 contract、provider 配置面和 review 基线。

### 主要改动

- 改造 apps/api/app/core/multimodal_search_service.py：
  - embedding 获取统一走 app.core.embedding.factory。
  - reranker 获取统一走 app.core.reranker.factory。
  - 清理对旧 reranker_service.py 的直接依赖。
- 梳理 apps/api/app/models/retrieval.py 中的返回字段，补充或预留 provider/backend trace 所需 contract，但不提前暴露不稳定字段到外部 API。
- 对齐配置读取路径：apps/api/app/config.py。
- 补齐或修正与 factory 对接相关的单元测试和集成测试。

### 重点文件

- apps/api/app/core/multimodal_search_service.py
- apps/api/app/core/embedding/factory.py
- apps/api/app/core/reranker/factory.py
- apps/api/app/core/reranker_service.py
- apps/api/app/models/retrieval.py
- apps/api/app/config.py
- apps/api/tests/unit/test_reranker_factory.py
- apps/api/tests/unit/test_qwen3vl_reranker.py
- apps/api/tests/unit/test_multimodal_search_service_intent.py
- apps/api/tests/integration/test_multimodal_search.py

### 验收标准

- 主搜索链不再直接依赖旧 reranker_service 作为默认入口。
- embedding/reranker 的实例来源与应用启动路径一致。
- intent、query_intent、retrieval_mode 等既有语义不回归。
- 默认主线仍保持 Milvus + 当前兼容的 embedding 维度，不引入 collection 维度错配。

### 最小验证

- cd apps/api && pytest -q tests/unit/test_reranker_factory.py --maxfail=1
- cd apps/api && pytest -q tests/unit/test_qwen3vl_reranker.py --maxfail=1
- cd apps/api && pytest -q tests/unit/test_multimodal_search_service_intent.py --maxfail=1
- cd apps/api && pytest -q tests/integration/test_multimodal_search.py --maxfail=1

### 主要风险

- 若在此阶段顺手切换默认 embedding provider，可能直接触发 Milvus collection 向量维度不兼容。
- 旧测试中存在对过时接口的 patch，可能需要重写而不是小修。

## PR-B：Milvus repository 抽象与结果 contract 固化

### 目标

把业务检索编排从 Milvus 具体 API 中解耦，形成可替换的 vector store repository 合同，但主线后端仍只接 Milvus。

### 主要改动

- 新增 repository 抽象层，统一输入 SearchConstraints，统一输出 canonical RetrievedChunk。
- 将 multimodal_search_service 的读路径改为依赖 repository，而不是直接依赖 milvus_service 的搜索接口。
- 对 Milvus 特有 hit/raw_data 做边界封装，避免泄漏到业务层。

### 重点文件

- apps/api/app/core/vector_store_repository.py
- apps/api/app/core/milvus_service.py
- apps/api/app/core/multimodal_search_service.py
- apps/api/app/models/retrieval.py
- apps/api/tests/test_retrieval_schema.py
- apps/api/tests/unit/core/test_milvus_unified.py
- apps/api/tests/unit/test_milvus_service_collection_bootstrap.py
- apps/api/tests/unit/test_search_library_contract.py

### 验收标准

- 业务层只消费统一 repository 结果，不直接解释 Milvus 原生 hit 结构。
- SearchConstraints 到 repository 的过滤语义稳定。
- Milvus 仍是唯一启用的向量后端，行为与 PR-A 基线保持一致。

### 最小验证

- cd apps/api && pytest -q tests/test_retrieval_schema.py --maxfail=1
- cd apps/api && pytest -q tests/unit/core/test_milvus_unified.py --maxfail=1
- cd apps/api && pytest -q tests/unit/test_milvus_service_collection_bootstrap.py --maxfail=1
- cd apps/api && pytest -q tests/unit/test_search_library_contract.py --maxfail=1

### 主要风险

- 抽象层若直接暴露 Milvus 特有参数，会导致后续 Qdrant 对接名义抽象、实际耦合。
- 若把写入、建索引、初始化一次性全抽，范围会明显膨胀；此阶段只覆盖读链路。

## PR-C：hybrid scoring 与 retrieval trace 工程化

### 目标

将 dense score、sparse score、融合排序、reranker 排序和调试 trace 从搜索主流程中拆出，形成可验证的独立模块，为真实 benchmark 提供可复用指标面。

### 主要改动

- 新增 retrieval scoring 模块，承接：
  - 稠密分数归一化
  - sparse lexical 分数叠加
  - weighted RRF 或当前融合策略
  - rerank 后重排
- 新增 retrieval trace 模块，用于输出内部评分分解与 provider/backend trace。
- 调整 bm25_service 与 multimodal_search_service 的职责边界。

### 重点文件

- apps/api/app/core/retrieval_scoring.py
- apps/api/app/core/retrieval_trace.py
- apps/api/app/core/bm25_service.py
- apps/api/app/core/multimodal_search_service.py
- apps/api/app/models/retrieval.py
- apps/api/tests/unit/test_multimodal_search_service_intent.py
- apps/api/tests/integration/test_multimodal_search.py

### 验收标准

- 混合检索评分逻辑可单测，不再只能通过超长集成链路观察。
- trace 关闭时不污染默认对外响应；trace 打开时可看到稳定的分数分解。
- 主链排序变化可被 benchmark 数据集追踪，而不是凭体感判断。

### 最小验证

- cd apps/api && pytest -q tests/unit/test_multimodal_search_service_intent.py --maxfail=1
- cd apps/api && pytest -q tests/integration/test_multimodal_search.py --maxfail=1
- cd apps/api && pytest -q tests/unit --maxfail=1 -k "retrieval or search or bm25"

### 主要风险

- 排序逻辑工程化后，结果顺序极可能发生变化；如果没有冻结 benchmark 查询集，会难以区分“逻辑改善”和“结果漂移”。

## PR-D：真实 benchmark 基线与评测脚本重写

### 目标

建立一套真实、可复跑、可审计的检索 benchmark 基线，替换当前随机或 mock 驱动的伪 benchmark。

### 主要改动

- 重写 apps/api/tests/benchmarks/run_search_benchmark.py，使其真正打后端检索链路。
- 收敛 scripts/eval_retrieval.py，默认不再静默走 mock_mode。
- 收敛 scripts/evals/run_rag_eval.py，去掉会污染结论的 mock answer fallback，或强制显式声明仅用于演示。
- 引入冻结查询集、冻结语料快照与统一报告产物格式。
- 基于同一 harness 输出 Milvus 基线报告，作为 PR-E 对比的唯一参考。

### 重点文件

- apps/api/tests/benchmarks/run_search_benchmark.py
- apps/api/tests/benchmarks/catalog.py
- apps/api/tests/benchmarks/reporting.py
- scripts/eval_retrieval.py
- scripts/evals/run_rag_eval.py
- tests/evals/**
- tests/fixtures/**

### 验收标准

- benchmark 真正访问检索链路，不再通过 random latency 生成报告。
- 报告至少包含：Recall@5、Recall@10、MRR、section hit rate、latency p50/p95。
- 报告明确标记：数据集版本、运行 profile、trace 开关、后端类型。
- 同一环境下连续复跑 3 次，结果波动在可接受范围内。

### 最小验证

- cd apps/api && pytest -q tests/benchmarks --maxfail=1
- cd apps/api && pytest -q tests/evals --maxfail=1
- cd apps/api && python ../../scripts/eval_retrieval.py
- cd apps/api && python ../../scripts/evals/run_rag_eval.py

### 真实 benchmark 执行口径

1. 固定语料快照。
2. 固定 query 集与 gold evidence。
3. 分别记录 cold run 与 warm run。
4. 默认 trace off，额外再跑一次 trace on 开销。
5. 输出 JSON 与 Markdown 报告，供后续 PR body 和评审引用。

### 主要风险

- 如果默认仍允许 mock fallback，团队会继续得到不可决策的“漂亮报告”。
- 若数据集不冻结，PR-E 的 Milvus/Qdrant 比较会失真。

## PR-E：Qdrant 实验接入与同口径对比验证

### 目标

在独立实验分支上增加 Qdrant repository 实现，并基于 PR-D 冻结的同一 benchmark 体系完成 Milvus 与 Qdrant 的同口径对比，不改变主线默认后端。

### 主要改动

- 新增 Qdrant adapter、mapper 与 filter compiler。
- 在 repository 层引入后端选择配置，但默认值保持 Milvus。
- 使用 PR-D 的同一 benchmark harness 对 Qdrant 运行 paired benchmark。
- 产出实验报告与结论，明确是否值得后续进入主线候选。

### 重点文件

- apps/api/app/core/qdrant_service.py
- apps/api/app/core/qdrant_mapper.py
- apps/api/app/core/qdrant_filter_compiler.py
- apps/api/app/core/vector_store_repository.py
- apps/api/app/config.py
- apps/api/tests/unit/test_qdrant_repository.py
- apps/api/tests/integration/test_qdrant_search.py
- scripts/eval_retrieval.py
- apps/api/tests/benchmarks/run_search_benchmark.py

### 验收标准

- Milvus 与 Qdrant 对同一 SearchConstraints 的解释保持 contract parity。
- 同一 benchmark 查询集、同一指标口径下能稳定输出双后端对比结果。
- 主线默认后端仍为 Milvus；Qdrant 仅实验启用。
- 形成最终对比结论：质量、延迟、资源占用、迁移成本。

### 最小验证

- cd apps/api && pytest -q tests/unit/test_qdrant_repository.py --maxfail=1
- cd apps/api && pytest -q tests/integration/test_qdrant_search.py --maxfail=1
- cd apps/api && pytest -q tests/benchmarks --maxfail=1
- cd apps/api && python ../../scripts/eval_retrieval.py --backend milvus
- cd apps/api && python ../../scripts/eval_retrieval.py --backend qdrant

### 主要风险

- Qdrant 与 Milvus 在过滤、分页稳定性、分数归一化上的语义可能不完全一致。
- 若直接对比未先完成 contract parity，得出的优劣结论没有意义。

## 每个 PR 的统一审查与推送动作

1. 先跑最小验证，确认没有把问题推给下一个 PR。
2. 运行一轮代码审查，优先检查：
   - contract 漂移
   - fallback 遗留
   - mock path 泄漏到正式 benchmark
   - vector backend 特有字段泄漏
3. 仅 stage 本 PR 相关文件，避免把无关工作树残留带入。
4. 使用仓库脚本创建 PR：
   - bash scripts/check-pr-template-body.sh --body-file <filled-pr-body.md>
   - bash scripts/pr_create_with_template_check.sh ...
5. 在 PR 描述中附带本阶段实际跑过的 benchmark 或测试命令结果摘要。

## 建议的分支命名

- feat/pr-a-retrieval-provider-alignment
- feat/pr-b-milvus-repository-contract
- feat/pr-c-hybrid-scoring-trace
- feat/pr-d-real-retrieval-benchmark
- feat/pr-e-qdrant-benchmark-experiment

## 之前推送的回看项

在开始 PR-A 实现前，先对最近一次已推送 PR 做一次轻量回看：

- PR 模板字段是否完整。
- 是否混入无关文件。
- 最小验证命令是否真实执行而非占位。
- 文档同步项是否与实际变更匹配。

## 完成定义

满足以下条件才算本阶段完成：

1. PR-A 到 PR-E 全部完成并各自有审查记录。
2. 主线 Milvus 检索工程化升级完成。
3. Qdrant 实验分支完成同口径 benchmark 对比。
4. 最终 benchmark 来自真实运行，不依赖 mock 或随机延迟。
5. 文档、脚本、测试与实验报告可支撑后续是否迁移后端的工程决策。