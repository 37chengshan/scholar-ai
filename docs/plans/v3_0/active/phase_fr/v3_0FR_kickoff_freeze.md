# v3.0FR Kickoff Freeze

日期：2026-04-29
状态：freeze
范围：Phase FR（Frontend Reliability Refactor）
上游：
- docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md
- docs/plans/v3_0/active/phase_fr/11_v3_0FR_execution_plan.md
- docs/plans/v3_0/active/phase_fr/2026-04-29_v3_0FR_Frontend_Reliability_Refactor_研究文档.md

## 1. 冻结目标

Phase FR 只做“可靠性重构第一轮”，不做整套 giant page 重写。

本轮正式范围冻结为：

```txt
legacy bridge cleanup
-> kb paper list virtualization
-> read preference persistence
-> notes preference persistence
-> hover-only destructive action cleanup
-> focused validation
```

## 2. Freeze 条款

### Freeze-01：必须在真实主链页面上修改

- 所有改动必须落在 `apps/web` 现有正式入口。
- 禁止新建 `ChatV3`、`KnowledgeWorkspaceNew`、`ReadNew` 等平行实现路径。

### Freeze-02：本轮不做 giant page 全拆

- `ChatWorkspaceV2` 可做局部清障，但不允许在本轮中把整套 Shell / Controller / Sections 深拆混入同一 PR。
- `KnowledgeWorkspaceShell` 不在本轮进行 IA 重排。

### Freeze-03：偏好状态与业务状态分离

- 本轮持久化只覆盖界面偏好状态。
- 禁止把正在运行的业务数据、导入结果、消息流数据直接放入同一个 preference store。

### Freeze-04：核心操作不可再依赖 Hover

- 主路径操作和破坏性操作不允许再以 `opacity-0 group-hover:opacity-100` 作为唯一显现方式。

### Freeze-05：列表虚拟化只作用于高数据量场景

- 小列表场景允许继续使用普通渲染。
- 高数据量场景必须进入 virtualization 路径，防止一次性渲染卡顿。

## 3. 验收闸门

通过条件：

1. legacy bridge 被删除且主链仍可运行。
2. KB 列表 virtualization 不破坏论文打开、笔记跳转、聊天跳转。
3. `Read / Notes` 偏好状态刷新后仍恢复。
4. `apps/web` 的 focused tests 与 type-check 通过。