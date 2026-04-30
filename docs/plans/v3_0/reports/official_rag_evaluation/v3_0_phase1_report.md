# v3.0 Phase 1 — Paper/Section Recall Evaluation Report

**Stage**: `raw`  |  **Verdict**: `PASS`

## Overall Metrics vs. v2.6.2 Baseline

| Metric | v2.6.2 Baseline | v3.0 Phase 1 | Delta | Gate |
|--------|----------------|--------------|-------|------|
| paper_hit_at_10 | 0.3438 | 1.0000 | +0.6562 | ✅ >= 0.7 |
| section_hit_at_10 | 0.6250 | 1.0000 | +0.3750 | ✅ >= 0.5 |
| oracle_recall_at_100 | 0.0000 | 0.6837 | +0.6837 | ✅ >= 0.6 |
| exact_recall_at_10 | 0.0000 | 0.7041 | +0.7041 | ✅ >= 0.3 |

## Gate Results

- ✅ PASS: `paper_hit_at_10 >= 0.7`
- ✅ PASS: `section_hit_at_10 >= 0.5`
- ✅ PASS: `oracle_recall_at_100 >= 0.6`
- ✅ PASS: `exact_recall_at_10 >= 0.3`

## Failure Bucket Distribution

| Bucket | Count |
|--------|-------|
| candidate_pool_miss | 31 |
| exact_miss | 23 |
| paper_miss | 0 |
| pass | 44 |
| section_miss | 0 |

## By Query Family

| Family | N | paper_hit | section_hit | exact | oracle@100 |
|--------|---|-----------|-------------|-------|------------|
| compare | 8 | 1.000 | 1.000 | 0.500 | 0.875 |
| cross_paper | 8 | 1.000 | 1.000 | 0.875 | 0.875 |
| fact | 25 | 1.000 | 1.000 | 0.880 | 0.800 |
| figure | 8 | 1.000 | 1.000 | 0.500 | 0.250 |
| hard | 8 | 1.000 | 1.000 | 0.750 | 0.250 |
| method | 25 | 1.000 | 1.000 | 0.800 | 0.720 |
| numeric | 8 | 1.000 | 1.000 | 0.625 | 0.750 |
| table | 8 | 1.000 | 1.000 | 0.125 | 0.625 |

## Notes

- Index built from `artifacts/papers/` chunk files (no re-parsing, no re-chunking).
- Dense retrieval uses Milvus `paper_contents_v2_api_tongyi_flash_{stage}_v2_4`.
- Section hit uses substring match against `normalized_section_path`.
