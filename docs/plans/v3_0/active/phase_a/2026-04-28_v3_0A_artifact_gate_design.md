---
标题：ScholarAI v3.0-A Academic Benchmark 3.0 Artifact 与 Gate 设计
日期：2026-04-28
状态：design
---

# 1. 核心决策

1. `phase6` 保持为 `v2.x` 冻结门禁真源。
2. `Benchmark 3.0` 使用独立命名空间：`apps/api/artifacts/benchmarks/v3_0_academic/`
3. artifact 结构尽量与 `phase6` 同构。
4. blind gate 与 public gate 共用大部分指标计算逻辑。

# 2. Root Layout

```txt
apps/api/artifacts/benchmarks/v3_0_academic/
  corpus_public.json
  corpus_blind.json
  manifest.json
  runs/{run_id}/...
```

# 3. Run Artifacts

每个 run 至少包含：

1. `meta.json`
2. `retrieval.json`
3. `evidence.json`
4. `answer_quality.json`
5. `abstain_quality.json`
6. `family_breakdown.json`
7. `domain_breakdown.json`
8. `dashboard_summary.json`
9. `diff_from_baseline.json`

# 4. Runner 模式

1. `public_offline`
   - 研发日常迭代
2. `blind_offline`
   - 受控盲评
3. `shadow_online`
   - 后续真实链路 shadow 观测

# 5. Baseline / Candidate / Diff

baseline：

1. 当前稳定主线
2. 同一 dataset_version 的参考 run

candidate：

1. 本轮待验证配置
2. 与 baseline 同 split、同 dataset_version

diff：

1. 对比 retrieval
2. 对比 evidence
3. 对比 answer
4. 对比 abstain
5. 对比 family/domain breakdown

# 6. Gate 维度

一级 gate：

1. retrieval
2. evidence
3. answer
4. abstain

二级 gate：

1. family non-regression
2. discipline non-regression
3. modality non-regression
4. blind/public gap monitoring

# 7. P0 指标建议

建议硬 gate：

1. `paper_hit_at_10`
2. `section_hit_at_10`
3. `recall_at_5`
4. `exact_chunk_hit_rate`
5. `citation_jump_valid_rate`
6. `answer_supported_rate`
7. `groundedness`
8. `abstain_precision`

建议 report-only：

1. `formula_family_score`
2. `conflict_faithfulness`
3. `multi_evidence_recall`

# 8. Breakdown 设计

P0 至少支持四个切片维度：

1. family
2. discipline
3. modality
4. answerability

# 9. Blind Gate 规则

1. 本地开发默认不可直接读取 blind gold。
2. blind run 只输出 aggregate + failure bucket summary。
3. blind 可阻断 release，但不返回样本级 gold 明细。

# 10. 与现有 `eval_service.py` 的关系

建议：

1. 不破坏现有 `phase6` 读取逻辑
2. 在 `eval_service.py` 中增加 benchmark namespace 概念
3. 复用现有归一化与 gate 计算思路

不建议：

1. 复制一套平行 benchmark service

# 11. 失败桶设计

建议统一 buckets：

1. `paper_miss`
2. `section_miss`
3. `exact_chunk_miss`
4. `evidence_scope_mismatch`
5. `unsupported_answer`
6. `false_answer_on_unanswerable`
7. `citation_jump_invalid`
8. `conflict_faithfulness_fail`

# 12. 结论

```txt
Artifact 与 gate 的目标不是多几个 JSON，
而是让 Benchmark 3.0 的每次提升或回退，
都能被定位到真实学术质量维度。
```
