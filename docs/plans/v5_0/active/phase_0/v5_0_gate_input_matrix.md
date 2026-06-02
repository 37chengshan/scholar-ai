---
owner: product-engineering
status: active-input-matrix
created_at: 2026-05-31
last_verified_at: 2026-05-31
depends_on:
  - docs/plans/v4_5/active/phase_0/v4_5_gate_input_matrix.md
  - docs/plans/v4_0/active/phase_7/25_v4_0_phase_7_execution_plan.md
  - docs/plans/v5_0/active/overview/27_v5_0_overview_plan.md
  - docs/plans/v5_0/search/2026-05-31_v5_0_ui_polish_and_perf_research.md
consumed_by:
  - scripts/evals/run_v5_release_gate.py
---

# v5.0 Gate Input Matrix

> 本文件冻结 v5.0-9 consolidated release gate 的 5 个输入面（audit / benchmark /
> walkthrough / governance / perf），作为 `scripts/evals/run_v5_release_gate.py`
> 的实现真源。任何对 gate 判定逻辑的变更必须先更新本文件。

---

## 1. 目的与范围

### 1.1 目的

把 v5.0 release gate 在 phase_0 就冻结下来，避免 benchmark、walkthrough、closeout
各自写一套口径。`run_v5_release_gate.py` 以本文件定义的字段路径与判定规则为权威来源。

### 1.2 继承关系

- **继承自** `v4_5_gate_input_matrix.md`：沿用 gate_case 行定义（single-paper-chat、
  evidence、multi-paper-compare、compare-v4-contract、kb-scoped-*）作为 Face B
  benchmark 的子集。
- **升级自** `run_v4_phase7_gate.py`：Face A / D 逻辑升级，新增 Face C（Playwright
  walkthrough）与 Face E（Perf），共 5 面。

### 1.3 不在本 matrix 范围

- 主观 UX 评分 / 设计美感评审（非机器可量化）
- 用户 NPS / 满意度问卷
- SEO / 可访问性（WCAG）专项审计
- 后端 SLO 看板连续运行状态（由独立监控系统负责）
- 非 v5.0 主路由的 Lighthouse 分数

---

## 2. 输入面定义

---

### Face A：Audit Input（多维 Audit）

**作用**：确认产品所有已知 P1 问题在 release 前全部关闭。

**来源路径**

```
docs/plans/v5_0/reports/*_multidimensional_audit.md
```

gate runner 读取最新一份 audit 报告（按文件名日期排序取最后一条）。

**字段定义**

| 字段名 | 类型 | 说明 |
|---|---|---|
| `p1_count_open` | integer | 当前未关闭的 P1 问题总数 |
| `p2_count_open` | integer | 当前未关闭的 P2 问题总数（仅记录，不阻断） |
| `last_audit_date` | date (ISO 8601) | audit 报告的产出日期 |
| `audit_dimensions_covered` | string[] | 本轮 audit 覆盖的维度列表（如 `["frontend","backend","rag","governance","perf"]`） |
| `audit_report_path` | string | 实际读取的报告文件相对路径 |

**gate 规则**

```
PASS  ⟺  p1_count_open == 0
BLOCK ⟺  p1_count_open > 0
```

P2 数量只写入 gate report，不影响 verdict。

`audit_dimensions_covered` 必须包含
`["frontend", "backend", "rag", "governance", "perf"]` 五维，缺任一维降为 `experiment-only`。

---

### Face B：Benchmark Input（学术 + 工作流 + RAG 对比）

**作用**：确认 RAG 学术能力无回归，核心 API 合约稳定。

**来源路径**

```
artifacts/validation-results/v5_0/*/
```

gate runner 在该目录下按 run_id 前缀查找三类 artifact：

| artifact 类型 | 文件模式 | 说明 |
|---|---|---|
| 学术基准 | `academic_bench_*.json` | 针对 paper-chat / evidence / KB 路径 |
| 工作流基准 | `workflow_bench_*.json` | 针对 multi-paper-compare / compare-v4-contract |
| RAG 对比 | `rag_comparative_verdict_*.json` | RAPTOR-lite vs 当前主链基线对比 |

**字段定义**

| 字段名 | 类型 | 说明 |
|---|---|---|
| `academic_run_id` | string | 最新一次学术基准 run 的 ID |
| `academic_verdict` | `"pass"` \| `"fail"` | 学术基准整体 verdict |
| `workflow_run_id` | string | 最新一次工作流基准 run 的 ID |
| `workflow_verdict` | `"pass"` \| `"fail"` | 工作流基准整体 verdict |
| `rag_comparative_verdict` | `"pass"` \| `"fail"` \| `"skipped"` | RAPTOR-lite 对比 verdict；skipped 时计为 experiment-only |
| `regression_flag` | boolean | 任一基准相比 v4.5 baseline 出现回归时为 true |
| `last_benchmark_date` | date (ISO 8601) | 最新基准产出日期 |

**gate 规则**

```
PASS  ⟺  regression_flag == false
        AND academic_verdict == "pass"
        AND workflow_verdict == "pass"
BLOCK ⟺  regression_flag == true
        OR academic_verdict == "fail"
        OR workflow_verdict == "fail"
```

`rag_comparative_verdict == "skipped"` 时不 block，但强制将全局 verdict 降为
`experiment-only`（不能写 `release-pass`）。

benchmark gate_case 行定义沿用 `v4_5_gate_input_matrix.md` §2 的 7 行，runner
在 academic / workflow artifact 中按 `gate_case` 字段逐行核验。

---

### Face C：Walkthrough Input（Playwright E2E 主链 7 journey）

**作用**：以真实浏览器端到端验证主链 7 个核心用户旅程全部可走通。

**来源路径**

```
apps/web/playwright-report/*
artifacts/walkthrough/v5_0/*
```

gate runner 读取 `artifacts/walkthrough/v5_0/latest_summary.json`，该文件由
Playwright 报告解析脚本生成。

**7 主链 journey 定义**

| journey_id | 旅程描述 |
|---|---|
| `J1` | Landing → Login → Dashboard |
| `J2` | Upload → Parse → Index → Ready（含进度可视化） |
| `J3` | Search → Import to KB |
| `J4` | KB → Read paper |
| `J5` | Read → Highlight → Linked note |
| `J6` | Notes → @ chat session |
| `J7` | Chat → Push to notes |

**字段定义**

| 字段名 | 类型 | 说明 |
|---|---|---|
| `journey_passed_count` | integer | pass 的 journey 数量（满分 7） |
| `journey_failed_count` | integer | fail 的 journey 数量 |
| `journey_skipped_count` | integer | 因环境问题 skip 的 journey 数量 |
| `journey_details` | object[] | 每条 journey 的 `{journey_id, status, error_summary}` |
| `last_run_at` | datetime (ISO 8601) | 最近一次 E2E 跑批时间 |
| `playwright_report_path` | string | 对应 HTML 报告相对路径 |

**gate 规则**

```
PASS  ⟺  journey_passed_count == 7
        AND journey_failed_count == 0
BLOCK ⟺  journey_failed_count > 0
        OR journey_passed_count < 7
```

`journey_skipped_count > 0` 时不能写 `release-pass`，降为 `experiment-only`。

---

### Face D：Governance Input（4 套校验脚本 + plan 状态同步）

**作用**：确认仓库治理结构完整，所有 phase 计划状态与 delivery ledger 一致。

**来源路径**

gate runner 直接调用以下脚本，以退出码 0 为 pass，非零为 fail：

| check_key | 脚本路径 | 说明 |
|---|---|---|
| `doc_governance` | `scripts/check-doc-governance.sh` | 文档命名、根层结构、specs 完整性 |
| `plan_governance` | `scripts/check-plan-governance.sh` | PLAN_STATUS / delivery ledger 一致性 |
| `phase_tracking` | `scripts/check-phase-tracking.sh` | phase frontmatter 状态与 ledger 同步 |
| `governance` | `scripts/check-governance.sh` | 治理 KPI（PR 模板、分支生命周期） |
| `runtime_hygiene` | `scripts/check-runtime-hygiene.sh tracked` | 运行时产物未提交（logs / cache / venv / pycache） |

**字段定义**

| 字段名 | 类型 | 说明 |
|---|---|---|
| `doc_governance` | boolean | `check-doc-governance.sh` 退出码 0 |
| `plan_governance` | boolean | `check-plan-governance.sh` 退出码 0 |
| `phase_tracking` | boolean | `check-phase-tracking.sh` 退出码 0 |
| `governance` | boolean | `check-governance.sh` 退出码 0 |
| `runtime_hygiene` | boolean | `check-runtime-hygiene.sh tracked` 退出码 0 |
| `all_phases_closeout` | boolean | PLAN_STATUS 中 v5.0-0 ~ v5.0-9 全部标为 done |
| `governance_check_timestamp` | datetime (ISO 8601) | gate runner 执行时间戳 |

**gate 规则**

```
PASS  ⟺  doc_governance == true
        AND plan_governance == true
        AND phase_tracking == true
        AND governance == true
        AND runtime_hygiene == true
        AND all_phases_closeout == true
BLOCK ⟺  任意一项为 false
```

所有 6 项必须全部为 true，否则 block。

---

### Face E：Perf Input（Lighthouse + Bundle）

**作用**：确认前端性能满足 release-pass 基线，防止 UI excellence 目标被性能债抵消。

**来源路径**

```
artifacts/perf/v5_0/lighthouse-*.json   # Lighthouse JSON 报告（每路由一份）
dist/stats.html                          # rollup-plugin-visualizer 产物（gzip 体积）
```

gate runner 读取 4 个主路由的最新 Lighthouse JSON，并解析 `dist/stats.html`
中的 gzip 大小统计。

**受测主路由**

| route_id | 路由 |
|---|---|
| `route_landing` | `/` |
| `route_kb` | `/kb` |
| `route_read` | `/read` |
| `route_chat` | `/chat` |

**字段定义**

| 字段名 | 类型 | 说明 |
|---|---|---|
| `lighthouse_scores` | object | `{route_id: score}` 各路由 Lighthouse performance 分（0–100） |
| `lighthouse_min_score` | integer | 4 路由中最低 performance 分 |
| `a11y_scores` | object | `{route_id: score}` 各路由 Lighthouse accessibility 分（0–100） |
| `a11y_min_score` | integer | 4 路由中最低 accessibility 分；来源：`categories.accessibility.score` |
| `bundle_first_screen_kb_gz` | float | 首屏（entry chunk + critical CSS）gzip 后体积（KB） |
| `bundle_total_main_routes_kb_gz` | float | 首屏 + 4 个主链路由总下载量 gzip 后（KB） |
| `cwv_lcp_ms` | float | LCP（毫秒），取 4 路由最大值 |
| `cwv_inp_ms` | float | INP（毫秒），取 4 路由最大值 |
| `cwv_cls` | float | CLS，取 4 路由最大值 |
| `cwv_fcp_ms` | float | FCP（毫秒），取 4 路由最大值 |
| `cwv_tbt_ms` | float | TBT（毫秒），取 4 路由最大值 |
| `perf_snapshot_date` | date (ISO 8601) | 最新 Lighthouse 跑批日期 |

**gate 规则**

```
PASS  ⟺  lighthouse_min_score >= 90
        AND a11y_min_score >= 90
        AND bundle_total_main_routes_kb_gz <= 500
        AND cwv_lcp_ms < 2500
        AND cwv_inp_ms < 200
        AND cwv_cls < 0.05
BLOCK ⟺  任意一项不满足
```

a11y 分数读取自同一份 Lighthouse JSON 的 `categories.accessibility.score`
字段，与 performance 分数同源。

`cwv_fcp_ms` 与 `cwv_tbt_ms` 写入报告，不参与 PASS/BLOCK 判定，仅作为回归
预警信号（超过 1500ms / 200ms 时在报告中标 ⚠️）。

---

## 3. Verdict 三态判定逻辑

gate runner 汇总 5 个输入面结果后，按以下优先级输出唯一 verdict：

```
1. release-pass
   所有 5 个 Face 的 gate 规则均满足 PASS 条件，
   且无任何 Face 触发 experiment-only 降级。

2. experiment-only
   所有 Face 均未触发 BLOCK，
   但至少一个 Face 存在降级信号：
     - Face B: rag_comparative_verdict == "skipped"
     - Face C: journey_skipped_count > 0
     - Face A: audit_dimensions_covered 不完整（< 5 维）

3. blocked
   任意一个 Face 触发 BLOCK 条件。
   blocked 时 gate report 必须列出所有阻断原因。
```

优先级：`blocked` > `experiment-only` > `release-pass`。

---

## 4. 输出格式

gate runner 每次执行产出两份产物：

### 4.1 Machine-readable JSON

路径：`artifacts/validation-results/v5_0/gate/<run_id>_v5_release_gate.json`

顶层结构：

```json
{
  "run_id": "<ISO datetime>",
  "verdict": "blocked | experiment-only | release-pass",
  "faces": {
    "face_a": { "p1_count_open": 0, "p2_count_open": 3, "last_audit_date": "...", "audit_dimensions_covered": [...], "audit_report_path": "...", "pass": true },
    "face_b": { "academic_run_id": "...", "academic_verdict": "pass", "workflow_run_id": "...", "workflow_verdict": "pass", "rag_comparative_verdict": "pass", "regression_flag": false, "last_benchmark_date": "...", "pass": true },
    "face_c": { "journey_passed_count": 7, "journey_failed_count": 0, "journey_skipped_count": 0, "journey_details": [...], "last_run_at": "...", "playwright_report_path": "...", "pass": true },
    "face_d": { "doc_governance": true, "plan_governance": true, "phase_tracking": true, "governance": true, "runtime_hygiene": true, "all_phases_closeout": true, "governance_check_timestamp": "...", "pass": true },
    "face_e": { "lighthouse_scores": { "route_landing": 92, "route_kb": 91, "route_read": 90, "route_chat": 90 }, "lighthouse_min_score": 90, "a11y_scores": { "route_landing": 95, "route_kb": 93, "route_read": 92, "route_chat": 91 }, "a11y_min_score": 91, "bundle_first_screen_kb_gz": 76.4, "bundle_total_main_routes_kb_gz": 482.1, "cwv_lcp_ms": 2180, "cwv_inp_ms": 145, "cwv_cls": 0.03, "cwv_fcp_ms": 1320, "cwv_tbt_ms": 178, "perf_snapshot_date": "...", "pass": true }
  },
  "block_reasons": [],
  "downgrade_reasons": []
}
```

### 4.2 Markdown Gate Report

路径：`docs/plans/v5_0/reports/<YYYY-MM-DD>_v5_0_release_gate_report.md`

报告结构：

```
# v5.0 Release Gate Report — <date>

## Verdict: <release-pass | experiment-only | blocked>

## Face A — Audit
## Face B — Benchmark
## Face C — Walkthrough
## Face D — Governance
## Face E — Perf

## Block Reasons (若有)
## Downgrade Reasons (若有)
## Recommended Next Actions
```

---

## 5. 与 v4 gate runner 的主要差异

| 维度 | `run_v4_phase7_gate.py` | `run_v5_release_gate.py` |
|---|---|---|
| 输入面数量 | 3（audit + benchmark + governance） | **5**（新增 Face C walkthrough + Face E perf） |
| Face A（Audit） | 读取单份 phase 报告，仅检查 artifact 存在性 | **读取最新 multidimensional audit 报告，按 P1 数量判定；强制覆盖 5 维** |
| Face B（Benchmark） | 读取 v4 comparative_verdict.json | 继承 v4.5 gate_case 行 + 新增 rag_comparative_verdict 字段 |
| Face C（Walkthrough） | 无 | **新增：Playwright 7 journey 全 pass 为必要条件** |
| Face D（Governance） | 读取 PLAN_STATUS + 2 个脚本 | 升级为 **5 个 check 脚本 + all_phases_closeout 字段** |
| Face E（Perf） | 无 | **新增：Lighthouse ≥ 90 + Bundle ≤ 500KB gz + CWV 三指标** |
| Verdict 降级逻辑 | 无 experiment-only | **新增 experiment-only 三态** |
| 输出产物 | JSON only | **JSON + Markdown report 双产物** |

---

## 6. 实施说明

1. `run_v5_release_gate.py` 必须在缺失任一必须输入（audit report / benchmark artifact /
   playwright summary / check 脚本 / Lighthouse JSON）时将对应 Face 标为 `BLOCK`，
   不允许静默跳过。
2. 所有字段路径在脚本中显式声明为常量，不允许在运行时拼接或猜测路径。
3. gate runner 是幂等的：给定相同输入产物，多次运行输出相同 verdict。
4. Face E 的 Lighthouse JSON 必须由 CI 产出（`lighthouse --output json`），
   不允许手工填写。
5. 本文件是唯一真源；脚本内注释须引用本文件路径。
