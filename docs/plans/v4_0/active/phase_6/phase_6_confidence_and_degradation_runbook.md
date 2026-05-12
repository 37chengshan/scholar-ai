---
owner: ai-runtime
status: asset-ready
depends_on:
  - 2026-05-11_v4_0_phase_6_academic_rag_optimization_research
  - 24_v4_0_phase_6_execution_plan
last_verified_at: 2026-05-12
evidence_commits:
  - working-tree-v4-0-phase-6-doc-restore
---

# v4.0 Phase 6 Confidence And Degradation Runbook

## 1. 目的

本文件定义 Phase 6 对“当前证据够不够”“系统是否已降级”“用户下一步该做什么”的统一解释规则。

## 2. Confidence 分层口径

Phase 6 不要求立刻引入单一分数字段，但要求所有主链结果都能落到以下三层语义之一：

| level | meaning | default behavior |
|---|---|---|
| `high-confidence` | 证据足以支持当前回答或段落 | 允许生成，但仍保留 claim verification |
| `medium-confidence` | 有一定证据，但存在缺口或不完整支撑 | 输出 partial，并暴露 corrective / repair action |
| `low-confidence` | 当前证据不足，继续生成风险高 | abstain 或进入明确恢复动作 |

## 3. 必须显式暴露的 degraded 信号

Phase 6 任何一条主链只要出现以下情况，就必须暴露 degraded state：

1. retrieval recall 明显不足
2. 进入 corrective retrieval
3. graph/global synthesis 不可用并 fallback
4. claim verification 失败
5. citation repair 失败
6. latency / cost 已经超过当前合理预算

## 4. 用户可见语义

### 4.1 允许直接回答

适用于：

1. evidence 足够
2. citation 完整
3. claim verification 没有明显 unsupported rows

### 4.2 partial

适用于：

1. evidence 只支持部分回答
2. 某些 claim 仍需 repair
3. review / compare 可展示草稿，但不能伪装成 fully grounded

要求：

1. 必须带恢复动作
2. 必须暴露不足原因

### 4.3 abstain

适用于：

1. 当前 evidence 明显不足
2. corrective retrieval 后仍无法形成可信支撑
3. claim repair 失败且继续生成会误导用户

要求：

1. 必须提供下一步恢复入口
2. 不能只返回模糊文案

## 5. Recovery 动作最低集合

Phase 6 的结果至少要能表达以下动作中的一部分：

1. continue retrieval
2. rewrite query
3. expand scope
4. verify claim
5. repair citation
6. repair claim
7. fallback to local-only
8. open recovery entry

## 6. Degradation 记录规则

每次 degraded path 都必须能回答：

1. 为什么触发
2. 触发了哪种动作
3. 是否恢复成功
4. 如果失败，用户下一步去哪

## 7. 不允许的写法

1. 把 partial 写成正常完成
2. 把 fallback 写成透明成功
3. 把 graph unavailable 隐藏在最终文案里
4. 在 Chat、Compare、Review 三条链上使用不同的 degraded 口径

## 8. 结论

Phase 6 的 confidence / degradation 目标不是更复杂，而是更一致、更显式、更能让用户和 Phase 7 gate 同时消费。