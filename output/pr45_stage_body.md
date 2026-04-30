## 变更目的
- 将 PR 45 更新为 retrieval benchmark close-out 说明，同步 qwen 双模型多轮真实验证与 Milvus / Qdrant 同口径对照的最终结论。

## 变更内容
- [ ] 前端（apps/web）
- [x] 后 端（apps/api）
- [x] 文档（docs）
- [x] 脚本 / 基础设施（scripts / infra）

详细说明：
- 修复 scripts/eval_retrieval.py 的真实评估口径，补齐 --user-id 透传，并在只有 expected_paper_ids 时按 paper_id 计算 Recall@K / MRR。
- 为 eval harness 新增回归测试 apps/api/tests/unit/test_eval_retrieval_harness.py，覆盖 mock 模式下的 paper-level 计分行为。
- 完成 qwen 双模型在 Milvus 主线的 Dataset-S 三轮真实 benchmark，结果稳定一致。
- 补齐 Qdrant 本地持久化执行路径、Dataset-S 写入路径与 round-trip 集成测试，完成 Qdrant 同口径三轮 paired benchmark。
- 新增 docs/plans/archive/reports/2026-04-21_retrieval_benchmark_closeout_report.md，作为本轮 close-out 总报告；并保留 docs/plans/archive/reports/2026-04-21_retrieval_benchmark_validation.md 作为早先阶段性报告。

## Close-out 结论
- 已完成：qwen3-vl-2b embedding + qwen3-vl-reranker 在 Milvus 主线的三轮真实验证。
- 已完成：Milvus / Qdrant 在 Dataset-S 上的同口径 paired benchmark。
- 最终结论：当前没有证据支持将主线从 Milvus 切换到 Qdrant；Qdrant 作为已打通的对照后端继续保留观察。
- 仍待后续阶段推进：更大规模 Dataset-L、更多 cross-paper query、远程 Qdrant server 部署形态对照。

## 影响范围
- 页面：无直接 UI 变更，但 close-out 结果为检索主线与后端路线判断提供依据。
- 接口：scripts/eval_retrieval.py 的 CLI 增加 --user-id / --use-reranker 真实口径透传；评估结果在 paper-level gold 场景下改为正确计分。
- 服务/脚本：真实 retrieval 评估链路、preflight、Dataset-S 数据准备、Qdrant 本地持久化写入与搜索、eval harness 回归测试。
- 数据/配置：新增并使用 QDRANT_LOCAL_PATH；使用 benchmark-user 作为真实导入与评估用户隔离标识；默认主线后端仍为 milvus。

## 风险评估
- 风险等级：中
- 主要风险：Qdrant 对照当前基于本地持久化模式，不代表远程 Qdrant server 的部署与性能结论；Dataset-S 规模仍偏小，不能直接外推到生产规模。
- 回滚方式：回滚本次 eval harness、Qdrant 本地模式与文档变更，恢复到 Milvus 主线阶段性验证状态。

## 交付单元追踪
- Phase ID: Gate1-7 / retrieval-validation
- Deliverable Unit: retrieval-benchmark-closeout
- Migration-Task: none
- 未覆盖项: Dataset-L / 更大规模真实集；更多 cross-paper queries；远程 Qdrant server 形态 benchmark。

## 自测清单
### 仓库治理
- [x] bash scripts/check-doc-governance.sh

### 后端
- [x] cd apps/api && /Users/cc/.virtualenvs/scholar-ai-api/bin/python -m pytest tests/unit/test_eval_retrieval_harness.py -q
- [x] cd apps/api && /Users/cc/.virtualenvs/scholar-ai-api/bin/python -m pytest tests/integration/test_qdrant_search.py -q
- [x] cd /Users/cc/scholar-ai-deploy/scholar-ai-project/scholar-ai && /Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/preflight_retrieval_env.py --backend milvus --output artifacts/benchmarks/real/preflight_report_qwen_milvus.json
- [x] cd /Users/cc/scholar-ai-deploy/scholar-ai-project/scholar-ai && /Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/prepare_real_retrieval_dataset.py --user-id benchmark-user --pages-per-paper 4 --output-dir artifacts/benchmarks/real/qwen
- [x] cd /Users/cc/scholar-ai-deploy/scholar-ai-project/scholar-ai && /Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/eval_retrieval.py --golden artifacts/benchmarks/real/qwen/golden_queries_dataset_s.json --backend milvus --user-id benchmark-user --use-reranker --paper-id dataset-s-001 dataset-s-002 dataset-s-003 --output artifacts/benchmarks/real/qwen/eval_retrieval_real_round1.json
- [x] cd /Users/cc/scholar-ai-deploy/scholar-ai-project/scholar-ai && /Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/eval_retrieval.py --golden artifacts/benchmarks/real/qwen/golden_queries_dataset_s.json --backend milvus --user-id benchmark-user --use-reranker --paper-id dataset-s-001 dataset-s-002 dataset-s-003 --output artifacts/benchmarks/real/qwen/eval_retrieval_real_round2.json
- [x] cd /Users/cc/scholar-ai-deploy/scholar-ai-project/scholar-ai && RETRIEVAL_TRACE_ENABLED=1 /Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/eval_retrieval.py --golden artifacts/benchmarks/real/qwen/golden_queries_dataset_s.json --backend milvus --user-id benchmark-user --use-reranker --paper-id dataset-s-001 dataset-s-002 dataset-s-003 --output artifacts/benchmarks/real/qwen/eval_retrieval_real_round3_trace.json
- [x] cd /Users/cc/scholar-ai-deploy/scholar-ai-project/scholar-ai && VECTOR_STORE_BACKEND=qdrant QDRANT_URL='' /Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/prepare_real_retrieval_dataset.py --user-id benchmark-user --pages-per-paper 4 --output-dir artifacts/benchmarks/real/qwen_qdrant
- [x] cd /Users/cc/scholar-ai-deploy/scholar-ai-project/scholar-ai && VECTOR_STORE_BACKEND=qdrant QDRANT_URL='' /Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/preflight_retrieval_env.py --backend qdrant --output artifacts/benchmarks/real/preflight_report_qwen_qdrant_local.json
- [x] cd /Users/cc/scholar-ai-deploy/scholar-ai-project/scholar-ai && VECTOR_STORE_BACKEND=qdrant QDRANT_URL='' /Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/eval_retrieval.py --golden artifacts/benchmarks/real/qwen_qdrant/golden_queries_dataset_s.json --backend qdrant --user-id benchmark-user --use-reranker --paper-id dataset-s-001 dataset-s-002 dataset-s-003 --output artifacts/benchmarks/real/qwen_qdrant/eval_retrieval_real_round1.json
- [x] cd /Users/cc/scholar-ai-deploy/scholar-ai-project/scholar-ai && VECTOR_STORE_BACKEND=qdrant QDRANT_URL='' /Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/eval_retrieval.py --golden artifacts/benchmarks/real/qwen_qdrant/golden_queries_dataset_s.json --backend qdrant --user-id benchmark-user --use-reranker --paper-id dataset-s-001 dataset-s-002 dataset-s-003 --output artifacts/benchmarks/real/qwen_qdrant/eval_retrieval_real_round2.json
- [x] cd /Users/cc/scholar-ai-deploy/scholar-ai-project/scholar-ai && RETRIEVAL_TRACE_ENABLED=1 VECTOR_STORE_BACKEND=qdrant QDRANT_URL='' /Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/eval_retrieval.py --golden artifacts/benchmarks/real/qwen_qdrant/golden_queries_dataset_s.json --backend qdrant --user-id benchmark-user --use-reranker --paper-id dataset-s-001 dataset-s-002 dataset-s-003 --output artifacts/benchmarks/real/qwen_qdrant/eval_retrieval_real_round3_trace.json

## 文档是否需要同步
- [ ] 不需要
- [x] 需要，已同步更新

若需要，请说明更新了哪些文档：
- [x] docs/plans/archive/reports/2026-04-21_retrieval_benchmark_validation.md
- [x] docs/plans/archive/reports/README.md
- [x] docs/plans/archive/reports/2026-04-21_retrieval_benchmark_closeout_report.md

## 截图 / 录屏 / 输出
- qwen + Milvus：Round 1 / Round 2 / Round 3 Trace 指标一致，Recall@5=100%，Recall@10=100%，MRR=100%，Section Hit Rate=68.75%，Paper Hit Rate=100%
- qwen + Qdrant：Round 1 / Round 2 / Round 3 Trace 指标一致，Recall@5=93.75%，Recall@10=100%，MRR=100%，Section Hit Rate=68.75%，Paper Hit Rate=100%
- 差异点：Qdrant 在 ds-cp2 上稳定少 1 个 Top-5 cross-paper 目标论文；当前没有证据支持切换 Milvus 主线。
- 报告路径：docs/plans/archive/reports/2026-04-21_retrieval_benchmark_closeout_report.md

## 关联 Issue / 背景
- Closes #
- Related #45
