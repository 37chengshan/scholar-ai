# PR Process

## Purpose

建立统一分支、提交、评审与合并流程，确保结构、契约与验证同步落地。

## Scope

适用于 scholar-ai 仓库全部 PR。

## Source of Truth

- 编码规范：docs/development/coding-standards.md
- 文档校验：docs/development/documentation-validation.md
- API 契约：docs/architecture/api-contract.md
- 测试策略：docs/development/testing-strategy.md
- PR 模板：.github/PULL_REQUEST_TEMPLATE.md

## Rules

分支命名：

- feat/<scope>-<summary>
- fix/<scope>-<summary>
- chore/<scope>-<summary>
- docs/<scope>-<summary>

commit 规范：

- 采用 conventional commits：feat/fix/refactor/docs/test/chore。
- 每个 commit 聚焦单一目的，避免混合式大提交。

PR 描述模板要求：

- 问题背景与目标
- 变更清单
- 风险与回滚
- 验证命令与结果
- 契约与文档同步情况

Review checklist：

- 是否违反分层边界
- 是否引入平行实现目录
- 是否更新了受影响文档
- 是否满足最小验证要求

API 变更必须同步更新：

- docs/architecture/api-contract.md
- docs/domain/resources.md
- 必要时补充 docs/adr

合并前最小验证要求：

- 文档治理变更至少通过文档结构与链接校验。
- 结构治理变更至少通过边界校验。
- 代码治理变更至少通过代码层边界校验。
- 前端变更至少通过 type-check
- 后端变更至少通过 pytest 冒烟（tests/unit/test_services.py）
- 文档治理变更至少通过核心文档存在性检查

## Required Updates

- 调整审查门禁：同步更新 .github/PULL_REQUEST_TEMPLATE.md。
- 调整验证命令：同步更新 docs/development/testing-strategy.md。

## Verification

- 抽样检查最近 PR 是否按模板提供验证结果。
- 抽样检查 API 变更 PR 是否同步更新契约文档。
- 抽样检查 branch 与 commit 命名是否符合规则。
- 抽样检查结构治理 PR 是否附带治理脚本结果。

## Open Questions

- 是否对高风险 PR 增加强制双审与安全审查。
- 是否引入自动校验 PR 标题与 commit 前缀。
