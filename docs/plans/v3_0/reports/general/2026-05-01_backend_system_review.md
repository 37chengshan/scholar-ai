# 2026-05-01 后端系统审查报告

## 1. 审查范围

本次审查聚焦 `apps/api` 的三类真实风险面：

1. 最小 smoke 验证是否可通过
2. Chat / Session / Task 主链路是否存在契约漂移
3. service 层与测试层是否已经出现“实现已变，但验收口径未同步”的问题

本次没有修改业务代码，只做证据式检查与报告落盘。

## 2. 本次执行的验证

已执行命令与结果：

1. `bash scripts/check-doc-governance.sh`：passed
2. `bash scripts/check-structure-boundaries.sh`：passed
3. `bash scripts/check-code-boundaries.sh`：passed
4. `cd apps/api && .venv/bin/pytest -q tests/unit/test_services.py --maxfail=1`：failed
5. `cd apps/api && .venv/bin/pytest -q tests/unit/test_chat_persistence_flow.py tests/unit/test_phase_h_runtime_contract.py tests/unit/test_phase_j_comparative_gate.py tests/unit/test_auth_rate_limit_and_failclosed.py --maxfail=5`：2 failed, 19 passed

关键失败用例：

1. `tests/unit/test_services.py::TestTaskService::test_retry_task_resets_status`
2. `tests/unit/test_chat_persistence_flow.py::test_chat_api_stream_only_persists_user_message`
3. `tests/unit/test_chat_persistence_flow.py::test_chat_api_reconnect_is_replay_only_without_rerun`

## 3. 总体结论

结论：**后端当前不处于可放心收口状态**。

更准确地说：

1. 治理脚本层面是干净的，目录边界没有明显跑偏。
2. 运行契约层面，`Phase H / Phase J / auth fail-closed` 相关测试是通过的，说明部分中后段治理成果是有效的。
3. 但最基础的 service smoke 和 chat 持久化链路测试已经直接失败，说明后端当前仍有“核心路径回归 + 测试契约漂移”并存的问题。
4. 最大的问题不是单点 bug，而是 **Task 状态机、Chat 持久化、Session 回放** 三条链已经出现边界耦合和验收口径失配。

## 4. 高优先级问题

### 4.1 TaskService 与最小 smoke 测试已经失配，后端基础冒烟不通过

证据：

1. `apps/api/app/services/task_service.py:155-188`
2. `apps/api/tests/unit/test_services.py:321-336`
3. 实测 `pytest -q tests/unit/test_services.py --maxfail=1` 失败

现象：

1. `retry_task()` 明确要求 `task.status == "failed"`，否则直接抛 `ValueError("Only failed tasks can be retried")`
2. 但 `test_retry_task_resets_status` 使用的 `mock_task` 默认不是 `failed`，仍然期待成功重置为 `pending`

判断：

1. 这不是单纯的“测试没更新”这么简单。
2. 这是最小 smoke 用例已经无法代表当前实现契约，意味着团队现在对 `retry_task` 的正式语义没有稳定共识。

影响：

1. 后端最小验证命令直接红灯，PR gate 的可信度下降。
2. 任务失败重试的真实边界容易被误判，进而影响上传、解析、重试 UI 与 worker 状态恢复。

建议：

1. 先冻结 `retry_task` 的正式语义，只允许 `failed` 重试还是允许 `cancelled/pending` 重试，必须二选一。
2. 然后同步更新 `TaskService`、单测、前端动作文案和 API 契约，不要让 smoke 测试继续处于“名义 smoke，实际上失真”的状态。

### 4.2 Chat 持久化链路存在职责漂移，测试已经实锤失败

证据：

1. `apps/api/app/api/chat.py:134-260`
2. `apps/api/app/services/message_service.py:27-89`
3. `apps/api/tests/unit/test_chat_persistence_flow.py:24-53`

现象：

1. `test_chat_api_stream_only_persists_user_message` 期望 API 层只持久化 user message
2. 实测 `mock_save_message.await_count == 2`
3. 日志同时显示 assistant placeholder 被创建，并尝试更新 assistant message

判断：

1. 当前 `chat.py`、`chat_orchestrator.py`、`message_service.py` 之间的持久化职责已经发生漂移。
2. 现在的问题不是“多保存一次消息”这么表面，而是 API 层和 orchestrator 层谁负责创建 placeholder、谁负责更新、谁负责 tool message 的边界没有被稳定冻结。

影响：

1. 聊天历史回读、SSE 回放、统计字段 `message_count`、tool message 持久化都有再次分叉的风险。
2. 一旦前端按 session history 回放消息，这类重复/错位持久化问题会直接变成用户可见问题。

建议：

1. 把 `POST /api/v1/chat/stream -> SSE -> GET /api/v1/sessions/{session_id}/messages` 定义为唯一验收链。
2. 只保留一处 assistant placeholder 创建责任点，并为 user/assistant/tool 三类消息补一组回归测试快照。

### 4.3 Reconnect replay-only 链路脆弱，测试桩稍微不完整就直接走到初始化错误

证据：

1. `apps/api/app/api/chat.py:180-201`
2. `apps/api/app/api/chat.py:243-260`
3. `apps/api/tests/unit/test_chat_persistence_flow.py:55-85`

现象：

1. `test_chat_api_reconnect_is_replay_only_without_rerun` 期望 replay-only，不应重新执行 route/save_message/orchestrator
2. 实测却返回 `event: error`
3. 捕获日志里明确出现：`'S' object has no attribute 'user_id'`

判断：

1. 这说明 replay-only 逻辑虽已设计出来，但仍然过早依赖 session 对象完整结构。
2. 也就是说，重连分支并没有真正做到“尽快切到回放模式，避免碰主执行链”。

影响：

1. SSE 重连在弱网环境下会比正常路径更脆。
2. 回放链路一旦误触主执行链，最危险的后果不是报错，而是重复执行、重复持久化、重复计费。

建议：

1. `last-event-id` 分支应尽量提前短路，先完成 session 存在性与最小 ownership 校验，再进入 replay。
2. replay-only 分支需要独立测试，不应依赖普通 session stub 形状。

## 5. 中优先级问题

### 5.1 `MessageService.get_messages()` 对外部事务 session 的处理方式有明显隐患

证据：

1. `apps/api/app/services/message_service.py:114-139`

现象：

1. 函数签名声称支持传入 `db`，用于 transaction continuity。
2. 但实现里使用了 `async with session_context if not db else session_context`
3. 当 `db` 由调用方传入时，这段代码等价于 `async with db`
4. 同一函数内部又保留了另一套 `AsyncSessionLocal()` 分支

判断：

1. 这里的 session 生命周期管理非常混乱。
2. 外部传入的 session 不应该在 service 内被 `async with` 接管，否则极易提前关闭调用方事务上下文。

影响：

1. 历史消息读取在事务链内部使用时可能出现难排查的问题。
2. 这类 bug 很可能不是每次都爆，而是以偶发事务关闭、对象失效、嵌套 session 行为异常的形式出现。

建议：

1. 传入 `db` 时直接执行查询，不管理其生命周期。
2. 未传入 `db` 时才自行 `async with AsyncSessionLocal()`.

### 5.2 `cancel_task()` 的返回契约与测试期望也已脱节

证据：

1. `apps/api/app/services/task_service.py:190-210`
2. `apps/api/tests/unit/test_services.py:338-353`

现象：

1. 实现返回 `ProcessingTask`
2. 测试却断言 `result is True`

判断：

1. `TaskService` 这组测试不是只坏了一条，而是多处契约已经陈旧。
2. 当前 smoke 失败只是最早暴露的一处，后面还有潜在连锁失真。

影响：

1. 团队容易对“测试覆盖存在”产生错误安全感。
2. 当任务链继续演进时，这组测试会越来越像噪音，而不是保护网。

建议：

1. 把 `test_services.py` 重新按当前 service 契约整体校对，不要只 patch 单个断言。

### 5.3 Chat / SSE 模型与文档契约存在长期分叉风险

证据：

1. `apps/api/app/models/chat.py`
2. `docs/specs/architecture/api-contract.md`

现象：

1. 文档里冻结了 canonical SSE 事件与运行阶段语义。
2. 代码里同时保留了旧一套 `AgentPhase` / `SSEEventType` 运行术语，以及 run protocol 扩展事件。

判断：

1. 当前实现可运行，不代表契约足够清晰。
2. 一旦前端、SDK、后端分别按不同枚举理解事件，问题会表现为“看起来能跑，但边角处总在破”。

建议：

1. 给 SSE canonical event set 做一次代码侧 freeze，对外事件、内部事件、legacy 兼容事件分层。

## 6. 正向信号

以下内容说明后端并非整体失控：

1. `tests/unit/test_phase_h_runtime_contract.py`：passed
2. `tests/unit/test_phase_j_comparative_gate.py`：passed
3. `tests/unit/test_auth_rate_limit_and_failclosed.py`：passed
4. `check-doc-governance` / `check-structure-boundaries` / `check-code-boundaries`：passed

这说明：

1. Phase H 的 runtime contract 重建没有整体失效
2. Phase J 的比较 gate 主结构仍在
3. 认证 fail-closed 这条高风险线目前没有明显回退
4. 仓库治理边界至少没有再次大面积塌陷

## 7. 后端评分

本次基于当前证据给后端单独评分：

| 维度 | 分数 | 说明 |
|---|---:|---|
| 架构边界清晰度 | 7.5/10 | 目录与治理脚本较稳，但 chat persistence 职责边界开始漂移 |
| 核心链路可靠性 | 5.5/10 | task smoke 与 chat persistence 直接失败，影响主链可信度 |
| 契约一致性 | 5.5/10 | service、测试、SSE 文档之间已有显著失配 |
| 测试有效性 | 6.0/10 | 有不少有价值测试，但最小 smoke 已失真 |
| 可维护性 | 6.0/10 | 中后段 phase 代码仍可读，但消息/session 生命周期处理复杂 |
| 发布就绪度 | 5.0/10 | 不能宣称可稳定 close-out |

后端综合分：**5.9/10**

## 8. 建议修复顺序

建议按下面顺序收口：

1. 先修 `TaskService` 与 `test_services.py` 的契约失配，恢复最小 smoke 可信度
2. 再收口 `chat.py + chat_orchestrator + message_service` 的持久化职责
3. 单独修 replay-only 重连分支，确保不再触发主执行链
4. 重构 `MessageService.get_messages()` 的 session 生命周期管理
5. 最后统一 SSE 代码枚举与文档契约

## 9. 最终判断

后端现在最真实的状态不是“很多小问题”，而是：

**治理外壳基本稳定，但核心主链存在回归与契约漂移，当前更适合进入一次后端稳定性收口，而不是继续叠加新功能。**
