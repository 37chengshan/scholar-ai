# vNext+1 指标口径规范

作者：glm5.1+37chengshan
日期：2026-04-20

## 目标

冻结验证阶段指标命名和计算方式，确保不同批次结果可比较。

## Import 指标

- import_success_rate
  - 定义：导入类 case 中 `pass_fail=pass` 占比
- time_to_query_ready_ms
  - 定义：`query_ready=true` 的导入类 case 的 `duration_ms` 平均值
- awaiting_user_action_rate
  - 定义：`final_status=awaiting_user_action` 占导入类 case 比例
- upload_resume_success_rate
  - 定义：恢复类 case（IMP-003）通过率
- source_failure_breakdown
  - 定义：导入类失败 case 按 `failure_reason` 分组计数
- fallback_depth
  - 定义：导入类 case `fallback_depth` 的均值与分布

## RAG 指标

- citation_coverage_rate
  - 定义：RAG 类 case 中 `citation_present=true` 占比
- low_confidence_rate
  - 定义：RAG 类 case 中 `low_confidence_flag=true` 占比
- answer_evidence_consistency_avg
  - 定义：RAG 类 case 的 `answer_evidence_consistency` 平均值
- no_valid_sources_rate
  - 定义：RAG 类 case 中 `no_valid_sources=true` 占比

## 输出文件

- JSON 汇总：`artifacts/validation-results/2026-04-vnext-plus1.summary.json`
- Markdown 汇总：`artifacts/validation-results/2026-04-vnext-plus1.summary.md`

## 数据源字段要求

每条结果至少包含：
- case_id
- pass_fail
- duration_ms
- final_status
- final_stage
- fallback_depth
- recoverable
- paper_created
- query_ready
- citation_present
- low_confidence_flag
- failure_reason

RAG 类建议补充：
- answer_evidence_consistency
- no_valid_sources
