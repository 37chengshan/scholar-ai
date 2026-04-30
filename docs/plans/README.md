# Plans Map

## Purpose

给 `docs/plans/` 一个稳定入口，明确当前主线、活跃计划和历史计划边界。

## Current Mainline

当前进行中主线是 `v3.0`，统一从以下文件进入：

1. `docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md`
2. `docs/plans/PLAN_STATUS.md`
3. `docs/plans/v3_0/active/phase_a/07_v3_0A_execution_plan.md`
4. `docs/plans/v3_0/reports/official_rag_evaluation/`

如果旧计划仍标记为 `in-progress`，但内容与 `v3.0` 主线冲突，优先按 `06_v3_0_overview_plan.md` 的 phase 拆分重新解释。

## Directory Rules

- `PLAN_STATUS.md`
  - `docs/plans/` 下计划状态唯一真源
- `v1_0/` `v2_0/` `v3_0/`
  - 版本化计划主目录
- `docs/plans/<version>/active/`
  - 当前执行中的 phase、overview、研究拆解
- `docs/plans/<version>/complete/`
  - 已完成的版本内计划
- `docs/plans/<version>/search/`
  - 搜索、数据源、研究收集类材料
- `docs/plans/<version>/reports/`
  - 验证、评测、迭代报告、发布门禁结果
- `archive/`
  - 已脱离当前主线的旧计划、旧 exec plan、旧报告
- `templates/`
  - 计划模板与回填模板

## Usage Rules

- 新 active 计划必须先在 `PLAN_STATUS.md` 登记。
- 同主题只保留一份 active 计划；其余计划必须标记 `superseded` 或移入对应版本的 `complete/`。
- 新的研究文档不要再落到独立 `docs/reports/`；直接放进对应版本的 `search/` 或 `reports/`。
- `overview` 文档负责讲主线、phase、边界，不负责展开到逐文件改造。
- `research/report` 文档负责补具体研究与阶段结论，不替代 `PLAN_STATUS.md`。
- 如果版本无法明确归类，先放 `docs/plans/archive/`，后续再决定是否升级为正式版本目录。
- 当版本主线切换时，必须同步更新本文件与 `docs/README.md`。
