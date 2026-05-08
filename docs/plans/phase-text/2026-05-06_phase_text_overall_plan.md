# Phase-text Overall Plan

## Purpose

`docs/plans/phase-text/` 的最终职责不是再开一条版本执行主线，而是沉淀 ScholarAI 跨版本、跨页面、跨工作流的事实真层。

这个目录最终要稳定承载三类内容：

1. 已实现且当前仍可测试/可验证的功能真相
2. 基于真实页面结构与真实交互链路整理的测试真相
3. 已被验证存在、且仍影响当前体验或交付结论的残余缺口真相

它服务于两个问题：

1. 当前仓库到底已经能做什么
2. 当前仓库还缺什么、哪些缺口已经被明确验证

`phase-text/` 不是 release note，不替代版本 closeout，也不替代 `docs/plans/PLAN_STATUS.md`。

## Non-goals

以下内容不属于 `phase-text/`：

1. 新功能执行计划
2. 版本放行结论
3. 未经代码、测试或浏览器证据支持的能力声明
4. 仅基于目标愿景、路线图、口头预期写成的“已完成”
5. 与真实主线脱节的平行方案说明

## Final Target State

`phase-text/` 最终应收敛为一个稳定的事实型文档组，至少包含以下四层：

### 1. Cross-version Implemented Features Truth

- 目标：说明 v1.0-v4.0 范围内，哪些能力已经真实落地且仍可测试
- 当前对应：
  - `2026-05-04_v1_0_to_v4_0_implemented_testable_features_report.md`
- 完成标准：
  - 覆盖主要公开页、受保护页、知识工作流、阅读工作流、聊天工作流、上传导入工作流、对比/笔记/设置等主面
  - 对每项能力给出代码、测试、closeout 或 walkthrough 证据来源

### 2. Frontend Test Truth

- 目标：说明前端每个页面、子页面、关键组件面需要如何验证
- 当前对应：
  - `2026-05-04_frontend_full_test_plan.md`
- 完成标准：
  - 覆盖公开页与受保护页
  - 覆盖 KB / Read / Chat / Compare / Notes / Settings 等核心页面
  - 对 Chat 页面给出最高优先级深测矩阵
  - 明确 UI、文案、状态、交互、返回路径、失败模式与浏览器证据要求

### 3. Verified Residual Gaps Truth

- 目标：沉淀“已确认仍存在”的残余问题，而不是把问题散落在对话历史里
- 当前对应：
  - `2026-05-07_verified_residual_gaps_report.md`
- 最终要求：
  - 按页面/工作流列出已验证问题、影响范围、复现条件、证据来源、是否已修复
  - 只记录已验证问题，不写猜测

### 4. Phase-text Maintenance Contract

- 目标：说明 `phase-text/` 自身的目标状态、边界、更新节奏与台账同步规则
- 当前对应：
  - `README.md`
  - 本文档
- 完成标准：
  - 任何新增 `phase-text` 产物都能从这里判断是否应该存在、该如何命名、需要同步哪些真源

## Deliverables Matrix

| lane | deliverable | required evidence | update trigger | done means |
|---|---|---|---|---|
| implemented truth | 跨版本已实现能力报告 | 代码入口 + 测试/closeout/browser 任一实证 | 主链能力变化、closeout 变化、功能删改 | 能力范围与当前仓库一致，过时结论已移除 |
| frontend test truth | 全页面前端测试文档 | 真实路由 + 页面结构 + 当前测试覆盖 + 浏览器 walkthrough 经验 | 页面结构变更、路由变更、关键交互变更 | 测试矩阵覆盖当前所有主页面与子页面 |
| residual gaps truth | 已验证残余问题报告 | 复现步骤 + 浏览器/日志/接口/测试证据 | walkthrough 发现新问题、根因修复完成、问题关闭 | 当前已知问题状态清楚、无失效条目 |
| maintenance contract | README + overall plan | 与现行文档组织、台账规则一致 | `phase-text` 范围、规则或目标变化 | 目录边界、同步规则、完成标准可执行 |

## Evidence Standard

`phase-text/` 中每一个“已实现”“可测试”“存在问题”“已修复”的结论，至少要有以下一种证据：

1. 真实代码入口或调用链
2. 单测、集成测试或窄回归测试
3. 浏览器 walkthrough 证据
4. closeout / status report / validation artifact
5. API probe 或运行时日志

禁止仅凭以下内容下结论：

1. `.env` 目标配置
2. 旧文档里的设计预期
3. 未复验的历史对话描述
4. 单纯截图但无真实页面路径和上下文

## Update Workflow

新增或更新 `phase-text/` 文档后，必须同步检查并按需更新：

1. `docs/plans/phase-text/README.md`
2. `docs/plans/README.md`
3. `docs/README.md`
4. `docs/plans/PLAN_STATUS.md`
5. `docs/specs/governance/phase-delivery-ledger.md`

如果新增文档声称某项功能“已实现”或“不可用”，还必须反查：

1. 对应版本 closeout 报告
2. 相关测试文档
3. 相关页面/工作流是否已有更晚证据

## Completion Criteria

`phase-text/` 作为一条文档线，可以被认为“整体收口”至少需要满足以下条件：

1. 已存在一份跨版本已实现能力报告，并与当前仓库保持同步
2. 已存在一份覆盖前端全部主页面与子页面的测试文档，并与当前 UI 结构保持同步
3. 已存在一份独立的“已验证残余问题”事实报告
4. `README`、`PLAN_STATUS`、delivery ledger 与 `phase-text/` 目录内容一致
5. 任何一个条目都能被追溯到代码、测试、walkthrough 或 closeout 证据
6. 不把 `phase-text` 写成 release gate 或版本放行真源

## Current Gap Assessment

截至 2026-05-07，`phase-text/` 当前状态如下：

1. 已有跨版本已实现能力报告
2. 已有前端全页面测试文档
3. 已有独立的“已验证残余问题/已知缺口”事实报告
4. 尚需随着 v4.0 walkthrough、前端修复、后端主链调整持续刷新

因此，`phase-text/` 目前已建立主体框架，但还未达到最终收口状态。

## Relationship To Other Truth Sources

- `docs/plans/PLAN_STATUS.md`
  - 计划状态真源
- `docs/plans/<version>/reports/*.md`
  - 版本 closeout / readiness / release 结论真源
- `docs/specs/governance/phase-delivery-ledger.md`
  - 文档/交付单元登记真源
- `docs/plans/phase-text/*`
  - 跨版本 implemented/testable/residual-gap 事实真源

`phase-text/` 可以引用版本 closeout 结论，但不能取代版本 closeout。

## Naming And Placement Rules

1. 统一放在 `docs/plans/phase-text/`
2. 文件名使用 `YYYY-MM-DD_<topic>.md`
3. topic 必须直指事实对象，例如：
   - `implemented_testable_features_report`
   - `frontend_full_test_plan`
   - `verified_residual_gaps_report`
   - `phase_text_overall_plan`
4. 不使用 `final`, `latest`, `new`, `tmp`, `draft2` 这类无治理价值命名

## Operating Rule

今后凡是要回答以下问题，优先先看 `phase-text/`：

1. “目前已经实现了哪些功能”
2. “哪些页面/子页面需要测”
3. “哪些问题已经被验证存在”
4. “跨版本功能事实与版本 closeout 的边界是什么”

但如果问题是：

1. “当前 phase 是否放行”
2. “当前版本是否 beta-ready / release-ready”
3. “下一 phase 怎么做”

则应先回到版本执行计划与 closeout 文档，而不是由 `phase-text/` 代答。
