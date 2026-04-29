# v3.0FR Execution Plan Review

日期：2026-04-29
状态：review
评审对象：docs/plans/v3_0/active/phase_fr/11_v3_0FR_execution_plan.md

## 1. 结论

执行计划范围清晰，已将 giant page 深拆与第一轮可靠性重构做了显式分层，适合直接执行。

## 2. 覆盖性检查

- WP0 合理：先冻结边界，避免把 Chat/KB 整页重写混进同一个切片。
- WP1 合理：legacy bridge 是无业务值、低风险的清理对象。
- WP2 合理：KB 列表 virtualization 直接回应大数据量卡顿风险。
- WP3 合理：Read / Notes 的偏好状态抽离属于高回报、低冲突改动。
- WP4 合理：Hover-only 删除入口必须作为基础可用性缺陷处理。

## 3. 建议补充的检查点

### 3.1 Legacy Cleanup 检查点

- 仓内对 `ChatLegacy` 和 `KnowledgeBaseDetailLegacy` 的引用为 0。
- 路由仍通过现有 V2 入口工作。

### 3.2 Virtualization 检查点

- 小于阈值时继续使用普通渲染。
- 高于阈值时进入 virtualization 路径。
- 高亮论文仍能滚动到可见区域。

### 3.3 Preference Persistence 检查点

- `Read` 偏好状态刷新后恢复。
- `Notes` 文件夹筛选和标签筛选刷新后恢复。
- 不出现把运行时对象误恢复进页面的脏状态。

### 3.4 Interaction 检查点

- 删除按钮默认可见，但不抢占标题区域。
- 现有确认弹窗逻辑保持不变。

## 4. 风险复核

1. virtualization 若高度估计失真，可能导致卡片局部裁切；应优先选择保守固定高度。
2. 若将 `selectedNoteId` 之类状态误持久化，会在跨页面恢复时制造错误上下文；本计划已正确排除。
3. 若在同一轮内继续深拆 `ChatWorkspaceV2`，回归面会显著扩大；本计划已冻结避免。

## 5. 最终建议

Phase FR 可以直接按当前计划进入执行。执行时应坚持“小改一刀、立刻验证”的顺序，不要在验证前继续扩大修改面。