# v3.6 Release Gate Report

## Gate Commands

- `bash scripts/check-doc-governance.sh` -> passed
- `bash scripts/check-structure-boundaries.sh` -> passed
- `bash scripts/check-code-boundaries.sh` -> passed
- `bash scripts/check-runtime-hygiene.sh tracked` -> passed
- `bash scripts/check-governance.sh` -> passed

## Build/Test Signals

- Frontend: `cd apps/web && npm run type-check` -> passed
- Frontend focused tests: 3/3 passed（EvidencePanel + text-layout）
- Backend focused tests: 3/3 passed（trace/error contract）

## Observations

- 初次治理检查曾因 contract 文档未同步失败；补齐 API/resource 文档后已通过。
- e2e gate 本次由治理脚本完成 manifest 校验，未执行完整浏览器用例矩阵。

## Verdict

- P4/P5 交付对应的发布门禁已达成当前基线：`PASS`。
- 若进入正式 RC 发布，建议补跑全量 `tests/e2e` 关键路径并归档截图/录像。
