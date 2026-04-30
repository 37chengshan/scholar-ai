# 12 v3.0E Execution Plan

最后更新：2026-04-29

## 目标

把 import / review / compare / reading-card 的 async 状态、错误态、恢复入口收口到 Beta 必需最小实现，不再新增第二套状态机。

## 范围

1. 统一最小观测字段：阶段、耗时、失败原因、可重试性
2. 收口 import job、review draft、reading-card 的错误态与恢复入口
3. 保留现有实现路径，不做额外性能扩面

## 验收标准

- Search/KB/Review 共享 `job.stage` 与 canonical async status 语义
- 用户可见失败时必须有恢复入口或明确限制说明
- 关键路径状态不能只留在日志里

## 回填记录

- 2026-04-29: strict close-out 纳入本轮，等待验证命令与截图/运行记录回填

## Close-out 结论

- current_status: closeout-required
- blockers:
  - Wave 0 测试结果尚未回读
  - compare/read/review 的统一状态透明度仍需实测
