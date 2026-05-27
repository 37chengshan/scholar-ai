# v4.5 Runtime Contract Freeze

> 日期：2026-05-13  
> 状态：freeze-draft  
> 上游：`docs/plans/v4_5/active/phase_0/26_v4_5_phase_0_execution_plan.md`

## 1. 目的

冻结 v4.5 phase_0 对真实 backend benchmark 的最低 contract，避免后续把“脚本能跑”误写成“release truth 已成立”。

## 2. benchmark runtime 原则

1. 必须启动真实 backend 进程。
2. 必须先过 `/health/live`，再进入 route 级 probe。
3. benchmark 结论只能基于真实 API payload，不允许用 mock answer 替代。
4. blocked case 必须与 failed case 分开统计。

## 3. auth freeze

v4.5 phase_0 的本地 benchmark 认证策略冻结为：

1. 用户真相来自数据库中的真实用户与真实论文样本。
2. API 调用可使用内部 minted access token。
3. 该 token 仅用于本地 phase_0 benchmark，不作为产品登录流证据。

## 4. route freeze

当前正式 benchmark route：

1. `POST /api/v1/chat`
2. `POST /api/v1/search/evidence`
3. `POST /api/v1/queries/query`
4. `POST /api/v1/compare/v4`
5. `POST /api/v1/knowledge-bases/{kb_id}/query`

## 5. payload truth

脚本至少要记录：

1. 路由响应是否成功
2. latency
3. answer / evidence / citation 是否存在
4. 命中的 `paper_id` 集合
5. `answer_mode` / `abstained` / `quality`
6. blocked / failed 的具体原因

## 6. data-truth freeze

当前 KB gate 的真相边界冻结为：

1. 若 `Paper.knowledge_base_id` 已存在真实样本，则 KB-scoped benchmark 必须进入真实 pass/fail。
2. 若 `Paper.knowledge_base_id` 与 `knowledge_base_papers` 都无法提供真实 membership 样本，才允许标记为 `blocked-by-data-truth`。
3. `knowledge_base_papers = 0` 必须记录为 many-to-many association risk，但不能单独作为阻断整个 KB benchmark 的理由。
4. 不允许改写为 `not-run`、`todo` 或 `soft-pass`。

## 7. artifact freeze

v4.5 phase_0 benchmark 产物路径冻结为：

1. `artifacts/validation-results/v4_5/live_rag_benchmark/<timestamp>/summary.json`
2. `artifacts/validation-results/v4_5/live_rag_benchmark/<timestamp>/summary.md`
3. `artifacts/validation-results/v4_5/live_rag_benchmark/<timestamp>/backend.log`
