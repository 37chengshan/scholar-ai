# 13 v3.0F Execution Plan

最后更新：2026-04-29

## 目标

在不扩大功能面的前提下，完成 Dashboard、Search、KB、Read、Chat、Review 的产品化收口，统一下一步动作与状态透明度。

## 范围

1. 统一 `metadata-only` / `importing` / `fulltext-ready` / `supported|weak|unsupported` 的 UI 表达
2. 关键页面显示“下一步动作”而不是仅显示技术状态
3. 对 Beta 必需的空态、错误态、恢复入口做收口

## 验收标准

- Search 外部结果能稳定表达导入前/导入中/全文可用状态
- Read/Chat/Review 对 unsupported 或 weak evidence 有一致提示
- Dashboard/KB 能指向下一步动作，不靠隐含流程

## 回填记录

- 2026-04-29: Search import modal 切换为先选择后确认的稳定交互，待整链路验证

## Close-out 结论

- current_status: closeout-required
- blockers:
  - 需要完整 Beta walkthrough 验证多页面状态一致性
