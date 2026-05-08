---
owner: product-engineering
status: asset-ready
depends_on:
  - 21_v4_0_phase_2_execution_plan
  - demo_dataset.md
last_verified_at: 2026-05-03
evidence_commits:
  - working-tree-v4-0-phase-2-assets
---

# v4.0 Phase 2 Demo Environment Policy

## 1. 范围

Phase 4.0-2 第一波只允许 `local controlled beta`。

任何 staging/cloud 演示都必须等到本地 fresh-state walkthrough 留下真实证据后再进入下一道 gate。

## 2. 环境决策

| environment | Phase 2 status | rule |
|---|---|---|
| local controlled beta | allowed | 作为唯一默认执行环境；必须有 reset proof |
| staging controlled beta | gated | 只有 local fresh-state pass 后才允许扩展 |
| cloud/public beta | out-of-scope | 交给 Phase 4.0-7 release/eval gate |

## 3. Demo Account Policy

1. 统一使用单一受控本地 demo 账号策略，记录名为 `beta_local_operator`。
2. 如果本地环境未启用正式登录流，walkthrough 记录中必须改填实际 `user_id` 或等效本地身份标识。
3. 同一轮 run 只允许一个 demo 账号写入数据，避免跨账号污染 KB、import jobs 与反馈记录。
4. 若 demo 账号已有历史 KB 或 import job，必须先清理或换一个新的 run namespace，不能直接宣称 fresh-state。

## 3.1 Controlled Beta Access Policy

1. local controlled beta 只允许三类参与者：
   - `primary operator`：实际执行 quickstart、记录 evidence、提交 feedback
   - `internal reviewer`：独立阅读 quickstart / known limitations，并对 run 结果提出反馈
   - `invited observer`：只读旁观，不直接写入共享 demo 数据
2. 同一轮 run 只能有一个 `primary operator`，其余参与者不得在未 reset 的前提下复用同一 KB 命名空间继续写入。
3. 所有参与者在开始前都必须阅读：
   - `beta_quickstart.md`
   - `known_limitations.md`
4. 若参与者观察到 `partial / fail / blocked`，必须按 `feedback_triage_template.md` 落单，而不是只在聊天记录中口头说明。
5. local controlled beta 的“受控”含义是：
   - 人群受控：仅限内部或明确邀请的试用者
   - 数据受控：只允许使用受控 run namespace 与 demo account
   - 节奏受控：任何新 run 都可被暂停，不允许默认持续放量

## 4. 环境变量边界

Phase 2 不引入 demo-only 配置；只允许使用仓库已有本地配置入口。

必查项：

| area | source of truth | minimum expectation |
|---|---|---|
| backend vector store | `apps/api/.env.example` | `MILVUS_HOST` 与 `MILVUS_PORT` 指向本地 Milvus |
| backend embedding | `apps/api/.env.example` | `EMBEDDING_MODEL`、`EMBEDDING_DEVICE`、`QWEN3VL_EMBEDDING_MODEL_PATH` 已配置 |
| backend reranker | `apps/api/.env.example` | `QWEN3VL_RERANKER_MODEL_PATH` 可用 |
| backend LLM | `apps/api/.env.example` | `LLM_MODEL`、`LLM_API_BASE` 与所需 API key 已就绪 |
| frontend API target | `apps/web/src/config/api.ts` | 默认本地开发通过 Vite proxy 指向 `http://localhost:8000`；若覆盖，必须显式记录 `VITE_API_BASE_URL` |

## 5. Reset Policy

### 5.1 Fresh-state 定义

只有同时满足以下条件，才允许把本次 walkthrough 写成 fresh-state：

1. 使用专用 demo 账号或等效单人本地身份。
2. 本次 run 的 KB 命名空间是新的，例如 `scholarai-beta-<run_id>`。
3. 该账号下不存在同名 KB、未完成 import job 或未归档 feedback 项。
4. backend、celery worker、postgres、redis、milvus 等服务状态已记录。

### 5.2 Reset Checklist

1. 确认本地服务状态：`docker compose ps` 或等效服务列表可读。
2. 若需要重新准备 Python 依赖，使用 `bash scripts/bootstrap-shared-api-env.sh`，不新建 Phase 2 专用脚本。
3. 记录 backend 配置来源：`apps/api/.env` 或等效本地环境注入方式。
4. 为本次 run 生成唯一 `run_id`，并按该 `run_id` 创建 KB 前缀。
5. 清理该 demo 账号下同前缀 KB 与未完成 import jobs；若做不到，直接标记 `blocked`。
6. 确认本地截图、日志与反馈文件使用相同 `run_id` 命名。

## 6. 数据隔离边界

| surface | allowed reset | forbidden shortcut |
|---|---|---|
| demo account | 清理或重建本地 demo 账号数据 | 复用带历史 KB 的账号后仍声称 fresh-state |
| knowledge bases | 仅清理 demo 账号名下、与 `run_id` 同前缀的 KB | 共享 KB 混入旧论文后继续跑 walkthrough |
| import jobs | 清理 demo 账号下未完成或同前缀任务 | 忽略 stuck import job 并继续验证下游页面 |
| vector store / artifacts | 默认只做账号与 KB 级隔离；不要求全库 drop | 共享 Milvus 状态无法区分旧 run 仍宣称 clean reset |
| screenshots / logs | 使用 `run_id` 归档到本地临时记录 | 拿旧 run 截图充当新 run 证据 |

## 7. 不可清理状态

以下情况一旦存在，本轮 run 不得声称 fresh-state，只能记为 `blocked` 或重新分配环境：

1. 无法确认 demo 账号对应的历史 KB 是否已隔离。
2. 无法判断未完成 import job 是否仍会写入当前 KB。
3. 共享 Milvus/worker 在后台继续消费旧任务，导致当前 run 无法区分新旧写入。
4. frontend 未明确指向当前本地 backend。

## 8. Staging/Cloud Expansion Gate

只有同时满足以下条件，才允许把本地策略外推到 staging/cloud：

1. local fresh-state walkthrough 已留下真实证据。
2. quickstart 与 known limitations 已被受控试用者阅读。
3. feedback triage 模板已接住至少一个真实 `partial` 或 `blocked` 例子。
4. rollback/pause 责任人和禁用口径已写入 closeout report。

## 9. Rollback / Pause Rule

1. `product-engineering` 是 Phase 2 local controlled beta 的默认 gate owner。
2. 出现以下任一情况时，必须立即 `pause` 新 beta run：
   - Search / Import / KB / Read / Chat / Notes / Compare / Review 任一主链重新出现 `P0`
   - 无法再证明 fresh-state reset
   - 已知 limitation 超出当前文档口径，导致 quickstart 会误导试用者
3. `pause` 的执行动作：
   - 停止安排新的 `beta_local_operator` walkthrough
   - 冻结当前 run namespace，不允许继续把其结果当作新证据
   - 在 closeout 或后续 gate report 中把 phase verdict 降回 `demo-ready` 或 `blocked`
4. `disable` 的含义不是删除代码，而是停止当前受控 beta 入口：
   - 停止把 Phase 2 quickstart 作为可执行试用入口
   - 停止把当前 local beta 环境写成 `controlled-beta-ready`
5. 只有在以下条件同时满足时才允许 `resume`：
   - 对应 `P0/P1` 已完成 fix-now 或被重新分类为 accepted limitation
   - 反馈队列已有明确 owner / decision
   - 必要时补充新的 walkthrough 或 gate evidence
