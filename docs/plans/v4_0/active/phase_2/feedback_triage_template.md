---
owner: product-engineering
status: asset-ready
depends_on:
  - beta_quickstart.md
  - known_limitations.md
  - fresh_state_walkthrough_script.md
last_verified_at: 2026-05-03
evidence_commits:
  - working-tree-v4-0-phase-2-assets
---

# v4.0 Phase 2 Feedback Triage Template

## 1. 目标

本模板把 controlled beta 的自由文本反馈收口成可分诊队列。

Phase 2 所有 `partial / fail / blocked` walkthrough 项都必须能落进这张模板，而不是留在聊天记录里。

## 2. Severity Taxonomy

| severity | meaning | action |
|---|---|---|
| P0 | 核心主链不可用，无法完成 Search / Import / KB / Read / Chat / Notes / Compare / Review 中的关键一步 | 立即阻断 walkthrough 与 closeout |
| P1 | 核心交互可用，但数据一致性、evidence 语义或状态表达错误，足以让结果失真 | 不得宣称 `demo-ready`；进入 fix-now 或 carry-forward 决策 |
| P2 | 非阻断的文案、视觉、性能或局部恢复问题 | 可以继续受控试用，但 48 小时内必须完成 owner 与处理结论 |

## 3. Decision Taxonomy

| decision | when to use |
|---|---|
| `fix-now` | 当前 Phase 2 若不修会阻断 fresh-state walkthrough 或误导 beta verdict |
| `carry-forward` | 已确认存在，但明确转交 Phase 3/4/5/6/7 |
| `accepted-limitation` | 已写入 known limitations，当前 beta 可带着它运行 |
| `duplicate` | 与已有 feedback item 重复 |

## 4. Triage Rules

1. 所有 `blocked` walkthrough 项默认至少是 `P0` 或 `P1`。
2. `partial / insufficient_evidence` 如果会让用户误判结果真实性，至少按 `P1` 处理。
3. 只有已经写入 `known_limitations.md` 且不改变 beta 结论的事项，才允许落为 `accepted-limitation`。
4. `carry-forward` 必须显式写明 downstream phase。

## 5. Template

```markdown
# Phase 2 Feedback Item

- feedback_id:
- reported_at:
- reporter:
- reporter_role:
- run_id:
- dataset_id:
- environment: local-controlled-beta
- workflow_step:
- expected_behavior:
- actual_behavior:
- evidence_issue:
- artifact_link:
- severity:
- owner:
- decision:
- downstream_phase:
- notes:
```

## 6. Example Classification

| scenario | severity | decision |
|---|---|---|
| Search 完全找不到 D-001，连精确 arXiv ID 也失败 | P0 | fix-now |
| Import 成功但首轮耗时约 4 分钟 | P2 | accepted-limitation |
| Review 结束但结果是 `partial / insufficient_evidence` | P1 | carry-forward 或 fix-now，取决于是否阻断本轮结论 |
| Compare 可以打开但混淆 D-001 与 D-040 的来源 | P1 | fix-now |

## 7. Queue Ownership

| field | rule |
|---|---|
| reporter | 可以是 operator、internal beta user 或 reviewer |
| owner | 必须是明确职能：`product-engineering`、`web-platform`、`ai-runtime` 或 `ai-platform` |
| artifact_link | 可以是截图、日志、run 记录路径或 terminal transcript |
| downstream_phase | 只有 `carry-forward` 才必填 |

## 8. Minimum Completion Bar

一条反馈记录只有在以下字段都不为空时，才算进入 triage：

1. `run_id`
2. `reporter`
2. `workflow_step`
3. `expected_behavior`
4. `actual_behavior`
5. `evidence_issue`
5. `artifact_link`
6. `severity`
7. `owner`
8. `decision`