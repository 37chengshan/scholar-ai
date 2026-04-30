# 01 Agent Framework Index

## 1. Baseline Snapshot

- 执行日期: 2026-04-27
- 本地分支: fix/pr60-v3-clean-merge
- 本地提交: 20a8c9b3be2b305fcccc73a076c036890b04feb7
- 远端 main: f2d27c5bb259dd8066a1785f64dea4d486a016b6
- 基线关系: merge-base = ec1fb0514608cbb386126f2c769e1bbc62176775
- 工作区状态: dirty（存在已修改与未跟踪文件）

## 2. Runtime Structure Map

### 2.1 Frontend Runtime

- 入口: apps/web/src/main.tsx
- 路由层: apps/web/src/app
- Chat 功能主线: apps/web/src/features/chat
- Notes 功能主线: apps/web/src/features/notes
- 网络调用层: apps/web/src/services
- 主题与样式: apps/web/src/styles

### 2.2 Backend Runtime

- 入口: apps/api/app/main.py
- API 层: apps/api/app/api
- 服务层: apps/api/app/services
- 模型层: apps/api/app/models
- 核心能力: apps/api/app/core
- RAG v3 主线: apps/api/app/rag_v3

## 3. Verification Commands (Phase0)

### 3.1 Frontend

- pnpm type-check
- pnpm playwright test e2e/chat-critical.spec.ts --reporter=line
- pnpm playwright test e2e/chat-evidence.spec.ts --reporter=line
- pnpm playwright test e2e/notes-rendering.spec.ts --reporter=line
- pnpm playwright test e2e/chat-responsive.spec.ts --reporter=line

### 3.2 Backend

- python3 -m pytest tests/unit/test_chat_fast_path.py -q
- python3 -m pytest tests/unit -q

## 4. Current Gate Reality

- Chat 关键 E2E 套件已通过（critical/evidence/notes/responsive）。
- chat fast path 单测已通过（7/7）。
- 全量 unit 仍非绿灯（134 failed, 57 errors），属于历史存量与环境耦合问题，暂不满足“全量 unit 全绿”口径。

## 5. Agent Execution Boundary

- Phase0 允许: 基线核验、P0 修复、契约一致性修复、文档沉淀。
- Phase0 禁止: 新功能扩展、架构重写、大规模重构。
- Phase1 入口条件: 以 docs/plans/04_phase0_execution_plan.md 的验收条目为准，重点先清理后端全量 unit 的存量失败基线。
