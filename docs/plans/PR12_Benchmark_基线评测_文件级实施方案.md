---
owner: ai-platform
status: done
depends_on:
  - PR11
last_verified_at: 2026-04-17
evidence_commits:
  - 84fd597
---

# PR12：Benchmark / 基线评测 文件级实施方案

## 1. 目标

在 PR11 完成 Harness Observability 之后，为 ScholarAI 建立第一版**可回归、可对比、可解释**的 benchmark 基线，覆盖：

- Chat 稳定性
- Search / KB 工作流稳定性
- RAG 检索与回答质量
- 基础性能（延迟 / phase duration）

---

## 2. 当前基线（基于现有仓库）

### 已有基础
- 前端已经有：
  - page shell tests
  - hook tests
  - `useChatStream` 相关测试
  - `sseParser` / `chatApi` / `kb` 相关测试
- 后端已有：
  - `tests/unit/test_services.py`
  - `tests/test_unified_search.py`
- PR10 已把 KB / Chat / Search 迁到 workspace 分层第一阶段，并补了对应 shell / hook 测试

### 当前缺口
- 还没有“场景级 benchmark”
- 没有统一数据集或 fixture catalog
- 没有 latency / success rate / stability baseline
- 没有 benchmark 结果输出格式
- 没有回归阈值和红线

---

## 3. 非目标（本 PR 不做）

- 不做线上 A/B
- 不做重型 load testing 平台
- 不引入复杂评测 SaaS
- 不做真实外部模型质量排行榜
- 不要求一次覆盖所有业务域

---

## 4. PR12 要覆盖的四类基线

## 4.1 Chat Stability Benchmark
衡量：
- send -> stream start latency
- stream complete success rate
- stop / retry / confirmation / cancel 是否按预期转移
- session switch 后是否状态干净
- stale SSE event 是否被正确忽略

### 样本类型
- 普通单轮问答
- 多轮会话
- confirmation_required
- 用户 stop
- 用户 retry
- 断流/错误恢复

---

## 4.2 Search / KB Workflow Benchmark
衡量：
- search latency
- filter / pagination 稳定性
- import flow success/cancel/retry
- polling completion detection
- results consistency

### 样本类型
- 空结果搜索
- 普通关键词搜索
- 分页搜索
- import -> polling -> completed -> refresh
- cancel import flow

---

## 4.3 RAG Quality Benchmark
衡量：
- retrieval hit quality
- citation completeness
- answer confidence range
- compare / evolution query 稳定性
- stream 和 blocking 回答的一致性

### 样本类型
- single paper
- cross paper compare
- evolution
- citation-sensitive question
- no-evidence question

---

## 4.4 Performance Baseline
衡量：
- request total duration
- phase duration（retrieving / synthesizing / verifying）
- import pipeline step duration
- search latency P50/P95（本地基线）
- streaming time to first token / time to done

---

## 5. 文件级实施方案

## 5.1 基准样本与 fixture

### A. 新增 `apps/api/tests/benchmarks/fixtures/`
建议新增：

```text
apps/api/tests/benchmarks/fixtures/
  chat/
    simple_chat.json
    confirmation_chat.json
    cancel_chat.json
  search/
    basic_search.json
    empty_search.json
    paginated_search.json
  rag/
    rag_single.json
    rag_compare.json
    rag_evolution.json
    rag_no_evidence.json
  import/
    import_flow.json
    import_cancel.json
```

### 目标
每个 fixture 明确：
- 输入
- 预期成功/失败类型
- 预期 phase
- 最低 citation / source 约束
- 允许的时延范围（可选）

---

### B. 新增 `apps/api/tests/benchmarks/catalog.py`
### 目标
统一管理 benchmark case 元数据。

### 内容
- case id
- domain
- title
- fixture path
- tags
- expected assertions
- severity

---

## 5.2 后端 benchmark runner

### C. 新增 `apps/api/tests/benchmarks/run_chat_benchmark.py`
### 目标
执行 chat stability benchmark。

### 覆盖
- stream starts
- message_id binding
- stop / cancel
- confirmation-required flow
- final status
- latency summary

### 依赖
- PR11 的 observability logs / context
- Chat API / orchestrator 的稳定接口

---

### D. 新增 `apps/api/tests/benchmarks/run_search_benchmark.py`
### 目标
执行 search 与 KB workflow benchmark。

### 覆盖
- search request latency
- result_count consistency
- pagination correctness
- import workflow state sequence（若后端可直接驱动）

---

### E. 新增 `apps/api/tests/benchmarks/run_rag_benchmark.py`
### 目标
执行 RAG 质量 benchmark。

### 覆盖
- blocking query
- stream query
- agentic query（若稳定）
- confidence distribution
- citation completeness
- source count

### 输出
- 每个 case 的：
  - success
  - latency
  - source_count
  - confidence
  - citation_count
  - notes

---

### F. 新增 `apps/api/tests/benchmarks/run_perf_baseline.py`
### 目标
从 PR11 的 observability 事件中汇总性能基线。

### 覆盖
- total request duration
- TTFT（time to first token，如果可采）
- total stream duration
- rag retrieve duration
- rag answer duration
- import phase duration

---

### G. 新增 `apps/api/tests/benchmarks/reporting.py`
### 目标
统一 benchmark 输出格式。

### 输出格式建议
- JSON：给机器读
- Markdown：给 PR review 看

### 统一结构
```json
{
  "suite": "chat_stability",
  "generated_at": "...",
  "cases": [
    {
      "case_id": "...",
      "status": "passed",
      "latency_ms": 123,
      "metrics": {},
      "notes": []
    }
  ],
  "summary": {
    "passed": 8,
    "failed": 1,
    "p50_ms": 120,
    "p95_ms": 290
  }
}
```

---

## 5.3 前端交互基线

### H. 新增 `apps/web/src/benchmarks/`
建议结构：

```text
apps/web/src/benchmarks/
  chat/
    chatStability.cases.ts
  search/
    searchFlow.cases.ts
  kb/
    importFlow.cases.ts
```

### 目标
让前端也有轻量场景集，不只依赖后端 benchmark。

---

### I. 新增前端 benchmark 测试
建议新增：

- `apps/web/src/features/chat/__tests__/chatStability.benchmark.test.ts`
- `apps/web/src/features/search/__tests__/searchFlow.benchmark.test.ts`
- `apps/web/src/features/kb/__tests__/importFlow.benchmark.test.ts`

### 覆盖
- session switch
- scope change
- stale SSE ignored
- stop/retry
- import cancel / completion refresh
- search pagination / import modal flow

### 说明
这类测试仍基于 Vitest / RTL，不需要上 E2E 平台。

---

## 5.4 基线阈值与门禁

### J. 新增 `apps/api/tests/benchmarks/thresholds.py`
### 目标
定义各套 benchmark 的阈值。

### 示例
- Chat：
  - success_rate >= 0.95
  - stop action state transition == deterministic
- Search：
  - result_count non-negative
  - pagination stable
- RAG：
  - source_count >= 1（evidence questions）
  - confidence in [0,1]
  - citation_count >= 1（citation-sensitive questions）
- Performance：
  - local baseline P50 < X
  - no catastrophic regression > 30%

---

### K. 新增 `scripts/run-benchmarks.sh`
### 目标
统一运行 benchmark。

### 建议内容
```bash
python -m apps.api.tests.benchmarks.run_chat_benchmark
python -m apps.api.tests.benchmarks.run_search_benchmark
python -m apps.api.tests.benchmarks.run_rag_benchmark
python -m apps.api.tests.benchmarks.run_perf_baseline
cd apps/web && npm run test:run -- src/features/chat/__tests__/chatStability.benchmark.test.ts
cd apps/web && npm run test:run -- src/features/search/__tests__/searchFlow.benchmark.test.ts
cd apps/web && npm run test:run -- src/features/kb/__tests__/importFlow.benchmark.test.ts
```

---

### L. 新增 `scripts/check-benchmark-thresholds.py`
### 目标
读取 benchmark report，对比阈值，作为 PR gate（先本地，后 CI）。

---

## 5.5 文档与报告

### M. 新增 `docs/benchmarks/README.md`
### 内容
- benchmark 目标
- 套件划分
- 运行命令
- 输出位置
- 如何更新阈值

---

### N. 新增 `docs/benchmarks/baseline-template.md`
### 内容
- 当前版本 baseline
- P50/P95
- success rate
- known flaky cases
- pending improvements

---

### O. 新增 benchmark 产物目录（可 gitignore）
建议：
- `artifacts/benchmarks/*.json`
- `artifacts/benchmarks/*.md`

不要把运行产物直接提交到代码目录。

---

## 6. 实施步骤（按依赖顺序）

## Phase 1：样本与 runner 骨架
1. 新增 fixtures
2. 新增 catalog
3. 新增 reporting
4. 新增 run_chat_benchmark.py
5. 新增 run_search_benchmark.py
6. 新增 run_rag_benchmark.py

### 依赖关系
- 不依赖前端 benchmark
- 依赖 PR11 已提供的 observability context 更佳，但可先写 runner 骨架

---

## Phase 2：性能基线
1. 新增 `run_perf_baseline.py`
2. 接 observability 输出
3. 新增 thresholds.py

### 依赖关系
- 强依赖 PR11
- 没有 PR11 时只能做弱性能统计

---

## Phase 3：前端 benchmark
1. 新增 case 文件
2. 新增 benchmark tests
3. 接 workspace hooks / services

### 依赖关系
- 依赖 PR10
- 若 PR11 前端 telemetry 已落地，可增强断言

---

## Phase 4：脚本与门禁
1. 新增 `run-benchmarks.sh`
2. 新增 `check-benchmark-thresholds.py`
3. 文档更新
4. 视情况接入 CI（可第二阶段）

---

## 7. 交付清单

### 必交付
- benchmark fixtures
- benchmark catalog
- chat/search/rag/perf 四套 runner
- 前端 chat/search/kb 三套 benchmark tests
- threshold 定义
- benchmark 运行脚本
- benchmark 文档
- JSON + Markdown 报告输出

### 完成标准
- 任何一次改 Chat / Search / RAG / Import 后，都能跑统一 benchmark
- benchmark 报告能给出 success/failure + latency + quality summary
- 至少有一套性能基线可对比
- 至少有一套质量基线可对比
- PR review 不再只靠“手工试一下”

---

## 8. 验收命令

### 后端 benchmark
```bash
cd apps/api && python -m tests.benchmarks.run_chat_benchmark
cd apps/api && python -m tests.benchmarks.run_search_benchmark
cd apps/api && python -m tests.benchmarks.run_rag_benchmark
cd apps/api && python -m tests.benchmarks.run_perf_baseline
```

### 前端 benchmark
```bash
cd apps/web && npm run test:run -- src/features/chat/__tests__/chatStability.benchmark.test.ts
cd apps/web && npm run test:run -- src/features/search/__tests__/searchFlow.benchmark.test.ts
cd apps/web && npm run test:run -- src/features/kb/__tests__/importFlow.benchmark.test.ts
```

### 阈值校验
```bash
python scripts/check-benchmark-thresholds.py
```

### 仓库级
```bash
bash scripts/check-governance.sh
bash scripts/verify-all-phases.sh
bash scripts/run-benchmarks.sh
```

---

## 9. 风险与控制

### 风险 1：benchmark 过于脆弱
控制：
- 先做 deterministic case
- flaky case 单独标记，不进硬门禁

### 风险 2：质量指标太主观
控制：
- 第一版先用结构化可验证指标：
  - source_count
  - citation_count
  - confidence range
  - stream completion
  - latency

### 风险 3：性能基线受环境波动影响太大
控制：
- 第一版只做本地/CI 相对基线
- 用 regression threshold，不用绝对 SLA

### 风险 4：前后端 benchmark 口径不一致
控制：
- 所有 suite 通过 catalog + reporting 统一口径

---

## 10. PR 建议标题

`test(benchmarks): add chat/search/rag baseline suites and performance benchmarks`
