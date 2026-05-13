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

# v4.0 Phase 6 Known Limitations

## 1. 口径

本文件记录 Phase 6 当前明确接受、不能偷换表述、且必须在后续执行与评测中持续暴露的限制。

## 2. 当前限制清单

| limitation_id | limitation | user-visible symptom | classify as | default decision |
|---|---|---|---|---|
| LIM-601 | Phase 6 不会引入第二套 agent runtime | 用户不会看到一个全新的“Academic Agent”工作台 | hard boundary | 永不放宽 |
| LIM-602 | graph/global synthesis 只允许 review/survey/related work | 单点事实问答不会默认使用 graph 增强 | scope boundary | 永不放宽到主链事实路径 |
| LIM-603 | corrective retrieval 是受控单轮，不是无限多跳 | 某些低质量 query 不会被系统无限追问修复 | accepted limitation | 保持单轮预算 |
| LIM-604 | claim repair 只能提升可解释修复，不保证每次都能转成 full answer | 某些回答仍会停在 partial 或 abstain | accepted limitation | 保留 honest failure |
| LIM-605 | Phase 6 首批真源聚焦 recovery action contract，不等于所有 academic RAG 能力都已完成 | 文档和接口会先看到 recoveryActions / recovery_actions 的统一 | staged delivery | 继续分阶段推进 |
| LIM-606 | 外部框架只可吸收局部模式，不会上升为主框架 | 不会出现“仓库已迁移到某某框架”的结果 | hard boundary | 永不写成框架迁移 |
| LIM-607 | Phase 6 本身不签发 release-pass verdict | 即使某轮实验看起来更好，也不能直接写成放行 | evaluation boundary | 必须移交 Phase 7 |

## 3. 使用者须知

1. 如果结果仍然是 partial 或 abstain，不代表 Phase 6 失败，而是代表系统保留了 honest failure。
2. 如果 review 获得 graph/global synthesis 增益，也不代表 Chat 主链已经同等升级。
3. 如果 recovery action 被暴露出来，不等于所有修复都已自动完成；它首先意味着系统开始把“下一步该怎么补证据”说清楚。

## 4. 不允许的写法

1. 把 Phase 6 写成“已迁移到新框架”。
2. 把 review-only graph experiment 写成全站默认主链。
3. 把单轮 corrective retrieval 写成 multi-hop autonomous research agent。
4. 把 partial / abstain 写成“差不多等于完成”。
5. 把 Phase 6 的优化证据写成最终 release verdict。

## 5. 结论

Phase 6 的已知限制不是“以后再看”的备注，而是当前设计的一部分：它要求系统在增强 academic RAG 的同时，仍然保留边界、可回退性和可评测性。
