## 变更目的
<!-- 这次改动要解决什么问题，最好一句话说清 -->
- 

## 变更内容
<!-- 列出本次实际改了什么，按模块写 -->
- [ ] 前端（apps/web）
- [ ] 后端（apps/api）
- [ ] 文档（docs）
- [ ] 脚本 / 基础设施（scripts / infra）

详细说明：
- 
- 
- 

## 影响范围
<!-- 哪些页面、接口、模块会受影响 -->
- 页面：
- 接口：
- 服务/脚本：
- 数据/配置：

## 风险评估
<!-- 说明可能引入的风险 -->
- 风险等级：低 / 中 / 高
- 主要风险：
- 回滚方式：

## 交付单元追踪
<!-- 与 docs/governance/phase-delivery-ledger.md 保持一致 -->
- Phase ID:
- Deliverable Unit:
- Migration-Task:
- 未覆盖项:

## 自测清单
<!-- 至少勾掉你实际跑过的项，不要全勾 -->
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
- [ ] `cd apps/web && npm run type-check`
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
<!-- 按 README 的 Source of Truth 来判断 -->
- [ ] 不需要
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
<!-- UI 改动、命令行输出、接口响应示例等 -->
- 

## 关联 Issue / 背景
- Closes #
- Related #
