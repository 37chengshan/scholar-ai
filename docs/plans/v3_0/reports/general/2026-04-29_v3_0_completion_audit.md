# 2026-04-29 v3.0 完成度审查报告

## 1. 结论

结论：**v3.0 当前不能判定为完成**。

更准确地说：

1. `Phase A` 已有较强落地证据，接近“结构性完成”。
2. `Phase B / C / FR` 已进入真实实现阶段，但仍属于“部分完成 + 局部验证通过”。
3. `Phase D` 明确未完成，且当前正式报告已给出 `beta_readiness: not_ready`。
4. `Phase E / F / G` 仍停留在总览规划层，未见对应 active 执行计划与完成证据。
5. 当前工作区还存在治理门禁未过的问题，因此不能作为完整 close-out。

## 2. 本次审查依据

本次审查交叉使用以下真源：

1. `docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md`
2. `docs/plans/PLAN_STATUS.md`
3. `docs/specs/governance/phase-delivery-ledger.md`
4. `docs/plans/v3_0/active/phase_a/` `phase_b/` `phase_c/` `phase_d/` `phase_fr/`
5. `artifacts/validation-results/phase_d/real_world_validation.json`
6. `artifacts/validation-results/phase_d/real_world_validation.summary.json`
7. 当前未提交代码改动与本地治理/类型检查结果

## 3. 总体判断矩阵

| Phase | 当前判断 | 依据 |
|---|---|---|
| A Academic Benchmark 3.0 | 基本落地，但台账仍未收口 | 已有 `v3_0_academic` corpus / blind / runs；但计划台账仍是 `in-progress` |
| B External Search + Import to KB | 部分完成 | 真实链路已至少跑通 `search -> import -> kb -> read` 一次，但未形成 P0 完成证据 |
| C Span Citation + Claim Verification | 部分完成 | 契约、后端字段、UI 支撑与 repair 路径已出现，但缺少真实世界验证闭环 |
| D Real-world Validation | 未完成 | 正式报告只有 `2` 个 run、`0` 个 full-chain run，且 `beta_readiness: not_ready` |
| FR Frontend Reliability Refactor | 大体实现，但治理未收口 | legacy bridge 删除、虚拟化、偏好持久化已落地；`legacy-freeze` 仍失败 |
| E Reliability / Data / Cost / Speed | 未开始为独立 phase | 总览里有 phase，未见 active 执行计划/台账条目 |
| F Frontend Productization Polish | 未开始为独立 phase | 总览里有 phase，当前只有 FR 作为前置切片 |
| G Public Beta / Demo Release | 未开始 | Phase D 仍 `not_ready`，无 beta close-out 证据 |

## 4. 关键证据

### 4.1 计划台账层面，v3.0 仍被官方标记为进行中

`docs/plans/PLAN_STATUS.md` 中：

1. `06_v3_0_overview_plan` 状态仍是 `in-progress`
2. `v3_0A`、`07_v3_0A_execution_plan`、`v3_0B`、`08_v3_0B_execution_plan`、`v3_0C`、`09_v3_0C_execution_plan`、`v3_0D`、`10_v3_0D_execution_plan` 全部仍是 `in-progress`

`docs/specs/governance/phase-delivery-ledger.md` 也明确写了：

1. `V3.0-A` 待补“实现 PR、数据构建证据与 gate 跑数”
2. `V3.0-B` 待补“SearchWorkspace 主入口、ImportJob-first 主链、dedupe 用户可见反馈与 async progress 实装证据”
3. `V3.0-C` 待补“claim locator / repair loop / UI 与后端统一实施证据”
4. `V3.0-D` 待补“sample registry、failure bucket spec、workflow run 记录格式与 close-out 报告执行证据”

这说明从仓库自己的 phase 治理口径来看，v3.0 还没有被回填到完成态。

### 4.2 Phase A 已有实物，不是空计划

`apps/api/artifacts/benchmarks/v3_0_academic/` 下已存在：

1. `corpus_public.json`
2. `corpus_blind.json`
3. `manifest.json`
4. `runs/run_v3_academic_baseline_001/`
5. `runs/run_v3_academic_candidate_001/`

抽样核对结果：

1. `corpus_public.json`: `paper_count = 200`, `query_count = 688`
2. `corpus_blind.json`: `paper_count = 200`, `query_count = 688`
3. 两个 run 目录均包含 `meta.json / retrieval.json / evidence.json / answer_quality.json / abstain_quality.json / family_breakdown.json / domain_breakdown.json / dashboard_summary.json / diff_from_baseline.json`

这说明 `Phase A` 的 schema、public/blind 双层结构、baseline/candidate/diff 主链已经具备较完整骨架。

但问题在于：台账没有把它正式回填成 done，本轮也没有跑出新的 gate 证据，因此我只能给出“接近结构性完成”，不能直接判定 Phase A 完成收口。

### 4.3 Phase B 已经落到真实代码，但 P0 闭环证据仍不够

代码与文档层面已看到：

1. 前端存在统一 external search / import 能力：
   - `apps/web/src/services/searchApi.ts`
   - `apps/web/src/features/search/hooks/useSearchImportFlow.ts`
   - `apps/web/src/features/search/components/SearchWorkspace.tsx`
2. 后端存在统一 external/import 路径：
   - `apps/api/app/api/search/external.py`
   - `apps/api/app/api/search/library.py`
   - `apps/api/app/services/import_job_service.py`
   - `apps/api/app/services/import_dedupe_service.py`
   - `apps/api/app/workers/import_worker.py`
3. 契约已引入 `libraryStatus = not_imported | importing | imported_metadata_only | imported_fulltext_ready`

真实验证层面：

1. `artifacts/validation-results/phase_d/real_world_validation.json` 的 `RW-002` 已记录 `search -> import -> kb -> read` 真链通过
2. 但 `RW-001` 也同时记录了搜索 30s+、KB 选择模态框阻断、evidence sidecar 500

因此 `Phase B` 不是未开始，而是“已实现到可跑通局部主链，但还没有达到执行计划里的 P0 完成态”。

### 4.4 Phase C 已经有契约与 UI 落地，但真实验证证据不足

已落地证据包括：

1. 后端 claim/evidence contract：
   - `apps/api/app/core/claim_schema.py`
   - `apps/api/app/services/evidence_contract_service.py`
   - `apps/api/app/services/review_draft_service.py`
2. 类型与 SDK：
   - `packages/types/src/chat/contracts.ts`
   - `packages/types/src/evidence/dto.ts`
   - `packages/types/src/kb/review.ts`
   - `packages/sdk/src/kb/review.ts`
3. 前端展示与 repair/跳转消费：
   - `apps/web/src/features/chat/hooks/useChatSend.ts`
   - `apps/web/src/features/chat/components/evidence/ClaimSupportList.tsx`
   - `apps/web/src/features/kb/components/KnowledgeReviewPanel.tsx`
   - `apps/web/src/app/pages/Read.tsx`

说明：

1. `quote_text`
2. `source_chunk_id`
3. `source_offset_start/source_offset_end`
4. `citation_jump_url`
5. `supported / weakly_supported / unsupported`
6. `repair_claim`

这些关键对象都已经进入真实代码。

但 `Phase D` 的正式结果中：

1. `total_reviews = 0`
2. `unsupported_claim_count = 0`
3. `weakly_supported_claim_count = 0`
4. `full_chain_runs = 0`

也就是说，`Phase C` 的真实世界验证闭环目前并没有形成足够证据。它更像是“实现已出现，但验收未完成”。

### 4.5 Phase D 明确未完成，而且仓库自己已经给出否定结论

`docs/reports/v3_0_real_world_validation.md` 与 `artifacts/validation-results/phase_d/real_world_validation.summary.json` 一致表明：

1. `total_samples = 8`
2. `total_runs = 2`
3. `full_chain_runs = 0`
4. `total_failures = 3`
5. `blocking = 1`
6. `beta_readiness = not_ready`

而 `docs/plans/v3_0/active/phase_d/v3_0D_sample_registry.md` 的 P0 目标明确要求：

1. 总样本数 `100-300`
2. 完整 workflow run 数 `>=20`
3. 八类高风险样本持续覆盖

当前实际值与目标值差距很大，所以 `Phase D` 不能被视为完成。

### 4.6 FR 已有明显代码落地，但收口不完整

我核对到以下 FR 目标已经实际出现：

1. legacy bridge 文件已不在正式源码路径中：
   - 未再发现 `apps/web/src/features/chat/components/ChatLegacy.tsx`
   - 未再发现 `apps/web/src/features/kb/components/KnowledgeBaseDetailLegacy.tsx`
2. KB 论文列表已加入虚拟化：
   - `apps/web/src/features/kb/components/KnowledgePapersPanel.tsx`
   - 使用 `react-window`，阈值 `papers.length >= 40`
3. `Read` 偏好已进入持久化 store：
   - `apps/web/src/features/read/state/readPreferencesStore.ts`
   - `apps/web/src/app/pages/Read.tsx`
4. `Notes` 偏好已进入持久化 store：
   - `apps/web/src/features/notes/state/notesPreferencesStore.ts`
   - `apps/web/src/app/pages/Notes.tsx`

前端本地验证里，`cd apps/web && npm run type-check` 已通过。

但 FR 仍有两个收口问题：

1. `bash scripts/check-legacy-freeze.sh` 失败，原因是相关提交缺少 `Migration-Task:` marker
2. `bash scripts/check-governance.sh` 因 `legacy-freeze` 同样失败

因此 FR 更接近“代码切片已基本落地，但治理闭环未完成”。

### 4.7 存在一个会误导判断的陈旧结论文件

`output/v3_FINAL_SUBMISSION_REPORT.md` 写的是：

1. 生成时间 `2026-04-26`
2. 多处宣称 `100% COMPLETE`
3. 面向的是更早的一轮 `v3 PR` close-out 语境

但当前真正的 v3.0 总览计划是 `2026-04-28` 才建立，且计划台账、Phase D 报告、治理门禁都还没有收口。

所以这个文件**不能作为当前 v3.0 是否完成的证据**，最多只能视为更早一轮阶段成果总结。

## 5. 本地验证结果

### 已通过

1. `cd apps/web && npm run type-check`
2. `bash scripts/check-doc-governance.sh`
3. `bash scripts/check-structure-boundaries.sh`
4. `bash scripts/check-phase-tracking.sh`

### 未通过

1. `bash scripts/check-code-boundaries.sh`
   - 报错：`apps/api/app/api/search/library.py` 出现 `backend API direct DB access not in baseline`
2. `bash scripts/check-legacy-freeze.sh`
   - 报错：legacy 组件相关提交缺少 `Migration-Task:` marker
3. `bash scripts/check-governance.sh`
   - 因 `legacy-freeze` 失败而整体失败

### 未完成

1. 后端 `pytest`

说明：

1. 仓库要求 `Python 3.11+`
2. 默认 `python3` 指向 `3.9.6`，直接运行会因解释器不匹配报错
3. `python3.11` 可用，但当前环境未安装测试依赖，执行时缺少 `httpx`

所以本次后端单测结论应记为：**当前本机环境下未完成验收，不应当作通过**。

## 6. 对“v3.0 是否完成”的最终判定

我的最终判定是：

1. **不能判定 v3.0 已完成**
2. **不能判定当前分支已达到 Public Beta / Demo Release**
3. **可以判定 v3.0 已有大量实质进展，尤其是 A、B、C、FR 均非空计划**

换句话说，当前状态更像：

```txt
v3.0 = 已进入中后段实施
但仍未完成真实世界闭环验证
也未完成治理与发布收口
```

## 7. 距离“可完成”还差什么

按影响优先级排序，最关键缺口是：

1. 完成 `Phase D` 的真实链路验证，把 `full_chain_runs` 从 `0` 提升到符合 P0 目标的规模
2. 修掉当前已知阻断项：
   - KB 选择模态框不稳定
   - search evidence sidecar 500
   - `apps/api/app/api/search/library.py` 的 code-boundary 违规
3. 补齐 `legacy-freeze` 所要求的 `Migration-Task:` 治理证据
4. 在可用的 `Python 3.11 + requirements` 环境下跑完后端测试
5. 为 `Phase E / F / G` 建立独立执行计划和完成证据，不能只停留在总览

## 8. 建议的 close-out 口径

如果现在要对外或对内汇报，建议使用以下口径，而不是“v3.0 已完成”：

> v3.0 已完成 Academic Benchmark、External Search/Import、Claim Verification、Frontend Reliability 的核心实现推进，但 Real-world Validation、治理门禁和 Public Beta 收口尚未完成，当前状态应定义为“v3.0 实施中后段，未达到最终完成态”。
