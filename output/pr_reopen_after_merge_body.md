## 变更目的
- 重新为 `feat/ui-sidebar-notes-chat-v2` 分支创建可审阅 PR，确保分支上的最新改动进入标准评审流程。

## 变更内容
- [x] 前端（apps/web）
- [x] 后端（apps/api）
- [x] 文档（docs）
- [x] 脚本 / 基础设施（scripts / infra）

详细说明：
- 包含 Chat 页面稳定性与 fast path 相关改动及对应测试补齐。
- 包含 retrieval benchmark 相关对齐改动与报告脚本/文档更新。
- 包含 settings/search 等联动改动（详见本 PR diff）。

## 影响范围
- 页面：Chat、Settings、Search
- 接口：chat stream / retrieval 评估相关链路
- 服务/脚本：retrieval matrix、summary、preflight、dataset prepare
- 数据/配置：`.env.example` / `.env.docker` 与检索配置项

## 风险评估
- 风险等级：中
- 主要风险：分支累计改动较多，回归面较大。
- 回滚方式：按 commit 维度回滚，或整 PR 回滚。

## 交付单元追踪
- Phase ID: chat-retrieval-hardening
- Deliverable Unit: branch-pr-reopen
- Migration-Task: N/A
- 未覆盖项: 未执行全量 e2e，仅完成关键定向测试与门禁。

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
- [ ] 不需要
- [x] 需要，已同步更新

若需要，请说明更新了哪些文档：
- [ ] `docs/architecture/system-overview.md`
- [ ] `docs/architecture/api-contract.md`
- [ ] `docs/domain/resources.md`
- [ ] `docs/development/*`
- [ ] `docs/governance/*`
- [ ] `architecture.md`
- [x] `AGENTS.md`

## 截图 / 录屏 / 输出
- FE 定向测试：5 files / 30 tests passed
- BE 定向测试：test_chat_fast_path.py 5 passed
- 门禁：branch-lifecycle / code-boundaries / pr-template-check passed

## 关联 Issue / 背景
- Closes #
- Related #
