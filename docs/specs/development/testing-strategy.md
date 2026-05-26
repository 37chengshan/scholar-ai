# Testing Strategy

## Purpose

定义 ScholarAI 的测试分层、覆盖范围与最小回归要求，保证重构和新功能可验证。

## Scope

覆盖单元测试、集成测试、E2E 测试、冒烟测试与回归触发条件。

## Source of Truth

- PR 流程：docs/specs/development/pr-process.md
- 文档校验：docs/specs/development/documentation-validation.md
- API 契约：docs/specs/architecture/api-contract.md
- 系统总览：docs/specs/architecture/system-overview.md

## Rules

单元测试覆盖范围：

- 纯函数、数据转换、核心业务规则
- service 层关键分支
- 前端 hooks 与 store 的状态转换

集成测试覆盖范围：

- API 路由到 service 的主链路
- 数据库读写与任务状态变更
- SSE 关键事件序列
- Import Pipeline 批次接口部分成功契约（accepted/rejected）
- Chat stream 到 session messages 回读契约一致性

E2E 覆盖范围：

- 上传论文 -> 解析 -> 检索/对话
- 创建会话 -> 发送消息 -> 流式返回
- 核心失败路径（鉴权失败、解析失败、超时）
- 关键链路阻断：Chat、KB、Retrieval

浏览器工具优先级：

- `Chrome DevTools MCP`：默认主工具，用于逐页导航、DOM 检查、控制台/网络排障、截图、性能与资源证据采集。
- `Computer Use`：作为视觉级交互补充，用于真实点击、滚动、菜单、遮挡、悬浮、响应式布局确认。
- `browser-harness`：作为脚本化浏览器自动化补充，用于需要自定义 Python 流程、批量操作或直接接管真实 Chrome 的场景。
- `browser-use`：已弃用，不得作为新工作的执行路径。

自动化基线：

- `scripts/verify/run-all.sh` 与 `.github/workflows/verify.yml` 是默认自动化验证基线。
- `ci-lite.yml` 与 `governance.yml` 是基线的子集或治理 smoke 变体，不得引入不同的 Node major 或冲突的必测定义。
- PR19 / Playwright 分步 walkthrough 属于扩展浏览器验证；只有当变更触及真实上传、任务编排、流式交互或响应式界面时才进入阻断清单。

PR19 最小流程分步验证（先节点后整跑）：

- 后端/Worker 启动基线（必须显式使用 `.venv`，避免环境漂移）：
	- API：
		- `cd apps/api && PYTHONPATH=$(pwd) .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000`
	- Worker（必须配置真实 Qwen 模型路径）：
		- `cd apps/api && PYTHONPATH=$(pwd) QWEN3VL_EMBED_MODEL_PATH=/Users/cc/.cache/huggingface/hub/models--Qwen--Qwen3-VL-Embedding-2B QWEN3VL_RERANK_MODEL_PATH=/Users/cc/.cache/huggingface/hub/models--Qwen--Qwen3-VL-Reranker-2B .venv/bin/celery -A app.workers.celery_app worker --loglevel=info --pool=solo`
- 进程稳定性检查（防止 python 进程崩溃）：
	- `pgrep -fl "uvicorn app.main:app|celery -A app.workers.celery_app"`
	- 若节点3失败，先检查 API/Worker 进程是否仍存活，再看 `apps/api/logs` 和 Playwright trace。

- 固定测试账号（禁止动态注册绕过）：
	- email: `pr19-e2e@example.com`
	- password: `Pr19E2EPass123`
	- 初始化/重置命令：
		- `cd apps/api && .venv/bin/python scripts/ensure_e2e_test_user.py`
- 节点验证顺序（每个节点通过后再进入下一个）：
	- 节点1 登录：`cd apps/web && npx playwright test e2e/pr19-stepwise-flow.spec.ts --grep "节点1"`
	- 节点2 创建知识库：`cd apps/web && npx playwright test e2e/pr19-stepwise-flow.spec.ts --grep "节点2"`
	- 节点3 上传3篇并可见进度：`cd apps/web && npx playwright test e2e/pr19-stepwise-flow.spec.ts --grep "节点3"`
	- 节点4 论文列表与阅读总结：`cd apps/web && npx playwright test e2e/pr19-stepwise-flow.spec.ts --grep "节点4"`
	- 节点5 单篇/多篇 RAG 对话：`cd apps/web && npx playwright test e2e/pr19-stepwise-flow.spec.ts --grep "节点5"`
- 全节点通过后再执行整链路：
	- `cd apps/web && npx playwright test e2e/pr19-stepwise-flow.spec.ts`
	- `cd apps/web && npx playwright test e2e/pr19-min-flow.spec.ts`
- 报告产物：
	- `docs/plans/v3_0/reports/validation/pr19-stepwise-flow-report.json`
	- `docs/plans/v3_0/reports/validation/pr19-min-flow-browser-report.json`

必测核心链路：

- API 统一响应格式
- 异步任务状态机迁移
- SSE done/error 收敛行为

冒烟测试清单：

- runtime hygiene 校验
- 文档结构与链接校验
- 结构边界校验
- 代码层边界校验
- 前端 type-check
- packages/types 与 packages/sdk 构建检查
- 后端 pytest 最小子集
- 核心文档存在性与路径正确性
- phase 交付台账一致性校验
- 分支生命周期校验
- 契约 gate 与 fallback 到期校验
- E2E gate manifest 校验

测试产物不入库规则：

- 禁止提交 `test-results/`、`apps/web/test-results/`、`playwright-report/`
- 禁止提交 `.coverage`、`apps/api/.coverage`、`htmlcov/`、`apps/api/htmlcov*/`
- 禁止提交 `.pytest_cache/`、`apps/api/**/__pycache__/`、`apps/api/venv/`

必须补回归测试的变更：

- API 响应结构变更
- 资源状态机变更
- 鉴权与权限控制变更
- SSE 事件语义变更
- 路由命名或参数协议变更
- 导入批次响应结构变更（`accepted/rejected/reason`）
- 会话消息分页与 total 语义变更

## Required Updates

- 新增测试层级或框架：同步更新本文件与 docs/specs/development/pr-process.md。
- 新增关键链路：同步更新必测链路与冒烟清单。

## Verification

- 本地自动化基线：
	- bash scripts/check-governance.sh
	- bash scripts/verify/run-all.sh

- 扩展浏览器验证（按变更触发）：
	- cd apps/web && npm run test:e2e:ci
	- cd apps/web && npx playwright test e2e/pr19-stepwise-flow.spec.ts
	- cd apps/web && npx playwright test e2e/pr19-min-flow.spec.ts

- CI 最小验证：
	- `.github/workflows/verify.yml`：本地自动化基线的 CI 等价物
	- `.github/workflows/ci-lite.yml`：轻量 PR smoke
	- `.github/workflows/governance.yml`：治理与结构 smoke
	- `.github/workflows/e2e-gate.yml`：浏览器阻断链路

## Open Questions

- 如何在保留执行时长可控的前提下扩大 E2E 阻断覆盖面。
- 是否对 SSE 增加专门的契约测试快照。
