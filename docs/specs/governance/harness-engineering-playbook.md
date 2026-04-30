# Harness Engineering Playbook

## Purpose

将 OpenAI Harness Engineering 的方法落地到 ScholarAI，形成可执行、可验证、可迭代的工程治理框架。

## Scope

覆盖文档系统、代码结构、CI 门禁、评审反馈、熵治理与持续重构流程，适用于 apps/web、apps/api 与跨层契约协作。

## Source of Truth

- 架构总览：docs/specs/architecture/system-overview.md
- API 契约：docs/specs/architecture/api-contract.md
- 资源模型：docs/specs/domain/resources.md
- 编码规范：docs/specs/development/coding-standards.md
- PR 流程：docs/specs/development/pr-process.md
- 测试策略：docs/specs/development/testing-strategy.md
- Agent 地图：AGENTS.md
- 治理脚本：scripts/check-governance.sh

## Rules

核心治理原则（映射 Harness Engineering）：

1. 仓库是唯一记录系统
- 所有关键决策必须沉淀到版本化文档，不依赖聊天记录或口头约定。
- AGENTS.md 只作为地图，不承载百科式细节。

2. 约束先于实现
- 先定义边界与不变量，再允许实现自由。
- 通过脚本和 CI 强制执行边界，而非依赖人工记忆。

3. 可读性优先
- 人和智能体都需要可导航结构。
- 文档采用统一骨架，代码按分层与依赖方向组织。

4. 反馈闭环优先
- 每次变更必须包含：校验 -> 评审 -> 修复 -> 回归。
- 失败信号优先转化为新规则、新脚本或新文档。

5. 熵治理持续化
- 技术债按小步高频清理，不堆积到大规模返工。
- 发现重复模式后，优先提炼成共享规范或自动化检查。

分层治理模型（ScholarAI 版）：

- 文档层：统一骨架 + 交叉链接 + 路径收敛。
- 结构层：目录边界、禁止平行实现、禁止根目录运行时污染。
- 代码层：前后端分层与命名一致性、契约同步。
- 流程层：PR 模板、Issue 模板、CI 必过门禁。

治理指标（建议按周追踪）：

- 文档完整率：核心文档骨架齐全率（目标 100%）。
- 文档有效率：本地链接有效率（目标 100%）。
- 结构合规率：边界校验通过率（目标 100%）。
- 契约同步率：API 变更后契约同步比例（目标 100%）。
- 回归响应时长：发现治理问题到修复合入时间（目标逐周下降）。

## Required Updates

- 新增治理规则：同步更新 docs/specs/development/coding-standards.md 与 scripts/check-*.sh。
- 新增校验门禁：同步更新 .github/workflows/governance-baseline.yml。
- 调整文档骨架：同步更新 docs/specs/development/documentation-validation.md。
- 调整架构边界：同步更新 docs/specs/architecture/system-overview.md 与 AGENTS.md。

## Verification

最小验证：

- bash scripts/check-doc-governance.sh
- bash scripts/check-structure-boundaries.sh
- bash scripts/check-governance.sh

回归验证：

- cd apps/web && npm run type-check
- cd apps/api && pytest -q tests/unit --maxfail=1

CI 验证：

- governance-baseline workflow 通过
- PR 模板中的治理验证项已填写

## Open Questions

- 是否引入定时 doc-gardening 任务，自动提交文档过期修复 PR。
- 是否将结构边界检查扩展到 import 依赖方向的静态分析。
- 是否将治理指标接入仪表盘，支持趋势告警。
