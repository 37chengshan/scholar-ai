# v5.0 Complete

`v5_0/complete/` 用于归档已完成的 v5.0 phase 文档。

当前为空仓库占位;只有在对应 phase closeout 与状态回填完成后,相关计划才应移动到这里。

## 归档触发条件

1. phase 在 `docs/plans/PLAN_STATUS.md` 已经标为 `done`
2. 对应 `reports/` 下的 closeout report 已经合并并通过 doc gate
3. 该 phase 的所有 deliverable unit 已在 `docs/specs/governance/phase-delivery-ledger.md` 标为 `done`
4. 该 phase 的代码已合入主干并通过 release gate

不满足上述四项的 phase 文档必须留在 `active/` 下,不允许提前归档。
