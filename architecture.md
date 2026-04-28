# ScholarAI Architecture Map

## Purpose

提供仓库级架构导航入口，统一连接系统边界、API 契约、资源模型、开发规范与 ADR。

## Scope

覆盖 scholar-ai 根目录下的前后端、异步任务、基础设施与治理文档入口。

## Source of Truth

- 系统总览：docs/architecture/system-overview.md
- API 契约：docs/architecture/api-contract.md
- 共享契约（types）：packages/types
- 共享 SDK：packages/sdk
- 资源模型：docs/domain/resources.md
- v2.0 收尾标准：docs/reports/2026-04-28_v2_0_closeout_pass_framework.md
- 开发规范：docs/development/coding-standards.md
- 文档校验：docs/development/documentation-validation.md
- PR 流程：docs/development/pr-process.md
- 测试策略：docs/development/testing-strategy.md
- Harness 治理：docs/governance/harness-engineering-playbook.md
- Phase 台账：docs/governance/phase-delivery-ledger.md
- 分支生命周期：docs/governance/branch-lifecycle-policy.md
- 治理 KPI：docs/governance/governance-kpi-spec.md
- E2E 失败手册：docs/governance/e2e-failure-handbook.md
- ADR 索引：docs/adr

## Rules

- architecture.md 只做导航，不承载实现细节。
- 结构变化时优先更新对应子文档，再回链到本文件。
- 禁止在本文件复制粘贴完整规范，避免双份真相。
- Phase 5 起，KB 综述草稿能力以 `ReviewDraft/ReviewRun` 为真源，边界定义统一落在 system-overview 与 api-contract。
- Phase 6 起，v2.0 发版门禁以 `scripts/evals/phase6_gate.py` + `/analytics` artifact-backed eval surface 为真源。

## Required Updates

- 新增子系统或边界变化：更新 docs/architecture/system-overview.md 后同步更新本文件链接。
- 新增契约文档：加入本文件链接索引。

## Verification

- 检查所有链接路径存在且可访问。
- 抽查本文件与 docs/architecture/system-overview.md 的边界描述一致。
- 运行 bash scripts/check-doc-governance.sh 验证文档结构与本地链接。

## Open Questions

- 是否将 architecture.md 拆分为“运行时视图”和“代码组织视图”两层导航。
