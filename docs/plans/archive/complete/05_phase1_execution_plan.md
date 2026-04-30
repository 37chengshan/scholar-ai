# 05 Phase1 执行文档：Production Hardening

> 基线：GitHub `37chengshan/scholar-ai` `main`。  
> 注意：容器内直接 `git clone https://github.com/37chengshan/scholar-ai.git` 时 DNS 解析失败；本轮改用已连接的 GitHub 工具读取 `main` 源码与报告。  
> 用途：给后续 GPT-5.4 / agent 执行时作为项目索引、审计基线与阶段计划。  


## 1. Phase1 目标

Phase1 是 v2.0 的工程底座。

目标：

```txt
把 v1.0 的人工验收，升级成一键 release gate + CI + 部署 smoke test。
```

Phase1 完成后，后续任何 v2.0 功能都必须经过同一套门禁。

---

## 2. Phase1 范围

### 包含

```txt
1. 一键 release gate runner
2. Playwright global auth setup
3. CI type-check + E2E + backend smoke
4. 部署后 smoke test
5. trace_id / run_id 全链路规范
6. API error contract 固化
7. Session 生命周期规范
8. Health/readiness 分层
```

### 不包含

```txt
1. Paper Reading Card
2. Evidence to Notes
3. Multi-paper Compare
4. Review Agent
5. GraphRAG
6. RAG 模型替换
```

---

## 3. Work Package 1：一键 release gate runner

### 目标

新增：

```txt
scripts/release/run-v2-gate.sh
```

执行：

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[Gate] Web type-check"
cd apps/web
pnpm type-check

echo "[Gate] Chat critical"
pnpm playwright test e2e/chat-critical.spec.ts --reporter=line

echo "[Gate] Chat evidence"
pnpm playwright test e2e/chat-evidence.spec.ts --reporter=line

echo "[Gate] Notes rendering"
pnpm playwright test e2e/notes-rendering.spec.ts --reporter=line

echo "[Gate] Chat responsive"
pnpm playwright test e2e/chat-responsive.spec.ts --reporter=line

cd ../api
echo "[Gate] Backend fast path"
python3 -m pytest tests/unit/test_chat_fast_path.py -q
```

根目录新增脚本：

```json
"release:gate": "bash scripts/release/run-v2-gate.sh"
```

验收：

```bash
pnpm release:gate
```

输出 PASS/FAIL。

---

## 4. Work Package 2：Playwright global auth setup

### 当前问题

`apps/web/e2e/helpers/auth.ts` 已经开始使用固定账号 + cookie 持久化，但仍应升级为 Playwright 官方 global setup / storageState 模式。

### 目标结构

```txt
apps/web/e2e/global-setup.ts
apps/web/e2e/.auth/user.json
apps/web/playwright.config.ts
```

### 目标行为

```txt
1. global setup 确保测试用户存在。
2. login 一次。
3. 保存 storageState。
4. 所有 E2E 复用 storageState。
5. 单测不再重复 register/login。
```

验收：

```txt
chat-responsive 不触发 register。
多 worker 下不 hit auth rate limit。
```

---

## 5. Work Package 3：CI gate

新增 GitHub Actions：

```txt
.github/workflows/release-gate.yml
```

最低任务：

```txt
web-type-check
web-e2e-critical
api-unit-smoke
docs-governance
```

建议先不把所有重 AI integration 放进 CI，避免运行成本过高。

CI 策略：

| 任务 | 触发 | 是否阻断 |
|---|---|---|
| type-check | PR | 是 |
| chat-critical | PR | 是 |
| notes-rendering | PR | 是 |
| backend fast path | PR | 是 |
| full integration | nightly | 否，先报告 |
| RAG benchmark | manual/nightly | 否，v2.0 后期转阻断 |

---

## 6. Work Package 4：部署 smoke test

新增：

```txt
scripts/release/smoke-prod.sh
```

检查：

```txt
/health
/login
/dashboard
/chat
/notes
/search
```

最小命令：

```bash
BASE_URL=https://your-deploy-url bash scripts/release/smoke-prod.sh
```

Smoke test 不做复杂内容，只验证：

```txt
1. 页面可访问。
2. 登录可用。
3. Chat composer 可见。
4. Notes 页面不 raw JSON。
5. API health ready。
```

---

## 7. Work Package 5：Trace / Run ID 规范

### 目标

所有核心请求都有：

```txt
request_id
trace_id
run_id
session_id
user_id
```

### 后端建议

Middleware 生成：

```txt
request_id
trace_id
```

Chat runtime 生成：

```txt
run_id
retrieval_trace_id
```

SSE 事件携带：

```txt
message_id
run_id
trace_id
```

前端存储：

```txt
message.runId
message.traceId
message.retrievalTraceId
```

验收：

```txt
E2E 可断言 Chat 产生 run_id / trace_id。
日志能串起一次请求。
```

---

## 8. Work Package 6：API Error Contract

统一错误格式：

```json
{
  "success": false,
  "error": {
    "type": "https://scholar-ai/errors/validation",
    "title": "Validation Error",
    "status": 400,
    "detail": "message",
    "requestId": "...",
    "timestamp": "..."
  }
}
```

前端统一处理：

```txt
AuthError
ValidationError
ForbiddenError
NotFoundError
RateLimitError
ServerError
NetworkError
```

验收：

```txt
所有 API service 不再各自猜错误结构。
```

---

## 9. Work Package 7：Session 生命周期规范

定义：

```txt
draft
active
archived
deleted
```

Chat 新对话：

```txt
/chat?new=1 → draft UI state
first send → active session
```

禁止：

```txt
空 session 污染 session list
旧 session 被 new-chat 首发复用
session URL 与 stream request session_id 不一致
```

验收：

```txt
chat-critical 覆盖：
- new chat first send
- old session not polluted
- URL/session/request consistency
- reload restores session
```

---

## 10. Work Package 8：Health / readiness

新增或增强：

```txt
/health/live
/health/ready
/health/degraded
```

检查：

| 检查项 | ready 必需 |
|---|---|
| FastAPI process | 是 |
| PostgreSQL | 是 |
| Redis | 是 |
| Milvus | v2 视环境 |
| Neo4j | v2 视环境 |
| Embedding | prod/eager 必需 |
| Reranker | prod/eager 必需 |
| LLM provider | 可 degraded |

验收：

```txt
AI 服务失败时，健康状态能区分 live / ready / degraded。
```

---

## 11. Phase1 验收标准

Phase1 PASS：

```txt
1. `pnpm release:gate` 一键可跑。
2. Playwright E2E 使用 global auth state。
3. chat-responsive 不再依赖注册流程。
4. CI 对 PR 执行 type-check + core E2E + backend smoke。
5. 部署后 smoke test 可执行。
6. Chat/SSE 请求带 trace_id/run_id。
7. API error contract 有统一前端处理。
8. Session lifecycle 写入文档并有 E2E 覆盖。
9. Health/readiness 能反映依赖状态。
```

---

## 12. Phase1 不建议做

```txt
- 不换 RAG 模型。
- 不做 Reading Card。
- 不做 Review Agent。
- 不重写 UI。
- 不迁移状态管理框架。
- 不把所有 integration test 强行塞进 PR CI。
```

---

## 13. Phase1 推荐 PR 拆分

```txt
PR-1: release gate runner
PR-2: Playwright global auth state
PR-3: CI release-gate workflow
PR-4: deploy smoke test
PR-5: trace_id/run_id propagation
PR-6: API error contract
PR-7: session lifecycle contract + tests
PR-8: health/readiness endpoints
```

每个 PR 要求：

```txt
1. 修改范围清晰。
2. 有测试。
3. 更新 docs。
4. 不做无关重构。
```
