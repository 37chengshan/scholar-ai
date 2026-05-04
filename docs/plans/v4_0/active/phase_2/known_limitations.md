---
owner: product-engineering
status: asset-ready
depends_on:
  - demo_dataset.md
  - 2026-05-03_v4_0_phase_2_beta_release_hardening_research
last_verified_at: 2026-05-03
evidence_commits:
  - working-tree-v4-0-phase-2-assets
---

# v4.0 Phase 2 Known Limitations

## 1. 口径

本文件面向 controlled beta 受控试用者，要求把当前能力边界写成用户可见限制。

这些限制不是“可忽略的小问题”，而是 Phase 2 必须诚实暴露并能进入 triage 的现实状态。

## 2. 当前限制清单

| limitation_id | limitation | user-visible symptom | classify as | default decision |
|---|---|---|---|---|
| LIM-001 | Review 可能返回 `partial / insufficient_evidence` | Review 运行结束，但部分 section 为空或带 omitted reason | `partial` | carry-forward to Phase 3 / 7 unless it blocks core demo |
| LIM-002 | 首轮 import 仍可能需要约 4 分钟 | Import job 已创建但 Read/Chat/Review 要等待较久 | `degraded` | accepted limitation for controlled beta, but timing must be recorded |
| LIM-003 | Compare 仍缺单次 fresh-state release-pass | Compare 页面可能可用，但 Phase 2 尚无 fresh-state 放行证据 | `partial` | fix-now only if current run is blocked; otherwise carry-forward |
| LIM-004 | Chat handoff 是 prefill-only，不自动发送 | 切到 Chat 后需要人工确认 prompt | `accepted limitation` | accepted for Phase 2 |
| LIM-005 | AI 输出必须人工核对 citation/evidence | 回答或 review 文字存在 unsupported 风险，不能当成事实直接引用 | `always-on caution` | never waive |
| LIM-006 | workflow truth 仍以前端 store + persistence 为主 | 页面状态恢复依赖前端持久化语义，非后端真源 | `accepted limitation` | carry-forward to later architecture work |
| LIM-007 | 外部 search provider 可能慢或结果噪音高 | 需要改用精确 arXiv ID 或多等几十秒 | `degraded` | accepted only with explicit logging |
| LIM-008 | staging/cloud beta 尚未开放 | 现阶段只能在本地受控环境演示 | `scope gate` | blocked until local fresh-state pass |

## 3. 使用者须知

1. 看到 `partial / insufficient_evidence` 时，不要把它理解成“差一点成功”，而要把它当成需要反馈的真实限制。
2. 若 citation jump 无法证明 claim，AI 输出只能作为草稿，不可当作最终结论。
3. 若 import 明显变慢，但最终完成，结果应记为 `degraded` 而不是 `blocked`。
4. 若环境无法证明 fresh-state，则整轮 walkthrough 应直接记为 `blocked`。

## 4. Quickstart 强绑定限制

以下限制必须在 quickstart 或 walkthrough 中被显式提到，不能只留在本文件：

1. `LIM-001` Review partial / insufficient evidence。
2. `LIM-002` 首轮 import latency。
3. `LIM-004` Chat handoff prefill-only。
4. `LIM-005` AI 输出需要 citation 审查。
5. `LIM-008` 仅允许 local controlled beta。

## 5. 不允许的写法

以下表述在 Phase 2 内一律禁止：

1. 把 `partial / insufficient_evidence` 写成“已完成 review”。
2. 把 local controlled beta 写成 public beta。
3. 把历史 Phase D/J run 写成当前 fresh-state run。
4. 把 citation 未核对的 AI 输出写成最终研究结论。