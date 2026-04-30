## 变更目的
- 修复 retrieval benchmark 中 section_miss 与 chunk_hit=0，完成 section/chunk 对齐并提供可追踪失败分类。

## 变更内容
- [ ] 前端（apps/web）
- [x] 后端（apps/api）
- [ ] 文档（docs）
- [x] 脚本 / 基础设施（scripts / infra）

详细说明：
- 新增 canonical section 标准化模块，统一 raw/alias 到固定 taxonomy。
- 新增稳定 chunk_id 生成模块，基于 paper/page/section/span 生成确定性 ID。
- 在 Docling chunk 与 Storage 入库链路补齐 normalized section path、span、anchor、chunk_id 元数据。
- 升级 scripts/eval_retrieval.py：section 规范化比较、exact/overlap/anchor chunk hit、failure buckets。
- 新增并扩展单测覆盖 section alias、chunk_id 稳定性、chunk hit 三种命中、failure bucket 分类。

## 影响范围
- 页面：无
- 接口：无新增接口，检索评估脚本输出字段增加
- 服务/脚本：apps/api 文本切块与存储元数据、scripts/eval_retrieval.py
- 数据/配置：向量内容 metadata 字段更完整（兼容新增字段）

## 风险评估
- 风险等级：中
- 主要风险：历史数据缺失新 metadata 时评估脚本将走兼容提取路径，指标可能与旧版本口径存在差异。
- 回滚方式：回滚本 PR 提交，恢复旧版 chunk 匹配与 section 逻辑。

## 交付单元追踪
- Phase ID: N/A
- Deliverable Unit: retrieval benchmark alignment
- Migration-Task: N/A
- 未覆盖项: 未执行全量后端回归，仅执行本次改动相关定向测试与门禁。

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
- [ ] `cd apps/web && npm run test:run`

### 后端
- [ ] `cd apps/api && pip install -r requirements.txt`
- [ ] `cd apps/api && pytest -q`
- [x] `cd apps/api && /Users/cc/.virtualenvs/scholar-ai-api/bin/python -m pytest -q tests/unit/test_section_chunk_alignment.py tests/unit/test_eval_retrieval_harness.py tests/unit/test_pr7_storage_evidence.py`
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
- `13 passed in 5.44s`（定向单测）
- `[branch-lifecycle] passed`
- `[code-boundaries] passed`

## 关联 Issue / 背景
- Closes #
- Related #
