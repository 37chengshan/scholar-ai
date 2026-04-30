# 08 v3.0-B 执行计划：External Search + Import to KB

> 日期：2026-04-28  
> 状态：execution-plan  
> 上游研究：`docs/plans/v3_0/active/phase_b/2026-04-28_v3_0B_External_Search_Import_研究文档.md`  
> 文档前提：按“Phase A 结构性产物已完成并可复用”来组织执行，不代表仓库当前代码状态已完全完成

## 1. 目标

`Phase B` 的执行目标是把外部论文发现正式接入 ScholarAI 主链，形成：

```txt
Search
-> External results
-> Import to KB
-> ImportJob orchestration
-> metadata-only / fulltext-ready
-> Read / Chat / Notes / Compare
```

## 2. 执行前先读什么

执行者开始前，按以下顺序读取：

1. `docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md`
2. `docs/plans/v3_0/active/phase_b/2026-04-28_v3_0B_External_Search_Import_研究文档.md`
3. `docs/plans/v3_0/search/2026-04-20_SemanticScholar_arXiv_一键下载解析入库_研究报告.md`
4. `docs/plans/v3_0/active/phase_b/2026-04-28_v3_0B_kickoff_freeze.md`
5. `docs/specs/contracts/import_processing_state_machine.md`
6. `docs/specs/reference/api/前端接口列表.md`
7. `docs/specs/domain/resources.md`
8. `docs/specs/architecture/api-contract.md`

执行规则：

1. 先复用现有 Search / ImportJob / adapter 主链，再补缺口。
2. 先冻结资源语义，再补 UI 和批量体验。
3. 任何实现都不得绕开 ImportJob-first 真源。

## 3. Work Packages

## WP0：Canonical Model Freeze

目标：

1. 冻结 `ExternalPaper` 的 canonical shape
2. 冻结 `metadata_only` / `fulltext_ready` 资源语义

执行方式：

1. 以研究文档和 kickoff freeze 为准定义统一字段
2. 让 Search 结果、Import preview、KB 标记共享同一模型语义

验收：

1. 前后端不再各自维护一套外部论文字段映射。

## WP1：Search Surface Unification

目标：

1. 让 `SearchWorkspace` 成为唯一外部发现入口
2. 统一 `local_kb / arxiv / semantic_scholar / all`

执行方式：

1. 复用 `SearchWorkspace.tsx`
2. 复用 `useUnifiedSearch.ts`
3. 不新增平行 external search 页面

验收：

1. Search 中可明确区分本地与外部来源。

## WP2：Provider + Resolver Hardening

目标：

1. 把 arXiv / Semantic Scholar 统一收口到 provider / resolver 抽象
2. 明确 metadata、PDF availability、download candidate 的边界

执行方式：

1. 复用 `search/external.py`、`source_adapters/*`
2. 统一后端代理调用，不让前端直连第三方
3. 保留 arXiv 缓存与节流约束

验收：

1. provider 调用结果可归一化为统一 `ExternalPaper`。

## WP3：ImportJob-first External Import

目标：

1. 让外部导入统一走 ImportJob 真源
2. 外部导入状态与本地上传状态体系对齐

执行方式：

1. 复用 `import_job_service.py`
2. 复用 `import_dedupe_service.py`
3. 复用现有 worker 主链

验收：

1. 不存在绕开 ImportJob 的 external import 平行链路。

## WP4：Dedupe + Resource Semantics

目标：

1. 正式区分：
   - `not_imported`
   - `importing`
   - `imported_metadata_only`
   - `imported_fulltext_ready`
2. 把 dedupe 结果表达成用户可理解反馈

执行方式：

1. 继续使用 DOI / arXiv / S2 / hash / title fuzzy 顺序
2. 将 dedupe 命中类型映射到前端 badge / status / CTA

验收：

1. 用户能知道为什么一篇论文不能重复导入或只导入了 metadata。

## WP5：Async Progress + Recovery

目标：

1. 导入状态真实可观测
2. 批量导入不丢状态
3. 页面跳转后可恢复任务视图

执行方式：

1. 继续以 SSE 为主通道
2. 轮询只作为 fallback
3. 状态语义统一挂在 ImportJob 上

验收：

1. 用户能看到 queued / resolving / downloading / parsing / indexing / completed / failed。

## WP6：KB / Read / Chat 主链接入

目标：

1. 导入结果不只是“任务完成”，而是真正进入 ScholarAI 工作流

执行方式：

1. fulltext-ready 进入 KB / Read / Chat / Notes / Compare 主链
2. metadata-only 仅进入 metadata 级展示，不冒充全文可问答

验收：

1. 导入成功后，资源消费路径清晰且一致。

## 4. 实际执行顺序

执行者按以下顺序推进：

1. `WP0 Canonical Model Freeze`
2. `WP2 Provider + Resolver Hardening`
3. `WP3 ImportJob-first External Import`
4. `WP4 Dedupe + Resource Semantics`
5. `WP1 Search Surface Unification`
6. `WP5 Async Progress + Recovery`
7. `WP6 KB / Read / Chat 主链接入`

原因：

1. 不先冻结 canonical model，前后端会各写一套外部论文 shape。
2. 不先收口 provider / import 真源，UI 只是套壳。
3. 不先定义 metadata-only / fulltext-ready，后续状态会持续混乱。

## 5. Kickoff Freeze

执行者必须遵守：

1. `docs/plans/v3_0/active/phase_b/2026-04-28_v3_0B_kickoff_freeze.md`

它冻结以下执行边界：

1. 只接 `arXiv + Semantic Scholar`
2. Semantic Scholar API key 只保留在后端
3. SearchWorkspace 是唯一正式外部发现入口
4. ImportJob 是唯一正式 external import 真源
5. metadata-only 与 fulltext-ready 不得混淆

## 6. 验收标准

Phase B P0 可视为完成，当且仅当：

1. Search 中能稳定发现外部论文
2. 外部论文能一键导入指定 KB
3. 导入状态真实可见
4. metadata-only 与 fulltext-ready 被严格区分
5. fulltext-ready 论文能进入 KB / Read / Chat 主链
6. 实现没有新造平行页面或平行导入状态机

## 7. 风险

1. 若 external paper shape 不冻结，前后端会持续字段漂移
2. 若 metadata-only 语义不冻结，用户会误以为论文已可全文问答
3. 若批量导入不尊重限流，arXiv / S2 会快速退化
4. 若导入后不能进入 KB / Read / Chat，Phase B 会只剩“会搜不会用”
