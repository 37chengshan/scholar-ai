# Migration Conditions

## Purpose

记录 PR3 物理迁移完成后的边界状态与持续门禁，防止回退到双主路径。

## Scope

适用于 apps/web 与 apps/api 成为唯一真实代码主路径后的开发与治理准入。

## Mandatory State

1. 前端共享 hook 无重复实现：`apps/web/src/hooks` 与 `apps/web/src/app/hooks` 不允许同名文件。
2. 后端分层收口完成：`apps/api/app/schemas` 与 `apps/api/app/repositories` 已落地并被主链路使用。
3. 搜索入口单一化：`apps/api/app/api/search.py` 已下线，统一走 `apps/api/app/api/search/`。
4. API 契约收口：列表响应统一 `data.items + meta`，分页统一 `limit + offset`，前端只消费 camelCase。
5. 治理门禁稳定：`check-doc-governance`、`check-structure-boundaries`、`check-code-boundaries`、`check-governance` 全通过。
6. apps 目录为唯一真实代码主路径：禁止在根级恢复 `frontend` 或 `backend-python` 业务实现。

## Verification Checklist

- `bash scripts/verify-phase0.sh`
- `bash scripts/verify-phase1.sh`
- `bash scripts/verify-phase2.sh`
- `bash scripts/verify-phase3.sh`
- `bash scripts/verify-phase4.sh`
- `bash scripts/verify-phase5.sh`

## Guardrail Rule

任何 PR 若引入旧路径平行实现（`frontend` 或 `backend-python`）应直接判定为结构违规并阻断合并。
