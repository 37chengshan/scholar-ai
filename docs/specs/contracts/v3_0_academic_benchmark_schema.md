# v3.0 Academic Benchmark Schema

## Purpose

冻结 `Benchmark 3.0` 的 corpus、query、evidence、claim、run artifact 契约。

## Scope

适用于：

1. `apps/api/artifacts/benchmarks/v3_0_academic/`
2. public / blind 数据文件
3. retrieval / answer / abstain / diff artifact

## Rules

1. `phase6` 继续作为 `v2.x` 冻结门禁真源，不直接写入。
2. `Benchmark 3.0` 使用独立命名空间：`apps/api/artifacts/benchmarks/v3_0_academic/`
3. 后端字段统一使用 `snake_case`。
4. public 与 blind 不允许维护平行 schema。
5. `claims[]` 为正式字段，可为空但不能另造平行结构。
6. kickoff 之后，`formula` gate、blind owner、`claims[]` 覆盖范围、discipline quota 以 `docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_kickoff_freeze.md` 为执行真源。

## Root Layout

```txt
apps/api/artifacts/benchmarks/v3_0_academic/
  corpus_public.json
  corpus_blind.json
  manifest.json
  runs/{run_id}/...
```

## Corpus Top-level

```json
{
  "dataset_version": "v3.0-academic-p0",
  "split": "public_dev",
  "paper_count": 200,
  "query_count": 640,
  "query_families": [],
  "papers": [],
  "queries": []
}
```

`split` 允许值：

1. `public_dev`
2. `public_test`
3. `blind_test`

## Paper Object

必填：

1. `paper_id`
2. `title`
3. `discipline`
4. `subfield`
5. `year`
6. `language`
7. `source_path`
8. `pdf_source_type`
9. `scan_quality`
10. `layout_complexity`
11. `table_density`
12. `figure_density`
13. `formula_density`
14. `paper_length_bucket`

## Query Object

必填：

1. `query_id`
2. `question`
3. `family`
4. `discipline`
5. `difficulty`
6. `answerability`
7. `paper_scope`
8. `gold_short_answer`
9. `gold_long_answer`
10. `must_abstain`
11. `abstain_reason`
12. `expected_paper_ids`
13. `expected_sections`
14. `expected_evidence`
15. `claims`

`family` 允许值：

1. `fact`
2. `method`
3. `experiment_result`
4. `numeric`
5. `table`
6. `figure`
7. `formula`
8. `limitation`
9. `compare`
10. `cross_paper_synthesis`
11. `citation_trace`
12. `kb_global`
13. `no_answer`
14. `conflict_verification`

## Evidence Object

必填：

1. `evidence_id`
2. `paper_id`
3. `page_num`
4. `section_path`
5. `char_start`
6. `char_end`
7. `quote`
8. `evidence_type`
9. `support_role`
10. `citation_target`

`evidence_type`：

1. `text`
2. `table`
3. `figure`
4. `formula`

## Claim Object

必填：

1. `claim_id`
2. `claim_text`
3. `support_required`
4. `evidence_ids`
5. `support_level`

`support_level`：

1. `supports`
2. `partially_supports`
3. `insufficient`
4. `refutes`

## Run Artifacts

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

## Verification

1. 所有文档引用的字段名必须与本文件一致。
2. 新增字段时必须同步更新本文件与 gate 逻辑。

## Kickoff Freeze

以下实现边界已冻结，不再作为 open question：

1. `formula` 在 P0 为 `report-only`
2. `claims[]` 在 P0 仅对指定高价值 families 强制
3. blind owner 分工固定
4. discipline / family 配额固定
