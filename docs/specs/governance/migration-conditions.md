# Migration Conditions

## Purpose

定义物理迁移完成后的稳定化守则，防止 legacy 路径、运行时产物和本地环境再次回流主线。

## Scope

适用于 apps/web 与 apps/api 已成为真实代码主路径后的持续治理与 PR 准入。

## Migration Completed Baseline

1. apps/web 与 apps/api 为唯一真实代码主路径。
2. 根目录不再保留 frontend/backend-python 平行实现目录。
3. 治理脚本、CI 与文档均已切到 apps/* 路径。

## Stabilization Guardrails

1. Do not reintroduce legacy paths：禁止恢复 frontend、backend-python、scholar-ai/** 等旧路径实现。
2. Do not commit local environments/reports：禁止提交 venv、coverage、__pycache__、test-results、logs/archive、uploads。
3. Runtime hygiene must pass：每次结构或流程变更必须通过 `bash scripts/check-runtime-hygiene.sh tracked`（本地深度清理用 strict）。
4. Governance chain must pass：`check-doc-governance`、`check-structure-boundaries`、`check-code-boundaries`、`check-governance` 必须全部通过。

## Verification Checklist

- `bash scripts/check-runtime-hygiene.sh tracked`
- `bash scripts/check-doc-governance.sh`
- `bash scripts/check-structure-boundaries.sh`
- `bash scripts/check-code-boundaries.sh`
- `bash scripts/check-governance.sh`
- `bash scripts/verify-all-phases.sh`

## Exit Rule

连续两个迭代周期无 runtime artifact 回流、所有治理门禁稳定通过后，可进入下一阶段（packages 共享契约抽取与业务工作流重构）。
