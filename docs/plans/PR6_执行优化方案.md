# PR6 执行优化方案（基于代码现状）

## 背景结论

- 共享契约当前确实未落地，packages/types 与 packages/sdk 仅为占位。
- Chat/KB/SSE 契约主要在 apps/web 本地定义，存在多真相源。
- Chat 的后端流式核心并非 app/core/streaming.py，而是 app/models/chat.py + app/services/chat_orchestrator.py + app/api/chat.py。

## 优化原则（参考 agent-native）

- Parity：UI 可执行能力与 API/SDK 工具能力对齐。
- Granularity：先收口原子契约（response/chat/kb/stream），再组合到 workspace。
- Determinism：流事件统一 envelope + message_id 绑定，页面只消费统一事件形态。
- Agency：页面不直接编排复杂流程，工作流交给 workspace hook 层。

## 实施顺序

1. 共享契约收口
2. KB Workspace
3. Chat Workspace

## 切片 A：共享契约收口

### A1 交付

- packages/types 首批落地：common/chat/kb/papers。
- packages/sdk 首批落地：client/chat/kb/papers typed client。
- apps/web 服务层改为 shared types + sdk（chat/kb/import/sessions）。

### A2 后端对齐（按真实代码）

- chat/sse 相关契约以 app/models/chat.py、app/services/chat_orchestrator.py、app/api/chat.py 为主。
- app/core/streaming.py 作为通用流工具，保持兼容，不作为 Chat 主协议真源。

## 切片 B：KB Workspace

### B1 交付

- 页面壳化：app/pages/KnowledgeBaseDetail.tsx 仅做 shell。
- 工作台组件：features/kb/components/KnowledgeBaseWorkspace.tsx。
- 旧逻辑迁入 features/kb/components/KnowledgeBaseDetailLegacy.tsx，保证行为连续。
- 补充 hooks/store 骨架，后续可持续拆分 import/polling/workflow。

## 切片 C：Chat Workspace

### C1 交付

- 页面壳化：app/pages/Chat.tsx 仅做 shell。
- 工作台组件：features/chat/components/ChatWorkspace.tsx。
- 旧逻辑迁入 features/chat/components/ChatLegacy.tsx，保证行为连续。
- 补充 hooks/store 骨架，后续收口单一消息真相源与 stream state machine。

## 测试与 CI

- 前端：npm run type-check、npm run test:run。
- 后端：pytest -q tests/unit/test_services.py --maxfail=1。
- 治理：bash scripts/check-doc-governance.sh、bash scripts/check-structure-boundaries.sh、bash scripts/check-code-boundaries.sh、bash scripts/check-governance.sh。
- 若测试策略变化，需同步更新 docs/development/testing-strategy.md 和 .github/workflows。
