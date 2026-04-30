# vNext+1 验证版总结

作者：glm5.1+37chengshan
日期：2026-04-20
分支：feat/vnext-plus1-validation-20260420

## 背景与范围

本次仅覆盖验证闭环，不扩展业务能力。范围固定为：

1. 统一验证入口与 CI 闸门
2. 真实链路验收矩阵
3. 指标沉淀与结构化导出
4. RAG 最小评测基线

## 执行命令

```bash
bash scripts/verify/run-all.sh
bash scripts/verify/run-validation-matrix.sh
python3 scripts/evals/run_rag_eval.py \
  --dataset tests/evals/rag_eval_dataset.json \
  --output artifacts/validation-results/rag-eval-sample-summary.json
```

## 验收矩阵摘要

- 矩阵文件：`docs/plans/archive/reports/qa/validation-matrix-vnext-plus1.md`
- 结果文件：`docs/plans/archive/reports/qa/validation-results/2026-04-vnext-plus1.md`
- 结构化输入：`artifacts/validation-results/2026-04-vnext-plus1.sample.json`

## 指标摘要

- 汇总脚本：`scripts/verify/summarize_validation_results.py`
- 汇总输出：
  - `artifacts/validation-results/2026-04-vnext-plus1.summary.json`
  - `artifacts/validation-results/2026-04-vnext-plus1.summary.md`

关键指标口径见：`docs/plans/archive/reports/qa/metrics-spec-vnext-plus1.md`

## RAG 评测摘要

- 数据集：`tests/evals/rag_eval_dataset.json`（32 条）
- 规范：`docs/plans/archive/reports/qa/rag-eval-spec.md`
- 执行器：`scripts/evals/run_rag_eval.py`
- 样例输出：`artifacts/validation-results/rag-eval-sample-summary.json`

## 剩余风险

1. 样例结果为基线模板，需在真实环境复跑覆盖真实失败分布。
2. API 集成测试依赖数据库与缓存服务，CI/本地需保持环境一致。
3. 低置信提示在前端展示链路需要持续追踪回归。
