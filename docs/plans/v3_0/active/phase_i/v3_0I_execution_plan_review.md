# v3.0I Execution Plan Review

> 日期：2026-04-30  
> 状态：review-ready  
> 范围：`Phase I` 按 `P0+P1` 混合完成，但第一批只落 `Truth + Route`。

## 1. 本轮完成定义

1. `P0`：冻结 taxonomy、academic kernel、claim truthfulness、adoption order 文档。
2. `P1`：把 `rag/chat/compare/review` 接到统一 route/truthfulness contract。

## 2. 明确不在本轮

1. `STORM-lite` 全局综述主链替换
2. `GraphRAG / LightRAG / OpenScholar` 实装
3. 新向量库与大规模 ORM 重构
4. 强 judge-based verifier 默认落地

## 3. 风险

1. baseline verifier 仍偏 lexical，需要后续用 `RARR/CoVe/SciFact-style` 升级
2. `global_review` 目前只做 metadata + truthfulness 接线，不等于全局 synthesis 重写
3. compare/review 历史字段仍保留，短期存在兼容层

## 4. 验收

1. routing policy 能稳定给出 `task_family + execution_mode`
2. `rag/chat` scoped retrieval 与 route 结果一致
3. `compare` 返回统一 truthfulness summary
4. `review repair` 走统一 substrate
5. 不引入数据库迁移硬依赖

## 5. Phase J Hook

本轮最小 benchmark-facing 字段固定为：

1. `task_family`
2. `execution_mode`
3. `truthfulness_report_summary`
4. `retrieval_plane_policy`
5. `degraded_conditions`
