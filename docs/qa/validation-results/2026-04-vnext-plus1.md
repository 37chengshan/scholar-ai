# vNext+1 验收结果（2026-04）

作者：glm5.1+37chengshan
日期：2026-04-20
来源：`artifacts/validation-results/2026-04-vnext-plus1.sample.json`

## 执行摘要

- total_cases: 12
- passed_cases: 10
- failed_cases: 2
- import_success_rate: 75.0%
- citation_coverage_rate: 100.0%
- low_confidence_rate: 16.7%

## 结果表

| case_id | pass/fail | duration_ms | final_status | final_stage | fallback_depth | recoverable | paper_created | query_ready | citation_present | low_confidence_flag | failure_reason |
|---|---|---:|---|---|---:|---|---|---|---|---|---|
| IMP-001 | pass | 8300 | completed | completed | 0 | true | true | true | false | false | |
| IMP-002 | pass | 42100 | completed | completed | 0 | true | true | true | false | false | |
| IMP-003 | pass | 50300 | completed | completed | 1 | true | true | true | false | false | |
| IMP-004 | pass | 16500 | completed | completed | 1 | true | true | true | false | false | |
| IMP-005 | pass | 15100 | completed | completed | 0 | true | true | true | false | false | |
| IMP-006 | pass | 17900 | completed | completed | 1 | true | true | true | false | false | |
| IMP-007 | fail | 8100 | awaiting_user_action | awaiting_user_action | 3 | true | false | false | false | false | NO_PDF_UPLOAD_REQUIRED |
| IMP-008 | pass | 12300 | completed | completed | 0 | true | true | true | false | false | |
| RAG-001 | pass | 2900 | answer_ready | answer_ready | 0 | true | false | true | true | false | |
| RAG-002 | pass | 3500 | answer_ready | answer_ready | 0 | true | false | true | true | false | |
| RAG-003 | pass | 3200 | answer_ready | answer_ready | 0 | true | false | true | true | false | |
| RAG-004 | fail | 3100 | answer_ready | answer_ready | 0 | true | false | true | true | true | LOW_CONFIDENCE_NOT_SHOWN_IN_UI |

## 备注

- IMP-007 为设计期望失败（待用户接力上传），不计入系统不可恢复失败。
- RAG-004 暴露了提示展示层遗漏，需在后续修复后复跑。