## 变更目的
- 完成 Chat 页面问题修复计划中的测试与验收闭环，覆盖前端稳定性与后端 simple fast path 的关键验证点。

## 变更内容
- [x] 前端（apps/web）
- [x] 后端（apps/api）
- [ ] 文档（docs）
- [ ] 脚本 / 基础设施（scripts / infra）

详细说明：
- 新增 `ChatWorkspaceV2` 级测试：发送后 placeholder 立即可见、首个 message chunk 优先渲染。
- 新增 `ExecutionTimeline` 测试：唯一 key 场景下无 duplicate key warning，并加全局 mock 恢复防止污染。
- 增强 `MessageFeed` 测试覆盖首 chunk 与 runtime 元数据并发更新时正文优先显示。
- 增强后端 `test_chat_fast_path.py`：
  - simple query 走 fast path
  - compare/general 与 single_paper scope 不走 fast path
  - SSE 顺序 `session_start -> routing_decision -> message -> done`
  - done diagnostics 包含首 token 时延并断言 `first_token_emit_latency_ms <= 3000`
- 修复后端测试导入兼容性（Router 生命周期参数）与 SSE chunk bytes 解析健壮性。

## 影响范围
- 页面：Chat 页相关渲染链路测试（不改 UI 样式）
- 接口：`/api/v1/chat/stream` fast path 与 SSE 契约测试
- 服务/脚本：无新脚本，测试覆盖增强
- 数据/配置：无新增配置与迁移

## 风险评估
- 风险等级：低
- 主要风险：测试 mock 过多导致与真实集成偏差；已通过路由顺序与时延诊断字段断言降低风险。
- 回滚方式：回滚本次提交即可恢复到原测试集。

## 交付单元追踪
- Phase ID: chat-p0-validation
- Deliverable Unit: chat-fastpath-test-acceptance
- Migration-Task: N/A
- 未覆盖项: 未执行完整 e2e 套件，保留给后续 PR/CI 阶段。

## 自测清单
### 仓库治理
- [ ] `bash scripts/check-runtime-hygiene.sh tracked`
- [ ] `bash scripts/check-doc-governance.sh`
- [ ] `bash scripts/check-structure-boundaries.sh`
- [x] `bash scripts/check-code-boundaries.sh`
- [ ] `bash scripts/check-phase-tracking.sh`
- [x] `bash scripts/check-branch-lifecycle.sh`
- [ ] `bash scripts/check-contract-gate.sh`
- [ ] `bash scripts/check-fallback-expiry.sh`
- [ ] `bash scripts/check-e2e-gate.sh --mode manifest`

### 前端
- [ ] `cd apps/web && npm install`
- [ ] `cd apps/web && npm run type-check`
- [x] `cd apps/web && npm run test:run -- src/features/chat/runtime/__tests__/chatRuntime.test.ts src/features/chat/components/workbench/ExecutionTimeline.test.tsx src/features/chat/hooks/useChatSend.test.tsx src/features/chat/components/message-feed/MessageFeed.test.tsx src/features/chat/workspace/ChatWorkspaceV2.test.tsx`

### 后端
- [ ] `cd apps/api && pip install -r requirements.txt`
- [ ] `cd apps/api && pytest -q`
- [x] `cd apps/api && /Users/cc/.virtualenvs/scholar-ai-api/bin/python -m pytest -q tests/unit/test_chat_fast_path.py`
- [ ] `cd apps/api && .venv/bin/python -m pytest -q tests/integration/test_imports_chat_contract.py --maxfail=1`

### 共享包
- [ ] `cd packages/types && npm run build`
- [ ] `cd packages/sdk && npm run build`

## 文档是否需要同步
- [x] 不需要
- [ ] 需要，已同步更新

若需要，请说明更新了哪些文档：
- [ ] `docs/specs/architecture/system-overview.md`
- [ ] `docs/specs/architecture/api-contract.md`
- [ ] `docs/specs/domain/resources.md`
- [ ] `docs/specs/development/*`
- [ ] `docs/specs/governance/*`
- [ ] `architecture.md`
- [ ] `AGENTS.md`

## 截图 / 录屏 / 输出
- Frontend: `Test Files 5 passed, Tests 30 passed`
- Backend: `tests/unit/test_chat_fast_path.py 5 passed`
- Gate: `[branch-lifecycle] passed`, `[code-boundaries] passed`, `[pr-template-check] passed`

## 关联 Issue / 背景
- Closes #
- Related #
