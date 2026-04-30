# RAG 最小评测集规范（vNext+1）

作者：glm5.1+37chengshan
日期：2026-04-20
数据集：`tests/evals/rag_eval_dataset.json`
执行器：`scripts/evals/run_rag_eval.py`

## 目标

建立可重复执行的最小回归基线，用于比较检索、chunk、rerank、confidence 相关变更前后表现。

## 规模与分布（冻结）

- 总样本：32
- A 单文档事实：8
- B 单文档摘要：6
- C 跨文档比较：6
- D 冲突证据：4
- E 无法回答/证据不足：4
- F 低置信应触发：4

## 单条样本字段

- case_id
- question
- paper_ids
- query_type
- expected_behavior
- must_have_citation
- allow_low_confidence
- expected_evidence_scope
- notes

## 执行方式

Mock（默认）：

```bash
python3 scripts/evals/run_rag_eval.py \
  --dataset tests/evals/rag_eval_dataset.json \
  --output artifacts/validation-results/rag-eval-sample-summary.json
```

Real（接入真实回答结果）：

```bash
python3 scripts/evals/run_rag_eval.py \
  --dataset tests/evals/rag_eval_dataset.json \
  --answers-file artifacts/validation-results/rag-answers.json \
  --output artifacts/validation-results/rag-eval-summary.json
```

`answers-file` 条目格式：

- case_id
- answer
- citations（数组）
- low_confidence_flag
- answer_evidence_consistency

## 输出字段（最低要求）

- total_cases
- passed_cases
- citation_present_rate
- low_confidence_rate
- average_consistency
- failed_case_ids

## 判定规则（最低）

- must_have_citation=true 且无 citations -> fail
- allow_low_confidence=false 且 low_confidence_flag=true -> fail
- answer_evidence_consistency < 0.5 且非低置信允许场景 -> fail

## 回归使用建议

- 每次检索/回答策略改动后执行一次
- 与上一次 summary JSON 对比
- 对 failed_case_ids 做定向追踪
