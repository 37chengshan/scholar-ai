---
owner: product-engineering
status: baseline-frozen
last_verified_at: 2026-05-31
scope:
  - apps/web (frontend source, dependencies, routing)
  - apps/api (python source, tests, services)
  - docs/specs (governance, architecture, contract)
  - scripts/check-* (governance gates)
upstream_reports:
  - docs/plans/v4_5/reports/2026-05-26_v4_5_frontend_backend_multidimensional_audit.md
  - docs/plans/v4_5/reports/2026-05-27_v4_5_rag_drift_recheck.md
  - docs/plans/v5_0/active/phase_0/v5_0_perf_baseline_snapshot.md
  - docs/plans/v5_0/active/phase_0/v5_0_gate_input_matrix.md
---

# 2026-05-31 v5.0 Phase 0 Audit Baseline

> 本文件是 v5.0 版本启动时的多维审计基线。它不是新的代码审查，而是把 v4.5 多维审计结论
> (2026-05-26) + v4.5 RAG drift recheck 结论 (2026-05-27) + v5.0 perf baseline snapshot
> 合并为一份"v5.0 起点真相"。后续 phase 5.0-9 release gate 的二轮 audit 以本文件为对比基准。

---

## 1. Executive Verdict

截至 2026-05-31，v5.0 起点状态为：

v4.5 多维审计 (2026-05-26) 列出的全部 P1 项已修闭环；v4.5 RAG drift recheck (2026-05-27)
确认 4 个 current drift 红点全部消除。前端 `npm run type-check` 通过，后端 targeted pytest
通过，治理 gate (tracked / doc / structure / code / governance) 通过。

当前仍有以下结构性差距需要 v5.0 各 phase 解决：

1. 前端 Read 页 0 test、Compare 页 0 test、Notes 页仅 2 test。
2. E2E 14 个 spec 覆盖了 chat/kb/search/notes/compare/user-journey，但 Read 与 Upload 零覆盖。
3. Vite 配置零 build 期优化：无 manualChunks、无 visualizer、无 bundle budget。
4. 设计 token 仅 39 个 CSS vars，不足支撑完整设计系统。
5. Upload features 完整但 `apps/web/src/app/pages/` 无路由。

本报告不宣称 release-pass 或 release-candidate，只记录起点状态。

---

## 2. Audit Dimensions

### Dim A: Frontend (apps/web)

来源：v4.5 audit 第 4.5 节 + perf baseline snapshot 第 2 节。

| 项 | 当前状态 | 负责 phase | 备注 |
|---|---|---|---|
| P1-FE-001 SSE done payload 丢失 trace_id/run_id/compare_matrix | **已修** (v4.5 closeout) | -- | -- |
| P1-FE-002 SearchAuthorPanel 未传 s2PaperId | **已修** (v4.5 closeout) | -- | -- |
| P1-FE-003 KB import polling 漏 queued | **已修** (v4.5 closeout) | -- | -- |
| P1-FE-004 WorkspaceShell 窄屏不可用 | **已修** (v4.5 closeout) | -- | Radix Dialog + 断点 stack |
| Read 页 0 vitest | 待补 | 5.0-4 | 至少 6 component test + 1 E2E spec |
| Compare 页 0 vitest | 待补 | 5.0-6 | -- |
| Notes 页仅 2 vitest | 待补 | 5.0-5 | -- |
| Upload 页面无路由 | 待补 | 5.0-3 | features/uploads 已就绪 |
| Design token 仅 39 CSS vars | 待补 | 5.0-1 | 扩至 ~200 tokens |
| `npm run type-check` | **通过** | -- | -- |

### Dim B: Backend API/Service (apps/api)

来源：v4.5 audit 第 4.1-4.2 节。

| 项 | 当前状态 | 负责 phase | 备注 |
|---|---|---|---|
| P1-AUTH-001 chat/cancel 无 session ownership 校验 | **已修** (v4.5 closeout) | -- | -- |
| P1-AUTH-002 chat/retry 在鉴权前读取消息 | **已修** (v4.5 closeout) | -- | -- |
| P1-AUTH-003 notes generate/regenerate/export 无 user_id 约束 | **已修** (v4.5 closeout) | -- | -- |
| P1-AUTH-004 evidence note chunk 查询未 join user_id | **已修** (v4.5 closeout) | -- | -- |
| P1-AUTH-005 artifact fallback 无 paper ownership 校验 | **已修** (v4.5 closeout) | -- | -- |
| P1-TASK-001 local upload 缺 os import | **已修** (v4.5 closeout) | -- | -- |
| P1-TASK-002 chunked upload 缺 PDF magic bytes 校验 | **已修** (v4.5 closeout) | -- | -- |
| P1-TASK-003 batch import 不调用 process_import_job.delay | **已修** (v4.5 closeout) | -- | -- |
| P1-TASK-004 retry route 不 enqueue worker | **已修** (v4.5 closeout) | -- | -- |
| P1-TASK-005 _sync_import_job_stage 未传给 coordinator | **已修** (v4.5 closeout) | -- | -- |
| P2-CONTRACT-001 Semantic Scholar source 混用 s2 | **已修** (v4.5 closeout) | -- | canonical `semantic_scholar` |
| P2-CONTRACT-002 Axios interceptor 丢顶层 meta | **已修** (v4.5 closeout) | -- | -- |
| P2-CONTRACT-003 /search/unified 缺 source/meta | **已修** (v4.5 closeout) | -- | -- |
| P2-CONTRACT-004 /search/evidence 返回 raw object | **已修** (v4.5 closeout) | -- | -- |
| P2-CONTRACT-005 star route / batch delete 契约不一致 | **已修** (v4.5 closeout) | -- | -- |
| P2-UX-001 自制 modal 缺 focus trap/ESC | **已修** (v4.5 closeout) | -- | Radix Dialog |
| Auth/Observability 残端加固 | 待处理 | 5.0-7 | trace_id/run_id 贯通率 |
| pytest 测试文件 237 | 基线记录 | -- | 远高于前端 94 |

### Dim C: Backend Data/Reliability (apps/api)

来源：v4.5 audit 第 4.3 节。

| 项 | 当前状态 | 负责 phase | 备注 |
|---|---|---|---|
| P1-DATA-001 Milvus insert 失败后仍标成功 | **已修** (v4.5 closeout) | -- | strict/fail-closed |
| P1-DATA-002 reindex/delete 不清 Milvus 向量 | **已修** (v4.5 closeout) | -- | 按 paper_id 清理四类向量 |
| P1-DATA-003 dimension mismatch 自动 drop collection | **已修** (v4.5 closeout) | -- | fail-fast |
| P1-DATA-004 /rag/query 未走 shared AnswerContract | **已修** (v4.5 closeout) | -- | legacy adapter 兼容 |
| P1-SCHEMA-001 isSearchReady 列名漂移 | **已修** (v4.5 closeout) | -- | -- |
| P1-SCHEMA-002 review_drafts/review_runs 无 Alembic migration | **已修** (v4.5 closeout) | -- | migration 015 |
| P2-TASK-001 temp PDF 无 cleanup | **已修** (v4.5 closeout) | -- | finally unlink |
| P2-TASK-002 cancel 不 revoke worker | **已修** (v4.5 closeout) | -- | coordinator 阶段闸门 |
| Pipeline 可视化后端就绪但前端断链 | 待处理 | 5.0-3 | imports/events.py + progress API 已实现 |
| test_answer_contract runtime warning | 残留 | 5.0-7 | 既有 warning，非新引入 |

### Dim D: Governance

来源：v4.5 audit 第 4.6 节 + perf baseline snapshot 第 6 节。

| 项 | 当前状态 | 负责 phase | 备注 |
|---|---|---|---|
| P1-GOV-001 data/ 未 ignore 不在 hygiene gate | **已修** (v4.5 closeout) | -- | -- |
| P1-GOV-002 WORKFLOW/Symphony 架构真源不一致 | **已修** (v4.5 closeout) | -- | 统一声明为本地编排覆盖层 |
| P2-GOV-001 testing strategy / CI workflow 不一致 | **已修** (v4.5 closeout) | -- | Node 20/22 偏差已消除 |
| 10 个 check-*.sh 脚本 | 全部存在 | -- | -- |
| Lighthouse CI 集成 | **缺失** | 5.0-2 | -- |
| Bundle visualizer 集成 | **缺失** | 5.0-2 | -- |
| run_v5_release_gate.py | **已创建** (phase_0) | -- | 从 v4 phase7 gate 升级 |

### Dim E: Performance (NEW)

来源：`v5_0_perf_baseline_snapshot.md` (2026-05-31)。本维度为 v5.0 新增。

| 项 | 当前基线 | v5.0 目标 | 负责 phase | 备注 |
|---|---|---|---|---|
| LCP (Landing) | **> 3.0 s** (预估) | < 2.5 s | 5.0-2 | Google Fonts @import 阻塞 |
| LCP (Chat) | **> 3.5 s** (预估) | < 2.5 s | 5.0-2 | Chat 536KB 一次进入 |
| LCP (Read) | **> 4.5 s** (预估) | < 2.5 s | 5.0-2 | pdfjs-dist 进入首屏 |
| INP (Chat SSE) | **> 250 ms** (预估) | < 200 ms | 5.0-2 | 无 virtualization |
| CLS (Chat SSE) | **0.1 ~ 0.3** (预估) | < 0.05 | 5.0-4 | 流式 layout shift |
| FCP | **> 2.0 s** (预估) | < 1.5 s | 5.0-2 | -- |
| TBT | **> 300 ms** (预估) | < 200 ms | 5.0-2 | -- |
| pdfjs-dist npm 体积 | **36 MB** | dynamic import 隔到 Read | 5.0-2 | 最大性能风险 |
| @tiptap/* npm 体积 | **6.9 MB** | 按需加载隔到 Notes | 5.0-2 | -- |
| Vite manualChunks | **无** | feature 分包 | 5.0-2 | -- |
| rollup-plugin-visualizer | **无** | 接入 | 5.0-2 | -- |
| Lighthouse CI | **无** | 接入门禁 | 5.0-2 | -- |
| 总依赖数 | **104** (87+17) | -- | -- | 基线记录 |
| Chat feature 源码 | **536 KB** / 59 文件 | -- | 5.0-6 | 全主链最重 |
| src 总大小 | **3.2 MB** | -- | -- | 基线记录 |

注：以上 CWV 数值为静态推估值（未跑 Lighthouse），phase 5.0-2 必须做一次真实 Lighthouse
测量验证。详见 perf baseline snapshot 第 4 节。

### Dim F: RAG Contract (已修复)

来源：`2026-05-27_v4_5_rag_drift_recheck.md`。

v4.5 RAG drift recheck 结论：2026-05-13 报告中列为 `current_contract_or_behavior_drift`
的 4 个红点，按当前代码和当前测试已不再成立。

| 原红点 | 原 reading | 当前状态 | 更新 reading |
|---|---|---|---|
| test_prune_unsupported_claims_appends_notice_when_support_low | verifier 输出 contract 有差异 | 2026-05-27 复跑通过 | 已收口，不再属于 current drift |
| test_retrieve_evidence_contract | live retrieval 返回 0 candidates | 测试已改为 deterministic current-contract coverage | 旧失败根因是 stale helper/test path，不再属于 current drift |
| test_evidence_quality_and_answer_policy | answer_mode 有差异 | 2026-05-27 复跑通过 | 已收口，不再属于 current drift |
| test_pagerank_calculation_e2e | graph pagerank 断言不一致 | 2026-05-27 复跑通过 | 已收口，不再属于 current drift |

v5.0 runtime contract freeze 已继承 v4.5 contract 全量字段，并新增 RAPTOR-lite / Graph synthesis /
Verifier fusion / perf 四个预留区。详见 `v5_0_runtime_contract_freeze.md`。

---

## 3. P1 Residual Table

v4.5 audit (2026-05-26) 共 22 项 P1，全部已修闭环。v4.5 closeout 修复的 16 项 P1 + P2
全部有定向测试覆盖。详见 v4.5 audit 第 4 节 closeout update。

---

## 4. RAG Drift Status

截至 2026-05-27，v4.5 RAG drift recheck 确认：

- 2026-05-13 报告中 4 个 `current_contract_or_behavior_drift` 红点**全部消除**
- 4/4 测试在当前代码树下稳定通过
- 不再把这 4 个点计入 `current_contract_or_behavior_drift`

仍不能宣称的状态：
1. `release-pass`
2. `full rag automation green`
3. `all historical rag tests are aligned with current architecture`

v5.0 Phase 5.0-8 将在 RAPTOR-lite / Graph synthesis / Verifier fusion 落地后做新一轮 RAG 深度验证。

---

## 5. v5.0 迁出清单

来源：overview plan 第 3 节。v4.0 phase_3/5/7 在 `PLAN_STATUS.md` 已标为 `superseded`。

| v4.x 来源 | v5.0 迁入目标 | 处置 |
|---|---|---|
| v4.0 phase_3 (artifact contract) | 5.0-5 + 5.0-6 | superseded |
| v4.0 phase_5 (interaction quality) | 5.0-1 + 5.0-2 | superseded |
| v4.0 phase_7 (testing & evaluation gate) | 5.0-9 | gate runner 升级 |
| v4.5 bridge phase_0 | 已 closeout | done |

---

## 6. Baseline Metrics (从 perf baseline snapshot 摘录)

| 指标 | 值 |
|---|---|
| src 总大小 | 3.2 MB |
| Chat feature (最重) | 536 KB / 59 文件 (占 17%) |
| pdfjs-dist | 36 MB (高风险：进入首屏路径) |
| @tiptap/* | 6.9 MB (中风险：未按需加载) |
| @radix-ui/* | 3.9 MB |
| 总依赖数 | 104 (87 + 17 dev) |
| pytest 测试文件 | 237 |
| vitest 测试文件 | 94 |
| Playwright E2E spec | 14 |
| React.lazy() 路由 | 8 个 |
| manualChunks / visualizer / font preload | 均无 |
| 设计 CSS token | 39 vars |

完整 feature 体积表与依赖分析见 `v5_0_perf_baseline_snapshot.md` 第 2-3 节。

---

## 7. 不在本 Baseline 范围

1. Live Lighthouse 实测（phase 5.0-2 deliverable）
2. Real User Metrics (RUM) 数据（无 RUM 接入）
3. 后端 latency p50/p95 全链路测量（phase 5.0-7 deliverable）
4. 移动端 perf baseline（v5.0 不做移动端专项）
5. Network throttling 下的测量（phase 5.0-9 release gate 含）
6. Playwright E2E walkthrough（phase 5.0-9 deliverable）
7. RAPTOR-lite / Graph synthesis / Verifier fusion 实现（phase 5.0-8 deliverable）
8. 主观 UX 评分 / 设计美感评审（非机器可量化）
9. 任何 apps/web 或 apps/api 业务代码改动（phase 5.0-0 不动业务代码）

---

## 8. Next Phase 预告 (Phase 5.0-1 启动条件)

phase 5.0-1 (设计系统 v2 + 杂志编辑风深化 + 反模板视觉) 可在以下条件满足后启动：

1. **本文件已存在且 status: baseline-frozen** -- 当前文件
2. `v5_0_runtime_contract_freeze.md` 已存在且 status: frozen
3. `v5_0_gate_input_matrix.md` 已存在且五个输入面定义完整
4. `scripts/evals/run_v5_release_gate.py` 已存在且 --help 可运行
5. `docs/specs/governance/phase-delivery-ledger.md` 中 phase 5.0-0 条目已回填为 done
6. `PLAN_STATUS.md` 中 v4.0 phase_3/5/7 已标 superseded

phase 5.0-1 不改主链页面布局，只建立 CSS token 体系、typography stack、color palette、
motion system 和 anti-template 视觉策略。

---

## 9. Governance KPI Baseline

KPI 定义见 `docs/specs/governance/governance-kpi-spec.md`（6 项指标：phase_coverage_rate、
planning_delivery_rate、fallback_expired_active、fallback_active_days_avg、
e2e_gate_pass_rate、post_merge_48h_incident_rate）。当前均为基线记录状态，
将在 phase 5.0-9 release gate 时做正式测量。

---

## 10. Baseline 失效条件

下列动作触发本 baseline 自动失效，必须重新跑：

1. `apps/web/vite.config.ts` 出现 manualChunks 或 rollupOptions 改动
2. 引入新的大依赖 (>500KB raw)
3. 任何 phase closeout 后，5.0-2 必须重测一次 perf baseline
4. 5.0-9 release gate 必须包含一次完整 baseline 复测对比
5. v5.0 runtime contract freeze 字段发生非预留性变更

---

## 11. 自审

| 维度 | 结论 | 说明 |
|---|---|---|
| 来源引用 | pass | 全部数据来自指定上游报告，未新增未核实问题 |
| P1 owner 覆盖 | pass | 所有待处理项均标注负责 phase |
| release 声明边界 | pass | 明确不宣称 release-pass 或 release-candidate |
| 维度覆盖 | pass | 涵盖 Frontend / Backend API / Data / Governance / Performance / RAG 六维 |
| 上游报告一致性 | pass | P1 修复状态与 v4.5 audit closeout update 一致，RAG drift 状态与 recheck 一致 |
