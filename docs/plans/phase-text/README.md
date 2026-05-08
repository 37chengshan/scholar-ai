# Phase-text

## Purpose

`phase-text/` 用于存放跨版本的事实型盘点材料，以及这条文档线自身的维护契约。

这里的文档不是新的执行计划，也不是替代 `PLAN_STATUS.md` 的状态真源，而是把：

1. 版本文档中的已交付能力
2. 仓库真实代码入口
3. 现有自动化测试与 closeout 证据

压成一份可审阅、可追踪、可补漏的功能事实报告。

## Rules

1. 只写“仓库里已经实现且当前仍可测试/可验证”的能力。
2. 必须区分：
   - 文档显式声明的能力
   - 代码已经实现但版本文档未重点强调的能力
3. 不把 future plan、方向草案、未执行 gate 写成已实现。
4. 新增或调整 `phase-text/` 文档后，必须同步：
   - `docs/plans/README.md`
   - `docs/README.md`
   - `docs/plans/PLAN_STATUS.md`
   - `docs/specs/governance/phase-delivery-ledger.md`
5. `phase-text/` 可以写功能真相、测试真相、已验证残余缺口真相，以及这条文档线自身的整体规划；不能写新的版本执行计划或 release verdict。

## Files

- `2026-05-06_frontend_page_test_record_template.json`
  - 前端逐页面测试记录 JSON 模板；每个页面一个大块，只定义字段和填写规则，供后续逐轮回填
- `2026-05-06_phase_text_overall_plan.md`
  - `phase-text/` 最终目标、边界、产物结构、完成标准与台账同步规则
- `2026-05-04_v1_0_to_v4_0_implemented_testable_features_report.md`
  - v1.0-v4.0 已实现且当前可测试能力总盘点
- `2026-05-04_frontend_full_test_plan.md`
  - 基于真实前端路由、页面结构与现有自动化覆盖整理的全页面测试文档，重点展开 Chat 页面
- `2026-05-07_verified_residual_gaps_report.md`
  - 已验证残余问题报告，只记录当前仍可在浏览器或接口里复现的缺口
