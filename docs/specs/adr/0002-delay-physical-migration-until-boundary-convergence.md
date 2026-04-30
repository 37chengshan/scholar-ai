# ADR 0002: Delay Physical Migration Until Boundary Convergence

- Status: Accepted
- Date: 2026-04-16

## Context

当前仓库已建立 apps/* 和 packages/* 逻辑映射，但真实业务代码仍在 frontend 与 backend-python。若在边界未收口前直接做物理迁移，会叠加目录搬迁、分层重构与契约修复三类风险。

## Decision

在当前里程碑执行以下策略：

1. 保持 frontend 与 backend-python 作为唯一真实代码主路径。
2. apps/web 与 apps/api 仅保留逻辑映射说明，不承接业务实现。
3. 先完成前后端边界收口（hooks、services、schemas/repositories、router 薄化）。
4. 待契约稳定后，再进行 apps/* 的物理迁移。

## Consequences

### Positive

- 降低一次性重构风险。
- 先解决职责分层与契约漂移，后续迁移更接近机械搬运。
- 治理脚本可更稳定地约束目录边界。

### Negative

- 逻辑映射与物理路径短期并存，需要更严格文档与脚本约束。

## Exit Criteria For Physical Migration

执行物理迁移前应满足：

1. 前端共享 hooks 无重复实现。
2. 后端 schemas/repositories 边界生效并有样板改造落地。
3. search 单一入口收敛完成。
4. API 契约与实现一致（分页与响应壳统一）。
5. 治理脚本与 CI 连续稳定通过。
