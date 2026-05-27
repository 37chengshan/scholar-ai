# v4.5 Gate Input Matrix

> 日期：2026-05-13  
> 状态：active-input-matrix

## 1. 目标

把 v4.5 release bridge 在 phase_0 就需要消费的 gate 输入固定下来，避免后续 benchmark、walkthrough、closeout 各写一套口径。

## 2. Matrix

| gate_case | route | scope | current expectation | pass signal | block signal |
|---|---|---|---|---|---|
| `single-paper-chat` | `POST /api/v1/chat` | paper | 可返回 answer contract，但证据质量可能退化 | `success=true` 且存在 `answer`，并命中目标 `paper_id` 的 citation/evidence | 5xx / 空 payload / 无目标论文命中 |
| `single-paper-evidence` | `POST /api/v1/search/evidence` | paper | 应返回 scoped evidence 或 paper hit | `evidence_matches` 非空，或 `paper_results` 含目标 `paper_id` | route error / 空 evidence / 无目标论文命中 |
| `multi-paper-compare` | `POST /api/v1/queries/query` | compare | 可形成真实 compare-style answer，但可能存在低置信或降级 | `answer` 非空，且来源覆盖至少一个目标 paper；若覆盖两篇更佳 | route error / answer 为空 / 完全未命中目标论文 |
| `compare-v4-contract` | `POST /api/v1/compare/v4` | compare | 应返回 compare contract、compare_matrix 与 honesty 字段 | `response_type=compare` 且存在 `compare_matrix`，并命中目标论文证据 | route error / compare matrix 缺失 / 未命中目标论文 |
| `kb-scoped-chat` | `POST /api/v1/chat` | knowledge base | 应沿 shared path 返回 KB scope answer | `success=true` 且 evidence/citation 命中 KB 内论文 | benchmark user 无可用 KB membership 样本 |
| `kb-scoped-evidence` | `POST /api/v1/search/evidence` | knowledge base | 应沿 shared path 返回 KB scope evidence | `evidence_matches` 非空且命中 KB 内论文 | benchmark user 无可用 KB membership 样本 |
| `kb-query` | `POST /api/v1/knowledge-bases/{kb_id}/query` | knowledge base | 应返回 KB answer 与 citation | `answer` 非空、`citations` 非空且命中 KB 内论文 | benchmark user 无可用 KB membership 样本 |

## 3. 当前 phase_0 解释

1. 这张表是 v4.5 benchmark、walkthrough 和 release gate 的共同输入。
2. KB gate 当前不再默认 blocked；若 `Paper.knowledge_base_id` 已有真实样本，就必须进入真实 pass/fail。
3. `knowledge_base_papers=0` 仍需在报告中标为 association-table 风险，但不能再单独替代整个 KB scope 的数据真相判断。
