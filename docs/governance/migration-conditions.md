# Migration Conditions

## Purpose

定义从当前真实路径 frontend/backend-python 迁移到 apps/web 与 apps/api 的前置条件，避免“边改边搬”导致的高风险迁移。

## Scope

适用于 ScholarAI 下一阶段物理迁移决策与 PR 准入。

## Mandatory Conditions

1. 前端共享 hook 无重复实现：`frontend/src/hooks` 与 `frontend/src/app/hooks` 不允许同名文件。
2. 后端分层收口完成：`backend-python/app/schemas` 与 `backend-python/app/repositories` 已落地并被主链路使用。
3. 搜索入口单一化：`backend-python/app/api/search.py` 已下线，统一走 `backend-python/app/api/search/`。
4. API 契约收口：列表响应统一 `data.items + meta`，分页统一 `limit + offset`，前端只消费 camelCase。
5. 治理门禁稳定：`check-doc-governance`、`check-structure-boundaries`、`check-code-boundaries`、`check-governance` 全通过。
6. apps 目录保持逻辑映射身份：`apps/web`、`apps/api` 不承接业务源码。

## Verification Checklist

- `bash scripts/verify-phase0.sh`
- `bash scripts/verify-phase1.sh`
- `bash scripts/verify-phase2.sh`
- `bash scripts/verify-phase3.sh`
- `bash scripts/verify-phase4.sh`
- `bash scripts/verify-phase5.sh`

## Exit Rule

仅当上述条件连续通过并在同一 PR 验证成功时，才允许进入物理迁移执行阶段。
