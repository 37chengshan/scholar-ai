# v2.1.3 Milvus Live Search Entity Decode Report

- overall_status: PASS
- gate_passed_for_64x3: True
- sampled_queries: 1
- id_only_success: True

## ID-only live smoke

| stage | collection | total | success | unsupported_field_type_count | fallback_used_count |
|---|---|---:|---:|---:|---:|
| raw | paper_contents_v2_qwen_v2_raw_v2_1 | 1 | 1 | 0 | 0 |
| rule | paper_contents_v2_qwen_v2_rule_v2_1 | 1 | 1 | 0 | 0 |
| llm | paper_contents_v2_qwen_v2_llm_v2_1 | 1 | 1 | 0 | 0 |

## Version matrix

- python_version: 3.11.15
- pymilvus_version: 2.6.12
- milvus_server_version: v2.3.3
- milvus_lite_version: 2.5.1
- index_type: IVF_FLAT
- metric_type: COSINE
- embedded_fallback_enabled: True
- embedded_fallback_active: False

## Gate

Only if all conditions are true, full 64x3 answer/citation can run:
- Unsupported field type count = 0: True
- fallback_used = false: True
- answer_smoke total > 0: True

