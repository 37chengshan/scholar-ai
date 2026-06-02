---
owner: product-engineering
status: overview-frozen
depends_on:
  - 2026-05-31_v5_0_research_decision_note.md
  - 25_v4_5_overview_plan.md
  - 18_v4_0_overview_plan.md
  - 2026-05-26_v4_5_frontend_backend_multidimensional_audit.md
last_verified_at: 2026-05-31
evidence_commits:
  - working-tree-v5-0-kickoff
---

# 27 v5.0 纵览计划:Re-launch with UI Excellence

> 日期:2026-05-31
> 状态:overview-frozen
> 上游研究:`docs/plans/v5_0/active/overview/2026-05-31_v5_0_research_decision_note.md`

## 0. 版本定位

`v5.0` 不是新产品,也不是对 v4.x 的小修小补。它是 ScholarAI 自项目启动以来第一次**为"产品诚实可宣称 release-pass"而设计的完整迭代版本**。

统一表达为:

```txt
v5.0 = Re-launch with UI Excellence
     = v4.x release-readiness 残留收口 (phase_3 artifact / phase_5 interaction / phase_7 gate)
     + 设计系统 v2 + WorkspaceShell v2 + Performance 体系
     + 主链 6 页深度精修 (杂志编辑风继承 + 反模板视觉)
     + 上传可视化 + Chat↔Notes 集成桥
     + Pipeline 真稳定性 + Auth/Observability 收口
     + RAG SOTA 深扩 (RAPTOR-lite + Graph review-only + Verifier 融合)
     + 全链 walkthrough + consolidated release gate
     + 第一份诚实 release verdict
```

## 1. 启动前提

本计划建立在以下 repo 真相之上(已用直接代码扫描核实,2026-05-31):

1. **前端栈成熟但债务集中**:Chat 已 7141 行 / 24 hooks / 8 子组件目录,Read 1384 行但 **0 test**,Notes 2475 行但 2 test,Compare 1159 行 **0 test**,Upload features 完整但 **app/pages 无路由**。
2. **设计 token 严重不足**:`apps/web/src/styles/theme.css` 仅 39 个 CSS vars,`magazine.css` 524 行编辑风资产可继承。
3. **性能基线为零**:Vite 配置无 manualChunks / 无 visualizer / 无 budget,仅有 route lazy 切分。
4. **后端 Pipeline 可视化已就绪但前端断链**:`apps/api/app/api/imports/events.py` + `tasks/{id}/progress` + `_sync_import_job_stage` 都已实现,但前端 Upload 页不存在。
5. **RAG SOTA 三件套已有雏形**:`hierarchical_retriever.py` 是 RAPTOR-lite 起点,`claim_verifier` + `citation_verifier` + `claim_evidence_verifier` 三 verifier 已存在,只有 Graph synthesis 是真正空白。
6. **2026-05-26 multidimensional audit P1 大部分已修闭环**,只剩需要进一步加固的 Auth/Observability/Pipeline 残端。
7. **2026-05-27 RAG drift recheck 已通过**,4 个 current drift 红点全部消除。
8. **v4.0 phase_3/5/7 仍未真正 closeout**,v4.5 bridge phase_0 已完成。

## 2. v5.0 的唯一目标

把 ScholarAI 从"局部可演示 / 多 phase 各自局部完成 / honest verdict 永远是 blocked"的状态,推进为**"产品视觉体验完整 + 全链路稳定 + RAG 学术深度领先 + 治理诚实可宣称 release-pass"**的状态。

用户表达的最大要求:**UI 美观 + 体验完整**。本计划以这一要求作为所有取舍的最高优先级。

## 3. v4.x 残留迁移决策

| 来源 | 迁入目标 | 处置 |
|---|---|---|
| v4.0 phase_3 (artifact contract closeout) | v5.0-5 (Notes 重构,artifact 与 notes 重叠) + v5.0-6 (Chat citation panel 体验) | 原 phase 在 PLAN_STATUS 标 superseded |
| v4.0 phase_5 (interaction quality) | v5.0-1 (设计系统 v2) + v5.0-2 (WorkspaceShell v2) | 原 phase 在 PLAN_STATUS 标 superseded |
| v4.0 phase_7 (testing & evaluation gate) | v5.0-9 (consolidated release gate) | gate runner 升级而非重写 |
| v4.5 bridge phase_0 | 已 closeout,作为 v5.0 的 release-readiness baseline | 保持 done,不动 |
| v4.5 W2-W? 残留 (若有) | v5.0-0 (Foundation + 治理切换) | 在 inventory 文档中逐项映射 |

## 4. Phase 拆分 (10 phase,六到八个月)

### Phase 5.0-0:Foundation + v4.x 迁移 + Audit Baseline (1-2 周)

**主线:**治理切换
**目标:**
1. 完成 v4.x → v5.0 phase migration inventory
2. `scripts/evals/run_v4_phase7_gate.py` 升级为 `run_v5_release_gate.py`
3. v5.0 runtime contract freeze (继承 v4.5 + 预留 RAPTOR/Graph/verifier fusion 字段)
4. v5.0 gate input matrix (audit + benchmark + walkthrough + governance + perf)
5. 性能基线测量 (首轮 Lighthouse + bundle 体积 snapshot)
6. 多维 audit baseline 二轮跑一次

**不做:**任何业务代码改动。

### Phase 5.0-1:设计系统 v2 + 杂志编辑风深化 + 反模板视觉 (2-3 周)

**主线:**前端基础
**目标:**
1. CSS tokens 从 39 扩到 ~200,建立 typography/color/spacing/motion/elevation 五大 token 族
2. 继承现有 `magazine.css` 524 行编辑风资产,升级为完整 design system v2
3. 三栈字体配齐:`Playfair Display` (display serif) + `Noto Serif SC` (中文 serif) + 新增 mono 栈
4. Color palette 改用 oklch,建立 semantic color (surface / accent / text / state)
5. Dark theme 专项:不是简单反色,而是独立色板
6. Motion system v2:duration/ease/intent 三层
7. Anti-template 视觉策略:editorial layout + 不对齐栅格 + 大尺度对比

**不做:**改动主链页面布局(留给 5.0-2 ~ 5.0-6)。

### Phase 5.0-2:WorkspaceShell v2 + 响应式 + Performance 体系 (2-3 周)

**主线:**前端基础
**目标:**
1. WorkspaceShell v2:响应式 stack、密度系统、键盘流统一
2. Performance 体系从零建立:
   - 引入 `rollup-plugin-visualizer`
   - 在 `vite.config.ts` 配 `manualChunks`(按 feature 分包)
   - 引入 Lighthouse CI 接入门禁
   - 建立 bundle budget(单 chunk ≤ 200KB gzipped,首屏 ≤ 500KB gzipped)
   - 路由级 preload 策略
3. Skeleton / loading / empty / error 四态系统化
4. 把 P1-FE-004 (workspace 窄屏) 升级为响应式底层

**不做:**改 6 个主链页面的内部布局。

### Phase 5.0-3:上传可视化全链路 (跨层,新独立 phase) (2-3 周)

**主线:**跨层(前端 + 后端)
**目标:**
1. 在 `apps/web/src/app/pages/` 补 `Upload.tsx` 页面路由
2. 接入现有 `apps/web/src/features/uploads/` (chunk/instant/recovery hooks 已就绪)
3. 上传可视化 UX:
   - 拖拽 + 队列卡片
   - 分阶段进度卡 (upload → parse → chunk → embed → index → ready)
   - 失败重试 / 取消 UX
   - 批量上传聚合视图
4. 接入后端 `imports/events.py` SSE 实时进度
5. 后端 `_sync_import_job_stage` 真实暴露给前端 (确保每个 stage 都能映射到 UI)
6. 取消中途 mid-pipeline (P2-TASK-002 已修,补 UI 反馈)

**不做:**改其他主链页面;改 Notes/Chat/Read。

### Phase 5.0-4:Read 页 + pretext 阅读引擎 + PDF 体验 (3-4 周)

**主线:**前端深度
**目标:**
1. 引入 `@chenglou/pretext` 作为 Read 页文字排版底层
2. evidence 侧栏 + 笔记面板使用 pretext 进行精准高度测量与文本绕排
3. PDF annotation v2:
   - selection → highlight → linked note 完整流
   - 键盘流 (j/k 翻页, [/] 缩放, n 新笔记)
   - annotation 列表面板
4. linkedNote 双向同步:Read 页与 Notes 页共享同一来源
5. **补齐 Read 页 0 个 test 文件** → 至少 6 个 component 测试 + 1 个 E2E spec
6. 阅读体验细节:reading progress 自动保存 / 阅读时长追踪

**不做:**改 Notes 编辑器(留给 5.0-5);引入 GraphRAG。

### Phase 5.0-5:Notes 系统深度重构 + editorial 排版 (3-4 周)

**主线:**前端深度
**目标:**
1. TipTap 二次封装为 ScholarAI Notes Editor:
   - block-based 编辑
   - @ mention atomic pill (paper/chunk/evidence/session)
   - 智能链接建议
2. pretext 接入 Notes 页 editorial 排版:
   - 多栏流动布局
   - obstacle-aware 标题/引用绕排
   - shrinkwrap 长引文
3. 笔记 ↔ paper / chunk / evidence / chat session 反向链
4. 笔记导出 (Markdown / PDF / BibTeX 关联)
5. 把 v4.0 phase_3 的 artifact contract closeout 在这里完成
6. 补齐测试覆盖 (从 2 升到 ~15)

**不做:**改 Chat;引入 GraphRAG。

### Phase 5.0-6:Chat 体验打磨 + Chat↔Notes 集成桥 (2-3 周)

**主线:**前端深度
**目标:**(Chat 已 7141 行成熟,本 phase 是**精修而非重构**)
1. message feed virtualization(用 pretext 高度预测,消除 SSE 期间的 layout shift)
2. composer-input UX 升级:多行 + 快捷键 + @ mention 笔记
3. reasoning-panel / tool-timeline 视觉与状态语义升级
4. citation-panel + evidence card 体验改造(响应 5.0-5 的笔记锚定)
5. **Chat↔Notes 双向集成桥**:
   - Chat 内 @ 笔记 / 引用笔记内容
   - Chat 结论一键 push 到笔记 (新建/追加)
   - Notes 内 @ chat session 引用历史对话
6. compare card UI 重做
7. SSE/cancel/retry 用户可见状态系统化

**不做:**改 RAG backend;改 Notes editor 底层。

### Phase 5.0-7:后端 Pipeline 真稳定性 + Auth/Observability 收口 (2-3 周)

**主线:**后端
**目标:**
1. 上传 fail-closed 终局加固 (在 5.0-3 visual 基础上做 backend 收口)
2. Auth/Ownership 残留检查:cross-user 路径全覆盖测试
3. trace_id / run_id / compare_matrix 全链路统一贯通
4. Observability SLO 看板:
   - 上传完成率 / 解析失败率 / RAG p95 latency / claim verification rate
5. 把 phase6_runtime contract 字段在所有路径强一致暴露

**不做:**改 RAG 主链能力(留给 5.0-8);改前端。

### Phase 5.0-8:RAG SOTA 深扩 (RAPTOR-lite + Graph review + Verifier 融合) (3-4 周)

**主线:**后端
**目标:**
1. `hierarchical_retriever.py` 升级为 RAPTOR-lite:递归摘要树 + 多粒度检索
2. Review-only Graph synthesis:
   - entity extraction → community detection → community summary
   - 仅在 review draft 生成时使用,不进 KB chat 主链
3. 三 verifier 融合 + NLI 升级:
   - `claim_verifier` + `citation_verifier` + `claim_evidence_verifier` 统一 entry
   - 引入 NLI / claim-level entailment
   - early-exit + async caching 控制 latency
4. comparative benchmark:RAPTOR-lite vs 当前主链 baseline,verdict 入 release gate

**不做:**改前端;改 Notes/Chat。

### Phase 5.0-9:全链 walkthrough + Release Gate + 多维 Audit + Closeout (2-3 周)

**主线:**验收
**目标:**
1. 7 个核心 journey 全 E2E 覆盖:
   - Landing → Login → Dashboard
   - Upload → Parse → Index → Ready
   - Search → Import to KB
   - KB → Read paper
   - Read → Highlight → Linked note
   - Notes → @ chat session
   - Chat → Push to notes
2. consolidated release gate runner (替代 v4.0 phase_7 gate)
3. multidimensional audit 二轮 (产品视角 + 治理视角 + perf 视角 + 学术视角)
4. v5.0 closeout report + 首份 release verdict
5. **release-pass 三必要条件**:
   - 7 主链 E2E 全过
   - benchmark not regression (RAG academic baseline)
   - multidimensional audit 无未修 P1

**不做:**继续增加新能力;改任何 v5.0 phase 已 closeout 范围。

## 5. 不在 v5.0 范围内 (避免范围蔓延)

1. ❌ NotebookLM 风 Audio Overview (声学合成不属学术核心价值)
2. ❌ 多人协作 Spaces / 实时编辑 (单用户深度优先)
3. ❌ 移动端原生 App (响应式 web 已足够)
4. ❌ GraphRAG 全主链化 (仅 review-only)
5. ❌ 重写 SDK / packages 顶层 (沿用现有契约)
6. ❌ 第二套 runtime / 第二套 chat surface / 平行前端路径
7. ❌ Chat 完整重构 (Chat 已成熟,只精修不重写)
8. ❌ 切换 PDF 渲染库 (pdfjs-dist + react-pdf 保留)
9. ❌ 切换编辑器框架 (TipTap 保留,只做二次封装)

## 6. 关键技术取舍 (Phase 0 会再做一次取舍冻结)

### 6.1 pretext 引入方式

- 推荐:`npm install @chenglou/pretext`,在 `apps/web/src/lib/pretext/` 做 thin adapter
- 在 5.0-0 决定。

### 6.2 RAPTOR-lite 落地形态

- 推荐:先 review-only + compare 接入,主 KB chat 在第二波 benchmark 通过后再切
- 在 5.0-8 决定。

### 6.3 Verifier 融合策略

- 推荐:统一 entry + NLI 增强 + early-exit + cache
- 在 5.0-8 决定。

### 6.4 Bundle 切分策略

- 推荐:按 feature 切 (chat / read / notes / kb / search / compare / uploads) 各成独立 chunk
- 在 5.0-2 决定。

## 7. 第一批正式产物 (在 5.0-0 落地)

1. `docs/plans/v5_0/active/phase_0/26_v5_0_phase_0_execution_plan.md`
2. `docs/plans/v5_0/active/phase_0/v5_0_runtime_contract_freeze.md`
3. `docs/plans/v5_0/active/phase_0/v5_0_gate_input_matrix.md`
4. `docs/plans/v5_0/active/phase_0/v5_0_v4x_migration_inventory.md`
5. `docs/plans/v5_0/active/phase_0/v5_0_perf_baseline_snapshot.md`
6. `scripts/evals/run_v5_release_gate.py`
7. `docs/plans/v5_0/reports/2026-XX-XX_v5_0_phase_0_audit_baseline.md`

## 8. release-pass 门禁

任何一项不满足都不允许在 v5.0-9 写 release-pass:

1. ✅ Phase 5.0-0 ~ 5.0-9 全部 closeout (PLAN_STATUS + delivery ledger 全部 done)
2. ✅ 7 主链 journey E2E 全过 (Playwright)
3. ✅ benchmark not regression (academic + workflow + RAG comparative)
4. ✅ multidimensional audit 二轮无未修 P1
5. ✅ Lighthouse CI 在 4 个主路由(/, /kb, /read, /chat)分数 ≥ 90
6. ✅ Bundle 首屏 ≤ 500KB gzipped
7. ✅ Auth/Ownership 跨用户负向测试零失败
8. ✅ 后端 SLO 看板连续运行无致命点

## 9. 治理与依赖

1. v5.0 全程必须通过 4 套治理校验:`scripts/check-doc-governance.sh` / `check-plan-governance.sh` / `check-phase-tracking.sh` / `check-governance.sh`
2. 每个 phase 必须按 GSD workflow 走 (`/gsd:plan-phase` → `/gsd:execute-phase` → `/gsd:verify-phase` → `/gsd:code-review`)
3. 跨 phase 增量改动必须先回到本 overview 文档评估
4. 任何 phase 文档不允许写成 release-candidate 或 release-pass 直到 5.0-9 完成
5. v5.0 引入的新依赖必须先经 search-first 评估并记录在 `docs/plans/v5_0/search/`

## 10. 工作量估计

- 最快路径:22 周 ≈ 5.5 个月
- 含 buffer:32 周 ≈ 8 个月
- 推荐配置:6-7 个月节奏,每 phase 保留 closeout 缓冲

## 11. 并行 Wave 视图与依赖关系

### 11.1 Phase 依赖矩阵

| Phase | 强依赖 (必须先完成) | 软依赖 (建议先) | 可与之并行 |
|---|---|---|---|
| 5.0-0 | — (起点) | — | — |
| 5.0-1 | 5.0-0 | — | 5.0-7 (后端独立) |
| 5.0-2 | 5.0-0, 5.0-1 部分 (token) | — | 5.0-7 |
| 5.0-3 | 5.0-1, 5.0-2 | — | 5.0-4 / 5.0-7 / 5.0-8 |
| 5.0-4 | 5.0-1, 5.0-2 | — | 5.0-3 / 5.0-7 / 5.0-8 |
| 5.0-5 | 5.0-1, 5.0-2, **5.0-4** (pretext adapter) | 5.0-3 | 5.0-7 / 5.0-8 |
| 5.0-6 | 5.0-1, 5.0-2, **5.0-5** (Notes 桥另一端), 5.0-4 | — | 5.0-7 / 5.0-8 |
| 5.0-7 | 5.0-0 | — | 5.0-1 ~ 5.0-6 全部 |
| 5.0-8 | 5.0-0 | 5.0-7 | 5.0-1 ~ 5.0-6 全部 |
| 5.0-9 | **所有 phase** | — | — |

### 11.2 并行波次方案 (推荐)

**Wave 0 (1-2 周) — 串行**
- 5.0-0 单独跑 (治理切换 + 基线测量, 不动业务代码)

**Wave 1 (2-3 周) — 双轨启动**
- 5.0-1 前端基础 (设计系统 v2)
- 5.0-7 后端 Pipeline 稳定性 ← 完全独立轨道

**Wave 2 (2-3 周) — 三轨**
- 5.0-2 性能体系 + WorkspaceShell v2 (5.0-1 token 70% 完成后启动)
- 5.0-7 继续
- 5.0-8 RAG 研究 + 索引侧工程提前起步

**Wave 3 (3-4 周) — 高并行**
- 5.0-3 上传可视化 ⎫
- 5.0-4 Read + pretext ⎬ 三轨纯前端并行 (含 Compare 测试补齐)
- 5.0-7 收尾
- 5.0-8 RAPTOR / Graph 主体实施

**Wave 4 (3-4 周) — 双轨**
- 5.0-5 Notes 重构 ← 5.0-4 完成 pretext adapter 后启动
- 5.0-8 收尾 + benchmark
- 5.0-3 / 5.0-4 closeout

**Wave 5 (2-3 周) — Chat 集中精修**
- 5.0-6 Chat 解冻 + Chat↔Notes 集成桥 ← 5.0-4/5.0-5/5.0-7/5.0-8 全 done
- 5.0-7 / 5.0-8 进入 maintenance

**Wave 6 (2-3 周) — 验收**
- 5.0-9 全链 walkthrough + Release Gate + Multidimensional Audit + Closeout

### 11.3 关键路径 (Critical Path)

```
5.0-0  →  5.0-1  →  5.0-2  →  5.0-4  →  5.0-5  →  5.0-6  →  5.0-9
1-2 wk    2-3 wk    2-3 wk    3-4 wk    3-4 wk    2-3 wk    2-3 wk
                                                         合计 15-22 周
```

后端 5.0-7 / 5.0-8 在并行轨道上,**不延长整体周期**。

### 11.4 时间对比

| 方案 | 周数 | 说明 |
|---|---|---|
| 纯串行 | 22-32 周 | overview 第 10 节给的 buffer 总和 |
| **合理并行 (推荐)** | **15-22 周 (~4-5.5 个月)** | 后端轨与前端轨完全并行 |
| 极限并行 | 13-18 周 | 5.0-5 与 5.0-4 强 overlap,合并风险高 |

### 11.5 并行红线 (不能违反)

1. ❌ 5.0-5 不能在 5.0-4 pretext adapter 落地前启动 — Notes editorial 排版直接复用 adapter
2. ❌ 5.0-6 Chat↔Notes 桥不能在 5.0-5 完成前启动 — 桥的"Notes 端"接入点在 5.0-5 定义
3. ❌ 5.0-6 message virtualization 不能在 5.0-4 pretext 落地前启动
4. ❌ 5.0-9 不能在任何 phase blocked 时启动
5. ❌ 5.0-7 的 Chat↔Notes 后端 API 必须在 5.0-6 前 done
6. ⚠️ 5.0-3 跨层 phase 必须前后端同 wave closeout,否则上传可视化半挂

### 11.6 推荐压缩优化 (可选)

按以下优化后关键路径可压到 14-19 周:

1. 5.0-1 末尾 1 周与 5.0-2 头部 1 周 overlap (token 70% 完成切 5.0-2)
2. 5.0-3 的后端 SSE 暴露并入 5.0-7 (同团队同时做)
3. 5.0-8 的 RAPTOR-lite 索引重建可在 5.0-7 任何时点起步

## 12. 风险与缓解

| 风险 | 缓解 |
|---|---|
| pretext 接入 PDF 渲染层导致 layout shift | 先做 Read 侧栏小规模 PoC,通过后再扩 |
| RAPTOR-lite 重做索引阻断现有 KB | 用影子索引并行验证,确认后切换 |
| 强 verifier 增加 latency | 异步链路 + cache + early-exit |
| 10 phase 拉长导致需求漂移 | 每 phase 必须 closeout 且禁止跨 phase 增量 |
| 设计系统 v2 与现有 magazine.css 冲突 | 把 magazine.css 作为继承基底而非废弃 |
| Chat↔Notes 集成桥后端工作量未计入 | 5.0-7 预留 backend mutation API |
| 上传可视化与 Pipeline 改造同步漂移 | 5.0-3 跨层 phase 必须前后端联动 closeout |
