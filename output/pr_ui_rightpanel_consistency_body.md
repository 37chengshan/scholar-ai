## 变更目的
- 按前端产品化计划完成聊天工作区可用性改造，统一右侧面板状态来源并降低信息噪声。

## 变更内容
- [x] 前端（apps/web）
- [ ] 后端（apps/api）
- [ ] 文档（docs）
- [ ] 脚本 / 基础设施（scripts / infra）

详细说明：
- 重构右侧面板为 activeRun 驱动：新增运行摘要、验证结果、技术详情折叠区，并保留消息详情模式。
- 升级 EvidencePanel 与 ExecutionTimeline 展示语义，提升证据卡片可读性与流程状态辨识。
- 收敛 ChatWorkspace、MessageFeed、Composer、Layout、ChatMessageCard 的视觉噪声与硬编码色值。

## 影响范围
- 页面：聊天工作区（Chat Workspace）及其右侧状态面板。
- 接口：无接口契约变更。
- 服务/脚本：无。
- 数据/配置：无。

## 风险评估
- 风险等级：低
- 主要风险：右侧面板展示逻辑调整后，极端状态下可能出现信息缺失或排序与用户预期不一致。
- 回滚方式：回滚提交 `6fd5086`。

## 交付单元追踪
- Phase ID: UI Productization Right Panel P0
- Deliverable Unit: Chat Right Panel Consistency + Usability Cleanup
- Migration-Task: N/A
- 未覆盖项: 仅覆盖本次提交涉及的聊天工作区组件，未扩展到其它业务页面。

## 自测清单
### 仓库治理
- [ ] `bash scripts/check-runtime-hygiene.sh tracked`
- [ ] `bash scripts/check-doc-governance.sh`
- [ ] `bash scripts/check-structure-boundaries.sh`
- [ ] `bash scripts/check-code-boundaries.sh`
- [ ] `bash scripts/check-phase-tracking.sh`
- [ ] `bash scripts/check-branch-lifecycle.sh`
- [ ] `bash scripts/check-contract-gate.sh`
- [ ] `bash scripts/check-fallback-expiry.sh`
- [ ] `bash scripts/check-e2e-gate.sh --mode manifest`

### 前端
- [ ] `cd apps/web && npm install`
- [x] `cd apps/web && npm run type-check`
- [ ] `cd apps/web && npm run test:run`

### 后端
- [ ] `cd apps/api && pip install -r requirements.txt`
- [ ] `cd apps/api && pytest -q`
- [ ] `cd apps/api && .venv/bin/python -m pytest -q tests/unit/test_services.py --maxfail=1`
- [ ] `cd apps/api && .venv/bin/python -m pytest -q tests/integration/test_imports_chat_contract.py --maxfail=1`

### 共享包
- [ ] `cd packages/types && npm run build`
- [ ] `cd packages/sdk && npm run build`

## 文档是否需要同步
- [x] 不需要
- [ ] 需要，已同步更新

若需要，请说明更新了哪些文档：
- [ ] `docs/architecture/system-overview.md`
- [ ] `docs/architecture/api-contract.md`
- [ ] `docs/domain/resources.md`
- [ ] `docs/development/*`
- [ ] `docs/governance/*`
- [ ] `architecture.md`
- [ ] `AGENTS.md`

## 截图 / 录屏 / 输出
- `cd apps/web && npm run type-check` 通过（tsc --noEmit）。

## 关联 Issue / 背景
- Closes #
- Related #
