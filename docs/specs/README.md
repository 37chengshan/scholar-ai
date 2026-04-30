# Specs Map

## Purpose

给 agent 和开发者一个稳定的规范/设计入口，集中承载架构、治理、契约、设计与参考资料。

## Scope

覆盖 `docs/specs/` 下全部规范型文档。

## Source of Truth

- 文档总入口：`docs/README.md`
- 计划入口：`docs/plans/README.md`
- 文档校验：`docs/specs/development/documentation-validation.md`

## Rules

- `docs/specs/` 只放规范、架构、设计、治理、参考资料，不放执行中的阶段报告。
- 不再承担 `docs/` 根层兼容入口；根层旧副本必须迁回 `docs/specs/` 的 canonical 位置或删除。
- 架构与契约真源放在 `architecture/`、`domain/`、`contracts/`。
- 流程与治理真源放在 `development/`、`governance/`。
- 兼容入口可以保留，但必须明确指向 canonical 文档。
- 设计思路与 UI 结构稿统一放在 `design/`。

## Required Updates

- 新增规范域：更新本文件和 `docs/README.md`。
- 新增 canonical 规范：同步更新 `scripts/check-doc-governance.sh` 的 required_docs 或 required_references。

## Verification

- `bash scripts/check-doc-governance.sh`
- `bash scripts/check-governance.sh`

## Open Questions

- 是否继续收敛 `engineering/` 兼容入口，最终只保留 canonical 文档。
