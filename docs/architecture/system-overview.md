# System Overview

## Purpose

定义 ScholarAI 的子系统边界、前后端职责、数据与任务流以及异步链路，作为架构与协作的统一基线。

## Scope

覆盖 apps/web、apps/api、异步任务、SSE 流式输出及外部运行时依赖。

当前仓库主路径：

- apps/web -> Web 前端实现
- apps/api -> API 后端实现
- infra -> docker-compose、nginx、部署脚本
- tools -> scripts 与开发辅助工具

## Source of Truth

- API 契约：docs/architecture/api-contract.md
- 资源模型：docs/domain/resources.md
- 开发规范：docs/development/coding-standards.md
- 架构入口：architecture.md

## Rules

子系统清单：

- Web 客户端：apps/web（Vite + React）
- API 后端：apps/api（FastAPI）
- 异步任务：apps/api/app/tasks 与 apps/api/app/workers
- 持久化与检索：PostgreSQL/PGVector、Redis、Neo4j、Milvus
- KB Review Pipeline：apps/api/app/services 下的 ReviewDraft 编排链路（outline/retrieve/write/validate/finalize）

前后端边界：

- 前端页面只消费 service/hooks，不直接拼接 API 调用。
- apps/api/app/api 只做协议与编排入口，不写重业务逻辑。
- apps/api/app/services 承担业务编排，数据访问和模型调用在对应基础层完成。

数据流：

1. 前端页面触发用户动作。
2. service/hooks 发起请求到 API。
3. router 完成鉴权与入参校验后转入 service。
4. service 协调数据库、向量检索和外部模型。
5. 返回统一响应格式给前端。

任务流：

1. 用户触发上传/解析/索引任务。
2. API 创建任务并持久化状态。
3. worker 消费任务并更新资源状态。
4. 前端轮询或订阅事件获取进度。

KB 综述草稿流（Phase 5）：

1. 用户在 Knowledge Workspace 的 review tab 发起整库或子集综述生成。
2. API 创建/更新 `ReviewDraft` 并启动 `ReviewRun`。
3. 服务编排执行 `outline_planner -> evidence_retriever -> review_writer -> citation_validator -> draft_finalizer`。
4. 若 Graph 不可用，检索链路降级为 local-only，并在 `error_state/quality` 留痕。
5. 前端通过真实 runs API 拉取 timeline 与 step drill-down。

SSE/异步链路：

- SSE 事件命名、载荷与完成信号遵循 docs/architecture/api-contract.md。
- Chat 流式事件仅接受 canonical event types，不再接收 legacy alias 映射。
- 除 heartbeat 外，所有业务 SSE 事件必须携带 `message_id`。
- 长任务必须可观测，至少提供 queued/running/succeeded/failed 状态。

当前主执行链路：

- Chat 前端主入口固定为 `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`。
- Chat 页负责统一 runtime 执行；Search、Read、Notes 只负责输入准备、结果展示与深链跳转，不再各自维护并行执行内核。
- Compare 页面主入口固定为 `apps/web/src/app/pages/Compare.tsx`，通过 `apps/api/app/api/compare.py -> compare_service.py -> HybridRetriever(real dense wiring)` 输出 evidence-backed `compare_matrix`。
- Compare 页面带入 Chat 的后续追问统一走 `POST /api/v1/chat/stream`，以 `context.paper_ids[]` 作为 canonical 多论文 scoped RAG 输入，不新增第二套 compare-chat runtime。
- KB review 生成为独立入口，仅服务综述草稿资源，不进入 Read/单篇问答主链路。

Notes/Read ownership：

- `paper.reading_notes` 是系统生成阅读摘要，由 notes API 与 notes worker 统一写入。
- `Note` 是用户可编辑笔记实体，由 `/api/v1/notes` 维护。
- Notes 页面可以展示系统摘要，但该展示是 derived projection，不再把系统摘要同步复制成 `Note` 实体。
- Read 页面自动创建或加载的 `reading note` 只指向用户笔记。

外部依赖与运行时组件：

- Docker Compose 作为本地依赖编排入口。
- Nginx 配置位于 nginx。
- 部署脚本位于根目录 deploy-cloud*.sh，后续纳入 infra/deploy 逻辑聚合。

## Required Updates

- 新增/删除子系统：同步更新本文件与 architecture.md。
- 引入新运行时依赖：同步更新 docs/domain/resources.md。
- 改动 SSE 行为：同步更新 docs/architecture/api-contract.md。

## Verification

- 检查目录边界：确认无新增平行实现目录。
- 检查链路一致性：随机抽样前端调用与后端路由是否经由 service。
- 检查异步可观测性：任务状态可从 API 或事件读取。

## Phase 6 评测子系统（Evaluation Subsystem）

Phase 6 引入一个独立的内部评测子系统，不影响用户侧功能，仅供工程内部 RAG 质量门禁与基准追踪使用。

### 子系统边界

```
┌─────────────────────────────────────────────────────────┐
│            Phase 6 Evaluation Subsystem                  │
│                                                          │
│  [Frozen Corpus]          [Run Artifacts]                │
│  artifacts/benchmarks/    artifacts/benchmarks/          │
│  phase6/corpus.json       phase6/runs/{run_id}/          │
│         │                         │                      │
│         └──────────┬──────────────┘                      │
│                    ▼                                      │
│           [eval_service.py]                              │
│   normalize | gate-evaluate | diff                       │
│                    │                                      │
│                    ▼                                      │
│           [evals.py router]                              │
│      GET /api/v1/evals/{overview,runs,diff}              │
│                    │                                      │
│                    ▼                                      │
│        [Analytics page /analytics]                       │
│     React eval dashboard (internal only)                 │
└─────────────────────────────────────────────────────────┘
```

### 关键约束

- **无 DB 依赖**：所有评测数据以文件系统 JSON 产物形式存储，`eval_service.py` 纯文件读取
- **离线评测优先**：`mode=offline` 运行为硬性门禁（gate），`mode=online` 为 shadow 非阻断报告
- **不可变产物**：运行目录写入后不修改（append-only），门禁阈值存于 `eval_service.py::PHASE6_THRESHOLDS`
- **v2.0 close-out gate**：offline gate 额外要求真实冻结 corpus（≥50 papers / ≥128 queries / 8 families）、baseline+candidate+diff 完整产物、candidate 无 6 项核心质量回退
- **只读 API**：`/api/v1/evals/*` 无写端点，无 auth 依赖（内部接口）
- **`/dashboard` 不变**：用户侧 dashboard 与本评测子系统完全隔离，`/analytics` 为内部评测看板
- **门禁脚本**：`scripts/evals/phase6_gate.py` exit 0=PASS / exit 1=FAIL，且已接入 `scripts/release/run-v2-gate.sh` 与 `.github/workflows/release-gate.yml`

## Open Questions

- deploy-cloud 系列脚本收敛到 infra/deploy 的分阶段计划。
- 是否需要统一任务编排层以减少 worker 入口分散。
