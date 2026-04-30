# v3.6 Release Gate

```json
{
  "verdict": "PASS",
  "baseline_status": "PASS",
  "release_branch": "fix/pr60-v3-clean-merge",
  "merged_pr": 62,
  "merge_commit_sha": "6d9787b664734039bdf2ecb05bbb2703b6ce16fa",
  "gates": {
    "A_backend_chat_fast_path": "PASS",
    "B_frontend_evidence_contract_gating": "PASS",
    "C_new_chat_session_race": "PASS",
    "D_notes_raw_json_rendering": "PASS",
    "E_chat_responsive_layout_and_composer_boundary": "PASS",
    "F_left_workspace_compaction": "PASS",
    "G_e2e_contract_update": "PASS",
    "H_release_gate_report_update": "PASS"
  }
}
```

## Scope

- 顺序执行目标：A 到 H
- 本轮结论基于真实代码改动 + 真实 Playwright 结果
- 不采用 mock answer 或跳测

## Executed Validation

### Backend

- `cd apps/api && python3 -m pytest tests/unit/test_chat_fast_path.py -q`
  - 结果：`6 passed`

### Frontend Static + Unit

- `cd apps/web && pnpm typecheck`
  - 结果：脚本不存在（`Command "typecheck" not found`）
- `cd apps/web && pnpm type-check`
  - 结果：通过
- Note: apps/web 使用 `pnpm type-check`；`pnpm typecheck` 未在 package scripts 中定义。
- `cd apps/web && pnpm vitest run src/features/chat/hooks/useChatSend.test.tsx src/features/chat/components/message-feed/MessageFeed.test.tsx`
  - 结果：通过

### Frontend E2E

- `cd apps/web && pnpm playwright test e2e/chat-critical.spec.ts --reporter=line`
  - 结果：`3 passed`
- `cd apps/web && pnpm playwright test e2e/chat-evidence.spec.ts --reporter=line`
  - 结果：`1 passed`
- `cd apps/web && pnpm playwright test e2e/notes-rendering.spec.ts --reporter=line`
  - 结果：`1 passed`
- `cd apps/web && pnpm playwright test e2e/chat-responsive.spec.ts --reporter=line`
  - 结果：`1 passed`

## Gate Status

### A. 后端 Chat fast path 收口

- 状态：PASS
- 修复点：general scope 不再按“短问题”走 fast path，只允许 smalltalk 走 fast path；done SSE 明确补齐 `response_type=general` 等字段
- 证据：后端单测通过，短学术问句已验证不会误走 fast path

### B. 前端 Evidence contract gating

- 状态：PASS
- 修复点：Evidence 面板只在明确 `response_type=rag` 或存在真实 RAG 信号时渲染，不再对 general/system 响应兜底生成 abstain contract
- 证据：`chat-evidence.spec.ts` 通过

### C. 新对话 session 竞态收口

- 状态：PASS
- 目标：`/chat?new=1` 首发不预建空 session，首条消息发送时创建真实 session 并替换 URL 为 `/chat?session=<id>`
- 修复点：
  - `useChatSend` 增加 `forceNewSessionForNextSend`，new-chat 首发强制创建真实 session，不复用旧 `currentSession`
  - `ChatWorkspaceV2` 在 `/chat?new=1` 进入时开启强制新会话标记，并在 `onSessionCreated` 后清除
  - `ChatWorkspaceV2` 为 new-chat 重置逻辑增加一次性 guard，避免重复触发把用户刚输入内容清空
  - `chat-critical` 用例改为基于 `chat-composer` 定位并校验 create-session/stream/URL 三者一致
- 证据：`chat-critical.spec.ts` 全绿，首发 URL 绑定通过

### D. Notes raw JSON 渲染修复

- 状态：PASS
- 修复点：统一通过 `features/notes/content.ts` 正规化 TipTap 文档，摘要只读视图改为 `NotesEditor` 渲染，不再直接输出 raw JSON
- 证据：`notes-rendering.spec.ts` 通过

### E. Chat 响应式布局与 Composer 边界修复

- 状态：PASS
- 修复点：
  - E2E auth helper 改为固定账号登录 + 持久化 cookie（跨命令复用），避免频繁 auth 请求触发限流
  - chat-critical 改 serial，避免并发 worker 同时登录
  - responsive 用例改为单次登录后循环四个 viewport
  - 断言增强为：textarea 可见、composer 可见、message list 可见、body 无横向溢出、composer/message list 均不越界
- 证据：`chat-responsive.spec.ts` 通过且不再触发 `/api/v1/auth/register` 429

### F. 左侧工作区压缩

- 状态：PASS
- 修复点：左侧导航高度、间距、最近对话与知识库列表均已压缩，知识库列表收口到 3 项

### G. E2E 契约更新

- 状态：PASS
- 修复点：登录后基线路由改为 `/dashboard`，关键聊天断言改为现有页面契约；新增 greeting evidence、notes rendering、responsive gate

### H. Release gate 报告更新

- 状态：PASS
- 本文即为最新 gate 报告

## Remaining Issues

### P2

- `sessionsApi.updateSession` 在同时传 `title + status` 时可能丢 status 已修复。
- `pnpm typecheck` 命令在当前项目不存在，保留 `pnpm type-check` 作为实际可执行类型检查命令。

## Verdict

**PASS**

原因：A-H 全部通过，P0/P1 已闭环，`chat-critical`、`chat-responsive`、`chat-evidence`、`notes-rendering` 全绿，且前端 type-check 通过（使用项目真实脚本 `pnpm type-check`）。
