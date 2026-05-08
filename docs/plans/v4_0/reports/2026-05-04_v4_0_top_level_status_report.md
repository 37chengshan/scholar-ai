# v4.0 Top-level Status Report

> 日期：2026-05-04  
> scope: `v4.0 phases 0-7`  
> status: `phase-0-to-2 verified; phase-3-to-7 pending`

## 1. Executive Summary

v4.0 当前已经完成并有 repo 内证据支撑的部分，是 Phase 0、Phase 1、Phase 2。

截至 2026-05-04：

1. Phase 0: `closeout-complete / readiness-conditional`
2. Phase 1: `closeout-complete / first-wave-shipped`
3. Phase 2: `walkthrough-complete / demo-ready`

Phase 3-7 仍然是后续阶段，不应被提前写成已完成。

## 2. Current Product Truth

当前产品真相不是“所有事都做完了”，而是：

1. A 主线 workflow continuity 已经建立
2. C 主线 beta hardening 已经拿到 demo-ready
3. phase2 主链模型已经收口到线上模型，不再默认走本地 embedding / rerank 双路径

当前在线模型格局：

1. generation: GLM 在线推理
2. embedding: DashScope `text-embedding-v4`
3. rerank: DashScope `qwen3-rerank`

这意味着 v4.0 的后续优化应围绕真实 online mainline 做稳定化与评测，而不是继续维护本地并行主链。

## 3. Phase-by-phase Status

| phase | current truth | note |
|---|---|---|
| 0 | closeout-complete / readiness-conditional | 负责把 v4.0 真源、边界和 gate 建起来 |
| 1 | closeout-complete / first-wave-shipped | workflow continuity 已落地 |
| 2 | walkthrough-complete / demo-ready | beta hardening、online mainline、browser walkthrough 已完成 |
| 3 | direction-confirmed / plan-required | citation-backed review artifacts 仍待正式执行 |
| 4 | direction-confirmed / plan-required | 前端视觉与展示质量打磨待开始 |
| 5 | direction-confirmed / plan-required | 前端交互、响应式与可访问性打磨待开始 |
| 6 | direction-confirmed / plan-required | Academic RAG optimization 应建立在 online mainline 上 |
| 7 | direction-confirmed / plan-required | testing / evaluation gate 仍未给 release verdict |

## 4. What Changed In This Closeout

相对于 Phase 2 进入前，本轮顶层变化是：

1. KB import/search 的 backend 主链改为真实 online embedding/rerank
2. Milvus 与 SQL chunk truth 对齐，不再出现 `0 Chunks / Pending index` 的假状态
3. Compare / Review / KB Chat / Read / Notes 都有浏览器侧实证
4. Compare 页面 warm-auth / URL 预选竞态被修复，支持 URL 预选论文直接生成矩阵
5. Read -> single-paper Chat handoff 与 paper-scoped retrieval 已恢复，单论文问答不再停在假性 abstain
6. Phase 2 不再停留在资产准备态，而是拿到了真实 walkthrough 证据

## 5. Residual Risk

v4.0 现在最大的剩余风险，不在“主链完全不可用”，而在：

1. single-paper Chat 已恢复，但当前仍可能输出 `partial` 而不是稳定 `full`
2. Review 仍会出现 `partial / insufficient_evidence`
3. KB deep-link 到特定 tab 的鉴权回落问题还没收口
4. controlled beta 还没有扩大到独立操作者与 staging/cloud
5. v4.0 后半段前端质量与 testing/eval gate 还没开始收口

所以当前最准确的上层说法是：

- 可以演示
- 可以继续推进后续 phase
- 不能写成 release-pass

## 6. Recommended Next Order

1. Phase 3: 把 Review artifacts 做成更稳定、可消费的 citation-backed 交付面
2. Phase 4-5: 在不重做 IA 的前提下，把前端质感、展示质量、状态表达和交互细节做完
3. Phase 6: 只在 online mainline 上做 retrieval / evidence / latency 优化
4. Phase 7: 做真正的 testing / evaluation gate，决定是否能从 `demo-ready` 升到更高一级
