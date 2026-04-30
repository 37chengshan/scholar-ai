# PR Process

## Purpose

建立统一分支、提交、评审与合并流程，确保结构、契约与验证同步落地。

## Scope

适用于 scholar-ai 仓库全部 PR。

## Source of Truth

- 编码规范：docs/specs/development/coding-standards.md
- 文档校验：docs/specs/development/documentation-validation.md
- API 契约：docs/specs/architecture/api-contract.md
- 测试策略：docs/specs/development/testing-strategy.md
- PR 模板：.github/pull_request_template.md
- PR 模板校验：docs/specs/development/pr-template-enforcement.md
- Phase 台账：docs/specs/governance/phase-delivery-ledger.md
- 分支生命周期：docs/specs/governance/branch-lifecycle-policy.md
- Fallback 台账：docs/specs/governance/fallback-register.yaml

## Rules

分支命名：

- feat/<scope>-<summary>
- fix/<scope>-<summary>
- chore/<scope>-<summary>
- docs/<scope>-<summary>

分支生命周期：

- 所有分支必须登记 lifecycle_state（created/active/review-ready/merged/superseded/archived）。
- active 分支超过 14 天无更新将触发阻断。
- superseded 分支必须标注 replacement_branch。

commit 规范：

- 采用 conventional commits：feat/fix/refactor/docs/test/chore。
- 每个 commit 聚焦单一目的，避免混合式大提交。

PR 描述模板要求：

- 问题背景与目标
- 变更清单
- 风险与回滚
- 验证命令与结果
- 契约与文档同步情况
- Phase ID 与 Deliverable Unit
- 未覆盖项与风险等级
- fallback 引入与退役计划（如适用）
- agent 或本地脚本创建 PR 时必须通过 `scripts/pr_create_with_template_check.sh`
- CI 在 pull_request 事件下强制运行 `scripts/check-pr-template-body.sh`
- 空模板、未勾选实际验证项、未明确文档同步选项的 PR 必须阻断

Review checklist：

- 是否违反分层边界
- 是否引入平行实现目录
- 是否更新了受影响文档
- 是否满足最小验证要求

API 变更必须同步更新：

- docs/specs/architecture/api-contract.md
- docs/specs/domain/resources.md
- 必要时补充 docs/adr

合并前最小验证要求：

- 文档治理变更至少通过文档结构与链接校验。
- 结构治理变更至少通过边界校验。
- 代码治理变更至少通过代码层边界校验。
- 前端变更至少通过 type-check
- 后端变更至少通过 pytest 冒烟（tests/unit/test_services.py）
- 文档治理变更至少通过核心文档存在性检查
- 契约表面变更必须通过 contract gate（并同步 api-contract/resources）。
- fallback 引入必须写入 fallback-register，且通过到期检查。
- 关键链路必须通过 E2E gate 后才允许合并。
- import/chat 契约变更必须通过 `tests/integration/test_imports_chat_contract.py`。

## Required Updates

- 调整审查门禁：同步更新 .github/pull_request_template.md。
- 调整验证命令：同步更新 docs/specs/development/testing-strategy.md。
- 调整分支生命周期阈值：同步更新 docs/specs/governance/branch-lifecycle-policy.md 与 scripts/check-branch-lifecycle.sh。

## Verification

- 抽样检查最近 PR 是否按模板提供验证结果。
- 抽样检查 API 变更 PR 是否同步更新契约文档。
- 抽样检查 branch 与 commit 命名是否符合规则。
- 抽样检查结构治理 PR 是否附带治理脚本结果。
- 运行 bash scripts/check-phase-tracking.sh。
- 运行 bash scripts/check-branch-lifecycle.sh。
- 运行 bash scripts/check-contract-gate.sh。
- 运行 bash scripts/check-fallback-expiry.sh。
- 运行 `cd apps/api && .venv/bin/python -m pytest -q tests/integration/test_imports_chat_contract.py --maxfail=1`。

## Open Questions

- 是否对高风险 PR 增加强制双审与安全审查。
- 是否引入自动校验 PR 标题与 commit 前缀。
