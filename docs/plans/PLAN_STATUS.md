# 计划状态总览

最后更新：2026-04-17

## 使用规则

1. 本文件是 docs/plans 下计划状态唯一真源。
2. 所有 active 计划必须同步更新：status、last_verified_at、evidence_commits。
3. 每次代码合并后，必须在 24 小时内回填对应计划状态。
4. 同主题计划只能有一份 active，其他必须标记 superseded。

## 状态定义

- `not-started`: 尚未开始
- `in-progress`: 正在推进
- `blocked`: 被依赖/资源阻塞
- `done`: 已完成并有证据
- `superseded`: 被新计划替代，不再执行

## 活跃计划面板

| 计划 | owner | status | depends_on | last_verified_at | evidence_commits | notes |
|---|---|---|---|---|---|---|
| PR3_执行方案_物理迁移到_apps | platform | done | - | 2026-04-17 | historical-pr3-commit-to-backfill | 物理迁移已完成，后续只维护 |
| PR4_迁移后稳定化执行清单 | platform | done | PR3 | 2026-04-17 | historical-pr4-commit-to-backfill | 稳定化与门禁已落地 |
| PR5_共享契约收口_与_前端工作台可用性方案 | app-foundation | in-progress | PR4 | 2026-04-17 | a07490b,0a123c9 | 作为共享契约与工作台唯一 active 主计划 |
| PR6_共享契约收口_与_前端工作台可用性方案 | app-foundation | superseded | PR5 | 2026-04-17 | - | 已被 PR5 计划替代，停止执行 |
| PR6_执行优化方案 | app-foundation | superseded | PR5 | 2026-04-17 | - | 作为历史优化记录，不再单独执行 |
| PR7_PR8_Chat稳定性_AgentNative_RAG升级实施方案 | ai-runtime | in-progress | PR5,PR10 | 2026-04-17 | wip-pr7-pr8,wip-review-2026-04-17 | 本轮 PR7 P7-A/B/C 与 PR8 P8-A 已完成并通过严格复核 |
| PR10_KB_Chat_Search_workspace_分层与稳定化方案 | web-platform | in-progress | PR5 | 2026-04-17 | 9a7332e,9208b73,cecfccf,wip-review-2026-04-17 | 第一轮收尾清单已补录严格复核结果 |
| PR19_上传链路收口_与_完整上传体验重做计划_v3 | app-foundation | in-progress | PR5 | 2026-04-17 | wip-pr19-upload-workspace | 上传链路收口与工作台体验重做推进中 |
| PR18_Celery_ImportPipeline_Stability_Refactor_Plan | app-foundation | superseded | PR19_上传链路收口_与_完整上传体验重做计划_v3 | 2026-04-18 | - | 已并入 PR19 上传链路主计划，不再单独执行 |
| PR20_UI截图细节还原方案 | web-platform | superseded | PR10_KB_Chat_Search_workspace_分层与稳定化方案 | 2026-04-18 | - | 已被统一工作台分层与稳定化计划覆盖 |
| PR20_前端杂志风美化与性能优化_深度落实方案 | web-platform | superseded | PR10_KB_Chat_Search_workspace_分层与稳定化方案 | 2026-04-18 | - | 已合并进入现行前端治理与工作台主线 |
| PR11_Harness_Observability_文件级实施方案 | ai-platform | done | PR10 | 2026-04-17 | 89a9d9a | 已完成，进入维护态 |
| PR12_Benchmark_基线评测_文件级实施方案 | ai-platform | done | PR11 | 2026-04-17 | 84fd597 | 已完成，进入阈值维护态 |

## 回填模板

每次执行完成后按如下格式附加记录：

```markdown
### 2026-04-17 PR7 P7-A 回填
- status: done
- owner: ai-runtime
- changed_files:
  - apps/api/app/core/docling_service.py
  - apps/api/tests/unit/test_docling_service.py
- verification:
  - cd apps/api && pytest -q tests/unit/test_docling_service.py
  - bash scripts/check-governance.sh
- evidence_commits:
  - <commit-hash>
- reviewer:
  - gsd-code-reviewer (summary link or note)
```