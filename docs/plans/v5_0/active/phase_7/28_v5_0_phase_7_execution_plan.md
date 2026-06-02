---
owner: ai-runtime
status: execution-plan-complete
depends_on:
  - docs/plans/v5_0/active/overview/27_v5_0_overview_plan.md
  - docs/plans/v5_0/active/phase_0/26_v5_0_phase_0_execution_plan.md
last_verified_at: 2026-05-31
evidence_commits:
  - working-tree-v5-0-phase-7-plan
---

# 28 v5.0-7 执行计划：Backend Pipeline 稳定性 + Runtime Contract

> 日期：2026-05-31
> 状态：execution-plan-complete
> 上游真源：`docs/plans/v5_0/active/overview/27_v5_0_overview_plan.md` Phase 7 定义

---

## 1. Objective

Phase 5.0-7 的目标是**修复后端 Pipeline 的生产级缺陷并建立可观测性基线**。

具体交付四个成果：

1. **Upload Fail-Closed 强化** — 修复 P0 crash bug、OOM 风险、非原子写入、缺失 rate limit，使上传链路在任何故障模式下 fail-closed
2. **Auth/Ownership 测试补齐** — 为 ImportJob、UploadSession、Paper、KnowledgeBase 四类资源编写跨用户越权隔离测试矩阵，验证 403 vs 401 语义
3. **Trace ID 统一** — 消除 request_id 三轨分裂（error_handler / auth / problem_detail 各自生成 UUID），统一为单一 trace_id 链路
4. **Observability SLO 基线** — 合并重复 middleware、增强 health check、定义 SLO 目标、暴露 metrics 端点

---

## 2. 范围与不在范围

### 在范围

- `apps/api/app/api/papers/paper_upload.py` — os import 修复 + 流式校验 + rate limit
- `apps/api/app/services/upload_session_service.py` — 原子写入 (temp + rename + fsync)
- `apps/api/app/services/import_file_service.py` — fsync 保障
- `apps/api/app/middleware/rate_limit.py` — fail-closed 策略对齐
- `apps/api/app/middleware/error_handler.py` — request_id 从 context 获取
- `apps/api/app/middleware/observability.py` — 合并 logging middleware 功能
- `apps/api/app/middleware/logging.py` — 删除（功能合并到 observability）
- `apps/api/app/middleware/auth.py` — request_id 从 context 获取
- `apps/api/app/utils/problem_detail.py` — request_id 从 context 获取
- `apps/api/app/workers/pipeline_context.py` — trace_id 从 task 参数恢复
- `apps/api/app/main.py` — middleware 注册调整 + /metrics 端点 + /health 增强
- `apps/api/tests/unit/test_ownership_isolation.py` — 新建 ownership 矩阵测试
- `apps/api/tests/unit/test_upload_failclosed.py` — 新建上传 fail-closed 测试
- `apps/api/tests/unit/test_trace_id_unified.py` — 新建 trace_id 统一测试
- `apps/api/tests/unit/test_observability_slo.py` — 新建 SLO metrics 测试

### 不在范围

- 任何 `apps/web` 前端代码修改
- RAG 能力改动（留给 phase 8）
- `import_job_service.py` 拆分（记录为技术债，不阻塞本 phase）
- Prometheus 部署基础设施（仅暴露 /metrics 端点，部署留给运维）
- Milvus / 向量存储改动

---

## 3. Wave 分组

依赖关系：`T1 (P0 修复) → T2 (上传强化) → T3 (Trace ID) → T4 (Auth/Ownership) → T5 (Observability)`

```
T1: P0 Crash Fix + Rate Limit 策略     [无依赖, 立即执行]
  ↓
T2: Upload Fail-Closed 强化             [依赖 T1]
  ↓
T3: Trace ID 统一                       [无依赖, 可与 T2 并行]
  ↓
T4: Auth/Ownership 测试补齐             [依赖 T2 (稳定上传链路)]
  ↓
T5: Observability SLO 基线              [依赖 T3 (统一 trace_id)]
```

---

## 4. Tasks

### T1: P0 Crash Fix + Rate Limit 策略决策

**type**: bug-fix
**complexity**: low
**estimated**: 1-2h

**files**:
- `apps/api/app/api/papers/paper_upload.py`
- `apps/api/app/middleware/rate_limit.py`

**action**:
1. 在 `paper_upload.py` 顶部添加 `import os`（第 14 行后），修复 `os.makedirs()` NameError crash
2. 在 `rate_limit.py` 第 79 行，将 `swallow_errors=True` 改为 `swallow_errors=False`，使 Redis 不可用时 rate limit 拒绝请求（与 auth middleware fail-closed 策略一致）
3. 在 `paper_upload.py` 的 `upload_to_local_storage()` 端点添加 `@limiter.limit("10/minute")` 装饰器
4. 在 `paper_upload.py` 的 `upload_webhook()` 和 `upload_paper()` 端点添加 `@limiter.limit("30/minute")` 装饰器

**verify**:
```bash
cd apps/api && python -c "from app.api.papers.paper_upload import router; print('import ok')"
cd apps/api && pytest -q tests/unit/test_uploads.py --maxfail=1
```

**done**:
- [ ] `import os` 已添加，`os.makedirs()` 不再 NameError
- [ ] rate limiter 改为 fail-closed
- [ ] 三个上传端点均有 rate limit 装饰器
- [ ] 现有上传测试通过

---

### T2: Upload Fail-Closed 强化

**type**: hardening
**complexity**: medium
**estimated**: 3-4h

**files**:
- `apps/api/app/api/papers/paper_upload.py`
- `apps/api/app/services/upload_session_service.py`
- `apps/api/app/services/import_file_service.py`
- `apps/api/tests/unit/test_upload_failclosed.py` (新建)

**action**:
1. **流式 PDF 校验** — 替换 `paper_upload.py` 第 234 行 `content = await file.read()` 为分块读取：先读 5 字节 magic header 校验 `%PDF-`，再分块读取并累计大小，超 50MB 立即 abort
2. **原子写入** — `upload_session_service.py` 第 193 行 `complete_session()` 改为 write-to-temp + `os.rename()` 模式：写入 `{final_path}.tmp`，fsync，rename 到 `{final_path}`
3. **fsync 保障** — `import_file_service.py` 的 `save_content_to_storage_key()` 写入后调用 `os.fsync(f.fileno())`
4. **PDF 结构校验** — 在 magic bytes 基础上增加 `%%EOF` 尾部检查（读取最后 1024 字节搜索 `%%EOF`）
5. **测试** — 新建 `test_upload_failclosed.py`：覆盖 OOM 防护（大文件拒绝）、原子写入（crash 残留不留）、magic bytes 校验、%%EOF 校验、rate limit 触发

**verify**:
```bash
cd apps/api && pytest -q tests/unit/test_upload_failclosed.py --maxfail=1
cd apps/api && pytest -q tests/unit/test_uploads.py tests/unit/test_upload_session_service.py --maxfail=1
```

**done**:
- [ ] `file.read()` 替换为流式分块读取，大小检查在读取过程中执行
- [ ] `complete_session()` 使用 temp + rename + fsync 原子写入
- [ ] `save_content_to_storage_key()` 写入后 fsync
- [ ] PDF 尾部 %%EOF 检查已添加
- [ ] 新建 test_upload_failclosed.py 覆盖所有 fail-closed 场景
- [ ] 现有上传测试全部通过

---

### T3: Trace ID 统一

**type**: refactor
**complexity**: medium
**estimated**: 3-4h

**files**:
- `apps/api/app/middleware/observability.py`
- `apps/api/app/middleware/error_handler.py`
- `apps/api/app/middleware/auth.py`
- `apps/api/app/utils/problem_detail.py`
- `apps/api/app/core/observability/context.py`
- `apps/api/app/workers/pipeline_context.py`
- `apps/api/tests/unit/test_trace_id_unified.py` (新建)

**action**:
1. **统一字段命名** — 将 `request_id_var` 重命名为 `trace_id_var`（context.py），HTTP 层生成的 `request_id` 统一称为 `trace_id`，保留 `X-Request-ID` header 兼容（读取时映射到 trace_id）
2. **Error handler 修复** — `error_handler.py` 第 65/130 行删除 `str(uuid.uuid4())`，改为从 `request.state.trace_id` 获取已有 ID，fallback 到 `get_trace_id()` contextvar
3. **Auth middleware 修复** — `auth.py` 中如有自生成 request_id 的逻辑，改为从 `request.state.trace_id` 获取
4. **ProblemDetail 关联** — `problem_detail.py` 第 41-42 行 `__post_init__` 中删除自动生成 UUID 的逻辑，改为从 `get_trace_id()` contextvar 获取，若为 None 则保留 None（由调用方显式传入）
5. **Worker trace 恢复** — `pipeline_context.py` 的 `PipelineContext.__init__` 接受可选 `trace_id` 参数，若提供则使用，否则生成新 UUID；Celery task 入口从 task kwargs 中提取 `trace_id` 并绑定到 contextvar
6. **测试** — 新建 `test_trace_id_unified.py`：验证 HTTP 请求全程只有一个 trace_id、error response 的 requestId 与请求一致、ProblemDetail 不再自生成 UUID、worker 可从 task 参数恢复 trace_id

**verify**:
```bash
cd apps/api && pytest -q tests/unit/test_trace_id_unified.py --maxfail=1
cd apps/api && pytest -q tests/test_trace_id.py --maxfail=1
```

**done**:
- [ ] context.py 中 `request_id_var` 重命名为 `trace_id_var`（或保留兼容别名）
- [ ] error_handler.py 不再自生成 UUID，从 request.state 或 contextvar 获取
- [ ] problem_detail.py 不再自生成 UUID，从 contextvar 获取
- [ ] auth.py 不再自生成 UUID
- [ ] PipelineContext 接受外部 trace_id 参数
- [ ] 新建 test_trace_id_unified.py 覆盖全链路 trace_id 一致性
- [ ] 现有 test_trace_id.py 通过

---

### T4: Auth/Ownership 测试补齐

**type**: testing
**complexity**: medium
**estimated**: 3-4h

**files**:
- `apps/api/tests/unit/test_ownership_isolation.py` (新建)
- `apps/api/app/services/import_job_service.py` (仅读取，不修改)
- `apps/api/app/services/upload_session_service.py` (仅读取，不修改)

**action**:
1. **Ownership 矩阵测试** — 新建 `test_ownership_isolation.py`，覆盖四类资源的跨用户越权场景：
   - ImportJob: user A 创建的 job，user B 调用 `get_job()` 应返回 403
   - UploadSession: user A 创建的 session，user B 调用 `get_session()` 应返回 403
   - Paper: user A 的 paper，user B 的 CRUD 操作应返回 403
   - KnowledgeBase: user A 的 KB，user B 的查询应返回 403
2. **403 vs 401 语义** — 验证未认证请求返回 401，已认证但无权限返回 403（不泄露资源存在性）
3. **RBAC 测试** — 测试 `require_roles()` 对 admin/user 角色的正确拦截
4. **Webhook ownership** — 验证 user A 不能确认 user B 的 upload webhook

**verify**:
```bash
cd apps/api && pytest -q tests/unit/test_ownership_isolation.py --maxfail=1
```

**done**:
- [ ] test_ownership_isolation.py 覆盖 ImportJob / UploadSession / Paper / KnowledgeBase 四类资源
- [ ] 403 vs 401 语义测试通过
- [ ] RBAC 角色拦截测试通过
- [ ] Webhook ownership 隔离测试通过

---

### T5: Observability SLO 基线

**type**: feature
**complexity**: medium
**estimated**: 3-4h

**files**:
- `apps/api/app/middleware/observability.py`
- `apps/api/app/middleware/logging.py` (删除)
- `apps/api/app/main.py`
- `apps/api/tests/unit/test_observability_slo.py` (新建)

**action**:
1. **合并双 middleware** — 将 `RequestLoggingMiddleware` 的 `SKIP_LOG_PATHS` 逻辑和结构化日志合并到 `ObservabilityMiddleware`，删除 `logging.py`，从 `main.py` 移除 `RequestLoggingMiddleware` 注册
2. **Health check 增强** — 在 `/health` 端点增加 PG / Redis / Neo4j 连通性检查，返回 `{"status": "healthy", "dependencies": {"pg": "ok", "redis": "ok", "neo4j": "ok"}}`
3. **Slow request 告警** — 在 `ObservabilityMiddleware` 中对 duration > 2000ms 的请求记录 warning 日志
4. **Metrics 端点** — 添加 `/metrics` 端点，使用 `prometheus_client` 暴露 `http_request_duration_seconds` histogram 和 `http_requests_total` counter（按 method/status/endpoint 标签）
5. **SLO 定义** — 在 `docs/specs/` 下新增 SLO 定义文档：API latency P95 < 500ms, error rate < 1%, availability > 99.5%
6. **测试** — 新建 `test_observability_slo.py`：验证 /metrics 端点返回 Prometheus 格式、/health 检查依赖、slow request 告警日志、SKIP_LOG_PATHS 仍生效

**verify**:
```bash
cd apps/api && pytest -q tests/unit/test_observability_slo.py --maxfail=1
cd apps/api && python -c "from app.main import app; print('app loads ok')"
```

**done**:
- [ ] RequestLoggingMiddleware 已删除，功能合并到 ObservabilityMiddleware
- [ ] /health 返回依赖健康状态
- [ ] > 2s 请求触发 warning 日志
- [ ] /metrics 端点暴露 Prometheus 格式指标
- [ ] SLO 定义文档已创建
- [ ] SKIP_LOG_PATHS 跳过逻辑保留
- [ ] 新建 test_observability_slo.py 通过

---

## 5. Success Criteria

| 序号 | 标准 | 验证方式 |
|------|------|----------|
| SC-1 | `upload_to_local_storage()` 端点不再 NameError crash | `python -c "from app.api.papers.paper_upload import router"` |
| SC-2 | 50MB+ 文件上传被流式拒绝，不 OOM | test_upload_failclosed.py 中大文件测试 |
| SC-3 | `complete_session()` crash 后不留残文件 | test_upload_failclosed.py 原子写入测试 |
| SC-4 | Redis 不可用时 rate limit 拒绝请求（fail-closed） | test_auth_rate_limit_and_failclosed.py 通过 |
| SC-5 | 四类资源（ImportJob/UploadSession/Paper/KB）均有 ownership 隔离测试 | test_ownership_isolation.py 通过 |
| SC-6 | HTTP 请求全程只有一个 trace_id（error response 一致） | test_trace_id_unified.py 通过 |
| SC-7 | ProblemDetail 不再自生成 UUID | test_trace_id_unified.py 通过 |
| SC-8 | 无重复 middleware 日志（每个请求一行 started + 一行 completed） | 手动检查日志输出 |
| SC-9 | /health 返回 PG/Redis/Neo4j 依赖状态 | test_observability_slo.py 通过 |
| SC-10 | /metrics 返回 Prometheus 格式指标 | test_observability_slo.py 通过 |
| SC-11 | 全部现有测试不回归 | `pytest -q tests/unit/ --maxfail=3` |

---

## 6. Risk Register

| 风险 | 影响 | 缓解 |
|------|------|------|
| `swallow_errors=False` 导致 Redis 短暂不可用时所有请求被拒 | 中 | auth 已有同样策略；Redis 可用性由运维保障 |
| 合并 middleware 可能影响外部日志消费方 | 低 | 确认当前无外部日志聚合系统依赖 RequestLoggingMiddleware 格式 |
| `request_id_var` → `trace_id_var` 重命名可能遗漏引用 | 中 | grep 全仓库确认所有引用已更新 |
| Prometheus 依赖引入增加部署复杂度 | 低 | `prometheus_client` 纯 Python 库，无外部依赖 |

---

## 7. Execution Order Summary

```
Wave 1 (立即):  T1 — P0 Crash Fix + Rate Limit 策略
Wave 2 (T1 后): T2 — Upload Fail-Closed 强化 + T3 — Trace ID 统一 (可并行)
Wave 3 (T2+T3 后): T4 — Auth/Ownership 测试 + T5 — Observability SLO (可并行)
```

总估时：10-14h（含 buffer 约 2-3 天）
