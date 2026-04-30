# v3.0J Execution Plan Review

> 日期：2026-04-30  
> 状态：review-ready  
> 范围：`Phase J` 首批目标是把 comparative benchmark 与 gate 真正收成可执行门禁，不是立即重建全部 benchmark 资产。

## 1. 本轮完成定义

1. comparative taxonomy、run contract、runbook、threshold proposal 进入正式执行计划。
2. `Phase A` academic benchmark 与 `Phase D` real-world workflow 都被定义为 `Phase J` 的正式 consume source。
3. `Phase H/I` 已冻结 hook 被收成 required gate input，而不是“建议字段”。

## 2. 明确不在本轮

1. 新增大规模 public / blind corpus 扩容
2. 新模型或新框架默认主链替换
3. `Phase D` 真实工作流执行本身
4. 所有阈值一次性跑实测定版

## 3. 风险

1. `Phase A` artifact 结构若未冻结，comparative gate 会持续写兼容分支。
2. `Phase D` 若缺 hook，workflow success 仍无法和 academic benchmark 同口径比较。
3. `Phase H` mode parity 若不诚实，candidate verdict 会被错误放大或掩盖。

## 4. 验收

1. baseline / candidate / diff protocol 有单一真源。
2. required hook 缺失时 comparative gate 直接 fail。
3. `citation_coverage / unsupported_claim_rate / latency / cost / degraded_rate` 的 verdict 规则明确。
4. `Phase H`、`Phase I`、release gate 的 consume 路径明确。

## 5. 与其他 Phase 的关系

1. `Phase A`：提供 academic benchmark 资产与 schema。
2. `Phase D`：提供真实 workflow 结果与 failure bucket。
3. `Phase H`：提供 online baseline、mode parity 与 fallback honesty。
4. `Phase I`：提供 truthfulness / route candidate hooks，供 comparative gate 裁决是否值得升级。
