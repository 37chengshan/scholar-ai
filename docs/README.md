# ScholarAI Docs Map

`docs/` is the single documentation root for the product workspace.

## Current Focus

当前主线是 `v3.0`。阅读顺序统一如下：

1. `docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md`
2. `docs/plans/PLAN_STATUS.md`
3. `docs/plans/v3_0/active/phase_a/07_v3_0A_execution_plan.md`
4. `docs/plans/v3_0/reports/official_rag_evaluation/`

如果某份旧计划、旧报告与上述主线冲突，以 `v3.0` 计划链路为准。

## Structure

- `specs/`
  - agent 读取的规范、架构、设计、治理与参考资料真源
- `plans/`
  - 按版本组织的计划、研究、报告、归档与状态真源

## Top-level Contract

`docs/` 根层是强约束目录，只允许存在以下三个入口：

1. `docs/README.md`
2. `docs/specs/`
3. `docs/plans/`

以下内容不允许继续直接放在 `docs/` 根层：

- 报告、研究、审计、验证结论
- 旧的 `architecture/`、`domain/`、`governance/` 兼容副本目录
- 产品指南、实现说明、临时材料

落位规则固定为：

- 规范、架构、设计、治理、参考资料 -> `docs/specs/`
- 计划、研究、评测、报告、归档 -> `docs/plans/`

## Canonical Paths

核心治理与架构文档统一使用这些 canonical 路径：

- `docs/specs/architecture/system-overview.md`
- `docs/specs/architecture/api-contract.md`
- `docs/specs/design/frontend/DESIGN_SYSTEM.md`
- `docs/specs/domain/resources.md`
- `docs/specs/development/coding-standards.md`
- `docs/specs/development/documentation-validation.md`
- `docs/specs/development/pr-process.md`
- `docs/specs/development/testing-strategy.md`
- `docs/specs/governance/code-boundary-baseline.md`
- `docs/specs/governance/core-boundary-baseline.md`
- `docs/specs/governance/harness-engineering-playbook.md`

兼容入口仅允许保留在 `docs/specs` 内的旧域名子目录，例如：

- `docs/specs/architecture/resources.md`
- `docs/specs/engineering/coding-standards.md`
- `docs/specs/engineering/pr-process.md`
- `docs/specs/engineering/testing-baseline.md`

这些文件只能指向 canonical 文档，不能继续扩写新规则。

## Routing Rules

- 新项目文档放到 `docs/`，不要再新增根级文档目录。
- `docs/` 根层只保留 `README.md`、`specs/`、`plans/`，不再新增第三个文档大目录。
- 规范、架构、设计、治理、参考资料统一放到 `docs/specs/`。
- 执行计划、研究过程、评测报告、归档材料统一放到 `docs/plans/`。
- 当前进行中的产品主线必须同时能在 `docs/README.md` 和 `docs/plans/README.md` 被定位到。
- 新执行计划先登记到 `docs/plans/PLAN_STATUS.md`，再补详细计划文档。
- 版本化执行材料统一落到 `docs/plans/<version>/{active,complete,search,reports}`。
- `active/` 下按 phase 或主题继续细分，例如 `active/phase_a/`、`active/phase1/`。
- 已完成或被替代的旧计划放到 `docs/plans/archive/complete/`，历史杂项报告放到 `docs/plans/archive/reports/`。
- 第三方资料、导入材料放到 `docs/specs/reference/`。
- Runtime outputs, coverage, logs, cookies, and generated artifacts do not belong in `docs/`.
- Every new ADR must be added under `docs/specs/adr/` with incremental numbering.

## Governance Commands

- `bash scripts/check-doc-governance.sh`
- `bash scripts/check-structure-boundaries.sh`
- `bash scripts/check-code-boundaries.sh`
- `bash scripts/check-governance.sh`
