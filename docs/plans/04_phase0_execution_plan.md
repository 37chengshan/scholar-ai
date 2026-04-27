# 04 Phase0 执行文档：项目基线梳理与风险清零

> 基线：GitHub `37chengshan/scholar-ai` `main`。  
> 注意：容器内直接 `git clone https://github.com/37chengshan/scholar-ai.git` 时 DNS 解析失败；本轮改用已连接的 GitHub 工具读取 `main` 源码与报告。  
> 用途：给后续 GPT-5.4 / agent 执行时作为项目索引、审计基线与阶段计划。  


## 1. Phase0 目标

Phase0 不是做新功能。目标是：

```txt
让 GitHub main、release gate 报告、真实测试结果完全一致。
```

只有 Phase0 通过，才进入 v2.0 Phase1。

---

## 2. Phase0 范围

### 包含

```txt
1. 项目结构索引
2. 当前 main 源码核验
3. release gate 报告核验
4. 后端 P0/P1 风险确认
5. 前端 P0/P1 风险确认
6. E2E/auth 稳定性确认
7. 一键验证脚本草案
8. 文档沉淀
```

### 不包含

```txt
1. 新 RAG 模型
2. GraphRAG
3. 新 Agent
4. 新页面大改
5. Notes 2.0
6. Paper Reading Card
7. Review Draft
```

---

## 3. Phase0 执行步骤

### Step 0：拉取基线

```bash
git checkout main
git pull --ff-only
git rev-parse HEAD
git status --short
```

记录：

```txt
commit_sha
branch
dirty_state
```

如果有未提交修改，先停止，明确是否基于本地工作区还是 GitHub main。

---

### Step 1：确认脚本真名

```bash
cat package.json
cat apps/web/package.json
```

当前已知：

```txt
根目录：
- verify:all
- type-check:web
- test:api:smoke

apps/web:
- type-check
- test:e2e
- test:e2e:ci
```

注意：

```txt
apps/web 没有 pnpm typecheck。
真实命令是 pnpm type-check。
```

---

### Step 2：源码-报告一致性核验

检查报告：

```bash
cat docs/reports/v3_6_release_gate_report.md
```

检查源码：

```bash
rg "_FAST_PATH_MAX_CHARS|simple_fast_path|smalltalk_fast_path|response_type" apps/api/app/api/chat.py
rg "clearCurrentSession" apps/web/src/app/hooks/useSessions.ts apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx
rg "h-screen|w-\[68px\]|w-\[288px\]" apps/web/src/app/components/Layout.tsx
```

判定：

| 结果 | 处理 |
|---|---|
| 报告 PASS，源码也符合 | 进入 Step 3 |
| 报告 PASS，源码不符合 | 先修源码或修报告，不能继续 |
| 源码符合，报告过期 | 更新报告 |
| 测试不通过 | v1.0/v2.0 基线不能成立 |

---

### Step 3：后端安全与 contract 核验

必查：

```bash
rg "session_manager.get_session|user_id|forbidden|403" apps/api/app/api/chat.py apps/api/app/api/session.py
```

重点：

```txt
/api/v1/chat/stream 使用 request.session_id 时，必须检查 session.user_id == current_user.id。
```

若缺失，补：

```txt
tests/api/test_chat_session_authorization.py
```

---

### Step 4：前端 type-check 与 Chat gate

```bash
cd apps/web
pnpm type-check
pnpm playwright test e2e/chat-critical.spec.ts --reporter=line
pnpm playwright test e2e/chat-evidence.spec.ts --reporter=line
pnpm playwright test e2e/notes-rendering.spec.ts --reporter=line
pnpm playwright test e2e/chat-responsive.spec.ts --reporter=line
```

如果失败：

```txt
先读 trace / screenshot / request log。
不要猜。
不要跳测。
```

---

### Step 5：后端测试

```bash
cd apps/api
python3 -m pytest tests/unit/test_chat_fast_path.py -q
python3 -m pytest tests/unit -q
```

如果 integration 测试依赖本地服务，记录依赖：

```txt
Postgres
Redis
Milvus
Neo4j
MinIO/local storage
```

---

### Step 6：生成项目索引

输出：

```txt
docs/agent/01_agent_framework_index.md
docs/audits/02_backend_full_audit.md
docs/audits/03_frontend_multidimensional_audit.md
docs/plans/04_phase0_execution_plan.md
docs/plans/05_phase1_execution_plan.md
```

---

## 4. Phase0 P0 修复清单

### P0-A：Fast path 与报告一致

验收：

```txt
RAG是什么 不走 simple fast path。
你好 走 smalltalk fast path。
done payload 有 response_type。
```

### P0-B：Chat session ownership

验收：

```txt
用户 A 不能向用户 B 的 session_id 发 /chat/stream。
```

### P0-C：`clearCurrentSession` 接口一致

验收：

```txt
pnpm type-check PASS。
/chat?new=1 首条消息绑定新 session。
```

### P0-D：Layout responsive 与报告一致

验收：

```txt
chat-responsive PASS。
body / composer / message-list 均无越界。
```

---

## 5. Phase0 验收标准

Phase0 PASS 需要同时满足：

```txt
1. GitHub main 是 clean state。
2. docs/reports/v3_6_release_gate_report.md 与源码一致。
3. apps/web pnpm type-check PASS。
4. chat-critical PASS。
5. chat-evidence PASS。
6. notes-rendering PASS。
7. chat-responsive PASS。
8. 后端 fast path 单测 PASS。
9. chat_stream session ownership 有测试或明确修复。
10. 五份索引/审计/执行文档已落地。
```

---

## 6. Phase0 交付物

```txt
1. 项目框架图 + 功能索引
2. 后端全面检查报告
3. 前端多维度审核报告
4. Phase0 执行文档
5. Phase1 执行文档
6. 当前 main 验证结果
7. 若有修复：对应 PR
```

---

## 7. Phase0 不通过时的处理

如果任一 P0 失败：

```txt
v2.0 Phase1 暂停。
先开 hotfix/phase0-baseline 分支。
只修 baseline，不做新功能。
修完重新跑全部 gate。
```
