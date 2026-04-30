# Post-migration Stabilization Checklist

## Purpose

记录 PR4（迁移后稳定化）交付范围、验证结果与残留风险，用于评审与后续追踪。

## Scope

适用于 apps/web 与 apps/api 作为真实代码主路径后的仓库稳定化治理。

## Checklist

- [ ] 已删除 tracked runtime artifacts（logs/archive、test-results、uploads、apps/web/test-results）
- [ ] 已删除 nested legacy snapshot（scholar-ai/**）
- [ ] 已新增 runtime hygiene 脚本与本地清理脚本
- [ ] 已接入 governance 与 test workflows
- [ ] 已更新 README、AGENTS、migration docs、testing strategy、boundary baseline

## Verification Result

执行命令：

```bash
bash scripts/check-runtime-hygiene.sh tracked
bash scripts/check-governance.sh
bash scripts/verify-all-phases.sh
cd apps/web && npm run type-check && npm run test:run
cd apps/api && pytest -q tests/unit/test_services.py --maxfail=1
cd apps/api && pytest -q tests/test_unified_search.py --maxfail=1
```

结果记录：

- runtime hygiene:
- governance:
- phase verification:
- web type-check/tests:
- api tests:

## CI Result

- Governance Baseline:
- Test Unified Backend:
- PR merge state:

## Residual Risks

- [ ] 无
- [ ] 有（请列出具体目录/脚本/流程风险）

## Next Steps

- 将 packages/types 与 packages/sdk 的首批共享契约抽取纳入下一里程碑。
- 进入 KB Workspace 与 Chat Workspace 重构。
