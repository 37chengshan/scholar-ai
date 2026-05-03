# v4.0 Phase 0 Beta Minimal Asset Inventory

> 日期：2026-05-02  
> 状态：inventory-defined  
> owner: `product-engineering`

## 1. 目标

本文件只定义 `Phase 4.0-2 Beta Release Hardening` 需要接手的最小资产，不在 Phase 0 内伪装成“已制作完成”。

## 2. 最低资产清单

| asset | minimum definition | owner | target phase | blocking level |
|---|---|---|---|---|
| demo dataset | 至少 1 组可重复演示的 search/import/read/chat/review 样本集，包含 paper IDs、期望主链、已知风险 | product-engineering | 4.0-2 | release-blocking |
| demo account | 至少 1 套本地或 staging 演示账号约定，含 fresh-state 重置策略 | product-engineering | 4.0-2 | release-blocking |
| beta quickstart | 说明环境、入口、主链步骤、预期等待时间、失败恢复入口 | product-engineering | 4.0-2 | release-blocking |
| known limitations | 明确 review partial、首轮 import latency、compare/full-chain 现状与非目标 | product-engineering | 4.0-2 | release-blocking |
| feedback channel | 明确 Beta 反馈收集入口、问题模板和责任人 | product-engineering | 4.0-2 | non-blocking-for-phase1 |
| walkthrough script | 15-30 分钟演示脚本，覆盖 happy path 与降级口径 | product-engineering | 4.0-2 | release-blocking |

## 3. 当前已知限制

1. fresh import 首轮端到端仍约 `4.1 min`。
2. review 可能以 `partial / insufficient_evidence` 完成。
3. compare 有 eval/workflow bundle 证据，但还缺单次 fresh-state 全链 closeout 记录。

## 4. 与 Phase 4.0-1 的关系

这些资产不足以阻止 `Phase 4.0-1` 的研究和执行设计启动，但阻止任何 Beta-ready、release-pass 或完整 walkthrough 已完成的表述。
