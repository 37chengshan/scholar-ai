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

# v4.0 Phase 6 Retrieval Optimization Strategy

## 1. 目的

本文件定义 Phase 4.0-6 的 retrieval 优化顺序、允许调整的层面和明确禁止的越界动作，避免“学术 RAG 优化”被误做成第二套运行时。

## 2. 优化目标

Phase 6 的 retrieval 优化只服务现有主链：

```txt
Search / KB / Read / Chat / Compare / Review
-> stronger evidence recall
-> clearer correction trigger
-> better claim support
-> stable review-only synthesis
```

成功标准不是“回答更像人”，而是：

1. evidence recall 更稳定
2. unsupported claim 更少
3. corrective retrieval 更可解释
4. degraded path 更可见
5. Phase 7 baseline/candidate/diff 更容易证明收益

## 3. 当前可优化层

### 3.1 第一层：retrieval evaluator 与 trace

第一优先级不是换模型，而是增强当前检索结果的判断和可观测性：

1. 是否需要继续检索
2. 是否需要改写 query
3. 是否只够 partial answer
4. 是否必须进入 claim repair
5. 是否已经进入 degraded path

### 3.2 第二层：corrective retrieval

只在高价值 query family 上启用受控纠偏：

1. `compare`
2. `cross_paper`
3. `survey / related_work`
4. `conflicting_evidence`
5. `numeric / table / figure` 等高风险定位任务

原则：

1. 最多一次额外 corrective round
2. 必须写入 trace
3. 必须能回退
4. 不能静默重试到用户看不见

### 3.3 第三层：hierarchical retrieval

对长文和综述任务优先做分层 retrieval，而不是所有请求都走重型 multi-hop：

1. paper-level summary retrieval
2. section-level narrowing
3. chunk-level grounding

适用范围：

1. review draft
2. long paper method / ablation / appendix
3. compare matrix 长段落支撑

### 3.4 第四层：review-only global synthesis

graph / global synthesis 只允许进入：

1. Review
2. Survey
3. Related Work

禁止进入：

1. fact-level QA
2. numeric QA
3. table / figure citation grounding

## 4. 推荐实施顺序

### P0：先补观测与动作合同

1. 统一 recovery action 语义
2. 统一 retrieval correction 的 trace 字段
3. 明确 degraded / fallback 暴露规则

### P1：接入 CRAG-lite corrective retrieval

1. retrieval confidence judgement
2. rewrite / retry / expand scope
3. 单次 corrective round

### P2：升级 claim repair

1. unsupported claim 定位
2. citation repair
3. partial / abstain 语义稳定

### P3：分层 retrieval 与 review-only synthesis

1. long-doc hierarchical retrieval
2. review-only graph/global experiment
3. 与 Phase 7 handoff 对齐

## 5. 明确不做

1. 不训练 Self-RAG 同款模型
2. 不把外部框架升级为主运行时
3. 不引入第二套 agent runtime
4. 不对所有 query 默认启用多跳循环
5. 不让 graph/global synthesis 接管事实主链

## 6. 产出要求

每轮优化至少要留下：

1. 变更前后行为差异说明
2. retrieval trace 或等效运行证据
3. 对 unsupported claim / recovery action 的影响说明
4. 与 Phase 7 指标的预期对应关系

## 7. 结论

Phase 6 的 retrieval strategy 不是“换框架”，而是按「观测先行、纠偏受控、分层增强、综述实验受限」的顺序扩展当前 kernel。