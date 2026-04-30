# ScholarAI

ScholarAI 是一个面向学术阅读、知识管理与 academic-grade RAG 工作流的全栈工程化仓库。仓库的核心目标是让真实业务代码、规范文档、治理门禁和多 Agent 协作保持单一真源，而不是演化出平行实现与失真的设计文档。

## Purpose

- 固化架构边界，确保真实业务代码只落在 `apps/web` 与 `apps/api`。
- 标准化跨端契约，让 API、typed client、前端页面与异步任务在同一语义上演进。
- 保持文档与代码同构，避免“系统已经变了但规范还停在旧口径”。
- 通过治理脚本、测试门禁与 Phase 台账维持长期可维护性。

## Scope

本 README 适用于 ScholarAI 根目录下的整体仓库协作与交付约束。

- `apps/web/`: 前端真实代码主路径。
- `apps/api/`: 后端真实代码主路径。
- `infra/`: Docker Compose、Nginx、部署与基础设施脚本。
- `tools/`: 辅助开发工具与脚手架。
- `packages/`: 共享类型、SDK 与预留共享模块。
- `docs/specs/`: agent 可读规范、架构、治理、设计与参考资料。
- `docs/plans/`: 计划、研究、评测、归档与阶段执行材料。

## Source of Truth

架构与契约：

- `docs/specs/architecture/system-overview.md`
- `docs/specs/architecture/api-contract.md`
- `docs/specs/domain/resources.md`
- `architecture.md`
- `AGENTS.md`

研发与治理：

- `docs/specs/development/coding-standards.md`
- `docs/specs/development/testing-strategy.md`
- `docs/specs/development/pr-process.md`
- `docs/specs/development/documentation-validation.md`
- `docs/specs/governance/code-boundary-baseline.md`
- `docs/specs/governance/harness-engineering-playbook.md`
- `docs/specs/governance/phase-delivery-ledger.md`
- `docs/specs/governance/branch-lifecycle-policy.md`
- `docs/specs/governance/governance-kpi-spec.md`
- `docs/specs/governance/e2e-failure-handbook.md`

## Rules

1. 根目录禁止提交运行时产物、临时日志、`*.pid`、`cookies.txt` 与测试废弃物。
2. 新文档只允许进入 `docs/specs/` 或 `docs/plans/`，禁止新增平铺的 `tmp/`、`legacy/`、`doc/` 等并行目录。
3. 除 `apps/web` 与 `apps/api` 外，禁止新开第三条真实业务实现路径。
4. 前端页面不得直接拼接未文档化接口；接口形态变化必须同步更新 `docs/specs/architecture/api-contract.md`。
5. 后端路由层不得承载复杂业务编排；service 层是后端行为真源。
6. 资源状态、异步任务状态与运行轨迹变更必须同步更新 `docs/specs/domain/resources.md` 与相关治理文档。
7. 项目根层文档只允许保留 `README.md`、`AGENTS.md`、`architecture.md`；新增仓库级说明必须并入这三份之一，不得再平铺新的根级 `.md`。
8. `docs/` 根层只允许保留 `README.md`、`specs/`、`plans/`；任何报告、研究、指南、兼容副本都必须收纳到这两个子树内。

## Required Updates

以下变化必须在同一轮交付内同步文档：

- 架构边界变化：更新 `docs/specs/architecture/system-overview.md` 与 `architecture.md`
- API 形态变化：更新 `docs/specs/architecture/api-contract.md`
- 资源状态变化：更新 `docs/specs/domain/resources.md`
- 测试或文档治理策略变化：更新 `docs/specs/development/testing-strategy.md` 与 `docs/specs/development/documentation-validation.md`
- Phase 交付状态变化：更新 `docs/plans/PLAN_STATUS.md` 与 `docs/specs/governance/phase-delivery-ledger.md`

## Verification

环境要求：

- Node.js 20+
- Python 3.11+
- Docker / Docker Compose

常用验证命令：

```bash
# 完整验证
bash scripts/verify/run-all.sh

# 快速本地验证
VERIFY_QUICK=1 bash scripts/verify/run-all.sh

# 治理与目录边界
bash scripts/check-runtime-hygiene.sh tracked
bash scripts/check-doc-governance.sh
bash scripts/check-structure-boundaries.sh
bash scripts/check-code-boundaries.sh
```

## Open Questions

- `packages/` 何时开始承接稳定共享逻辑，而不是只作为边界预留。
- 是否需要统一 SDK 层进一步收敛 `apps/web` 与 `apps/api` 的共享契约。
- 随着更多 Phase 落地，是否需要把治理回填进一步自动化到 PR 或 CI 层。
