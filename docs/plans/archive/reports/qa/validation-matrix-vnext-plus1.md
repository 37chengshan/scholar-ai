# vNext+1 真实链路验收矩阵

作者：glm5.1+37chengshan
日期：2026-04-20
范围：导入 -> 解析 -> 入库 -> 问答主链路

## 使用方式

1. 先执行统一验证入口：`bash scripts/verify/run-all.sh`
2. 再按本矩阵逐条执行验收，记录到 `docs/plans/archive/reports/qa/validation-results/2026-04-vnext-plus1.md` 或 JSON。
3. 将 JSON 结果交给 `scripts/verify/summarize_validation_results.py` 产出指标。

## 验收矩阵

| case_id | scenario | input_type | sample_input | expected_result | expected_status_path | expected_user_action | expected_query_ready | notes |
|---|---|---|---|---|---|---|---|---|
| IMP-001 | 本地 PDF 小文件导入 | local_file | 1MB PDF | 导入成功，paper 创建 | created->queued->running->completed | 无 | 是 | 基线成功场景 |
| IMP-002 | 本地 PDF 大文件分片导入 | local_file | 80MB PDF | 上传完成并进入处理 | created->queued->running->completed | 无 | 是 | 并发分片 |
| IMP-003 | 上传中断后恢复 | local_file | 80MB PDF + 中断 | 复用 session 完成导入 | created->queued->running->completed | 重新打开页面后继续 | 是 | 恢复类场景 |
| IMP-004 | DOI 一键导入 | doi | 10.1145/XXXXXX | 自动下载并入库 | created->queued->running->completed | 无 | 是 | 回退链成功 |
| IMP-005 | arXiv 一键导入 | arxiv | arXiv:2604.01234 | 自动下载并入库 | created->queued->running->completed | 无 | 是 | arXiv 主路径 |
| IMP-006 | pdf_url 导入 | pdf_url | https://example.org/paper.pdf | 下载校验通过并入库 | created->queued->running->completed | 无 | 是 | HEAD/GET 探测 |
| IMP-007 | DOI 无 PDF 手动接力 | doi | 无 open access PDF DOI | 进入待用户动作并可接力上传 | created->queued->running->awaiting_user_action | 上传本地 PDF | 否（接力前） | 失败/恢复类 |
| IMP-008 | dedupe 命中决策 | local_file | 与现有 paper 重复文件 | 返回 dedupe 决策并继续可控 | created->queued->running->awaiting_user_action->completed | 选择 keep_existing 或 create_new | 是 | 失败/恢复类 |
| RAG-001 | 单文档问答 | rag_single | question + 1 paper_id | 有答案且有引用 | query_started->retrieval->answer_ready | 无 | 是 | 引用必须存在 |
| RAG-002 | 跨文档问答 | rag_cross_paper | question + 多 paper_ids | 有答案且跨文档引用 | query_started->retrieval->answer_ready | 无 | 是 | 对比问答 |
| RAG-003 | 带 citation 回答 | rag_single | 事实类问题 | citation 字段完整 | query_started->retrieval->answer_ready | 无 | 是 | contract 校验 |
| RAG-004 | 低置信提示场景 | rag_single | 证据不足问题 | 返回 lowConfidenceReasons | query_started->retrieval->answer_ready | 用户可选择追问/缩小范围 | 是（带低置信） | 低置信类 |

## 覆盖性检查

- 导入场景：8 条（IMP-001..008）
- 问答场景：4 条（RAG-001..004）
- 失败/恢复类：至少 2 条（IMP-003、IMP-007、IMP-008）
- 低置信类：至少 2 条（RAG-004 + RAG-E/F 类评测集）
