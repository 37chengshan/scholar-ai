# v3.0 Close-out Checklist

最后更新：2026-04-29

## 定义

本清单是 `v3.0` strict close-out 的唯一执行清单。只接受三类改动：

1. 修复阻断主链的问题
2. 补 Phase D/E/F/G 的 Beta 必需实现
3. 完成治理、验证、发布材料收口

## Wave 0 测试输入

| 项目 | 当前状态 | 回填位置 | 备注 |
|---|---|---|---|
| 正在运行的测试批次 | readback-complete | 本文件 / `docs/plans/v3_0/reports/general/2026-04-29_v3_0_strict_closeout_report.md` | 已回读到前端单测、type-check、governance、后端 targeted pytest 结果 |

## 阻断项

| id | phase | owner | status | blocker | 验证命令 | 回填位置 |
|---|---|---|---|---|---|---|
| CO-BLK-001 | B | product-engineering | verified | Search 导入 KB 模态框在长列表/滚动场景下选择不稳定 | `cd apps/web && npm run test -- SearchKnowledgeBaseImportModal useSearchImportFlow SearchResultsPanel` | 本文件 / strict close-out report |
| CO-BLK-002 | C/D | ai-runtime | verified | Search evidence sidecar 后端异常需降级返回，不再 500 静默失败 | `cd apps/api && python3.12 -m pytest -q apps/api/tests/unit/test_search_evidence_api.py apps/api/tests/unit/test_real_world_validation_service.py` | 本文件 / Phase D report |
| CO-BLK-003 | B/C | ai-runtime | verified | `apps/api/app/api/search/library.py` 直接 DB 访问违反 code-boundary | `bash scripts/check-code-boundaries.sh` | 本文件 / governance close-out |
| CO-BLK-004 | FR/Gov | ai-platform | verified | legacy-freeze 需要严格 doc trail 替代 commit marker 补救 | `bash scripts/check-legacy-freeze.sh` | 本文件 / governance close-out |
| CO-BLK-005 | F/Gate | ai-runtime | open | 后端目标单测 `tests/unit/test_services.py` 在 Python 3.12 下失败，当前失败点为 `TaskService.retry_task` 仅允许 `failed` 任务重试，而现有测试夹具仍构造 `pending` 任务 | `cd apps/api && python3.12 -m pytest -q tests/unit/test_services.py --maxfail=1` | 本文件 / strict close-out report |

## Phase Close-out

| phase | closeout_status | owner | 必需输出 | 当前结论 |
|---|---|---|---|---|
| A | implementation-complete / verification-pending | ai-platform | academic gate 跑数、artifact 链、回填台账 | 待读取 Wave 0 与 gate 结果 |
| B | implementation-complete / verification-pending | product-engineering | external search/import 主链、统一 `libraryStatus`/job stage | 主链阻断修复中 |
| C | implementation-complete / verification-pending | ai-runtime | claim/evidence canonical payload、repair contract | sidecar 降级与契约统一中 |
| D | closeout-required | product-engineering | `real_world_validation.{json,summary.json}` + `docs/plans/v3_0/reports/validation/v3_0_real_world_validation.md` | 仍为 `not_ready`，需新一轮完整 run |
| E | closeout-required | product-engineering | async/error/recovery 最小实现 + 文档 | 已建执行文档，待验证 |
| F | closeout-required | web-platform | Dashboard/Search/KB/Read/Chat/Review 产品化收口 | 已建执行文档，待验证 |
| FR | implementation-complete / verification-pending | web-platform | 前端可靠性收口证据 | 待与 E/F 合并验证 |
| G | closeout-required | product-engineering | demo dataset/account、quickstart、known limitations、walkthrough | 已建执行文档，待产物回填 |

## 必过门禁

| gate | status | owner | evidence |
|---|---|---|---|
| `apps/web` type-check | passed | web-platform | `cd apps/web && npm run type-check` |
| `apps/api` Python 3.11+ target tests | failed | ai-runtime | `python3.12 -m pytest -q tests/unit/test_services.py --maxfail=1` -> `TaskService.retry_task` mismatch |
| `bash scripts/check-doc-governance.sh` | passed | ai-platform | `bash scripts/check-governance.sh` |
| `bash scripts/check-structure-boundaries.sh` | passed | ai-platform | `bash scripts/check-governance.sh` |
| `bash scripts/check-code-boundaries.sh` | passed | ai-platform | `bash scripts/check-code-boundaries.sh` |
| `bash scripts/check-governance.sh` | passed | ai-platform | `bash scripts/check-governance.sh` |
| `bash scripts/check-phase-tracking.sh` | passed | ai-platform | `bash scripts/check-phase-tracking.sh` |

## 主链验证

| workflow | status | 证据要求 |
|---|---|---|
| external search -> import -> KB papers -> read | pending | 至少 1 次 fresh-account 成功跑通 |
| read -> chat | pending | 真实回答流 + composer 恢复 |
| KB -> review draft -> review trace | pending | runId 回跳与 review trace 可见 |
| Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review | pending | 至少 1 条完整 full-chain run |

## 发布材料

| item | status | 回填位置 |
|---|---|---|
| Beta quickstart | pending | Phase G plan / strict close-out report |
| Demo dataset | pending | Phase G plan / strict close-out report |
| Demo account | pending | Phase G plan / strict close-out report |
| Known limitations | pending | `docs/plans/v3_0/reports/validation/v3_0_real_world_validation.md` / Phase G |
| 15-30 分钟 walkthrough | pending | Phase G plan / strict close-out report |
