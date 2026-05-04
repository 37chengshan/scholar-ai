---
owner: product-engineering
status: asset-ready
depends_on:
  - 21_v4_0_phase_2_execution_plan
  - 2026-05-03_v4_0_phase_2_beta_release_hardening_research
last_verified_at: 2026-05-03
evidence_commits:
  - working-tree-v4-0-phase-2-assets
---

# v4.0 Phase 2 Demo Dataset

## 1. 目标

本文件定义 Phase 4.0-2 controlled beta 的可重复 demo dataset。

目标不是扩大样本规模，而是给 `Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review` 提供一套可复用、可降级、可反馈的最小真实样本。

## 2. 使用约束

1. 本文件优先复用 Phase D 真实样本台账，不另造 marketing-only 样本。
2. 每次 walkthrough 必须显式记录使用了哪个 `dataset_id`。
3. 历史 RW-002 / RW-004 / RW-005 只能提供已知 timing 与 degraded 预期，不能替代 Phase 2 fresh-state 证据。
4. 若 search provider 不稳定，允许使用固定 arXiv ID 复搜；仍失败时必须标记 `blocked` 或 `partial`。

## 3. 字段契约

| field | requirement |
|---|---|
| `dataset_id` | 固定样本组 ID，写入 quickstart、walkthrough 与 feedback |
| `source_query_or_ids` | 至少一条 search query，外加一条固定 ID 或 DOI fallback |
| `sample_registry_refs` | 引用 Phase D 样本台账，避免重复造册 |
| `expected_import_mode` | 标明 `fulltext-ready`、`metadata-only` 或已知不稳定路径 |
| `expected_workflow_steps` | 明确本样本必须覆盖的页面与动作 |
| `expected_evidence` | 至少 1 个 citation/evidence probe |
| `known_degraded_cases` | 当前允许出现的 partial / latency / evidence weakness |
| `fallback` | search/import 失败时允许的替代动作 |
| `reset_requirements` | 运行前必须满足的账号、KB、import job 隔离条件 |

## 4. 数据集目录

### 4.1 `beta-mainline-001`

- objective: 作为 controlled beta 默认 happy-path 样本，覆盖单篇导入、跨页面 handoff、第二篇对比扩展与 review honesty。
- source_query_or_ids:
  - D-001: `Attention Is All You Need`
  - D-001 fallback: `1706.03762`
  - D-040 compare extension: `A Survey of Large Language Models`
  - D-040 fallback: `2303.18223`
- sample_registry_refs:
  - `D-001`
  - `D-040`
- expected_import_mode:
  - D-001: `fulltext-ready` via unified search import
  - D-040: `fulltext-ready` via unified search import
- expected_workflow_steps:
  - Search D-001
  - Import D-001 into fresh KB
  - Open Read view from KB
  - Launch Chat from paper context
  - Generate Notes summary
  - Search and import D-040 into the same KB
  - Run Compare across D-001 and D-040
  - Run Review for the same KB
- expected_evidence:
  - At least 1 citation jump from Chat or Review must land back in D-001 content.
  - Compare output must distinguish the original Transformer paper from the later LLM survey, not collapse them into one claim.
- known_degraded_cases:
  - Historical RW-005 shows first full import still takes about 4.1 minutes end-to-end.
  - Review may finish as `partial / insufficient_evidence`; this is a degraded result, not a success verdict.
  - Compare still lacks a Phase 2 fresh-state release-pass and must be recorded as `pass / partial / fail` explicitly.
- fallback:
  - If search ranking is noisy, rerun with the exact arXiv ID.
  - If D-040 search/import fails, substitute D-020 only for Compare smoke and mark the walkthrough `partial`.
- reset_requirements:
  - Use a fresh demo account or a namespaced KB under the dedicated demo account.
  - KB name prefix must include `scholarai-beta-<run_id>`.
  - No unfinished import jobs may exist under the same demo account.

### 4.2 `beta-degraded-001`

- objective: 作为 degraded path 样本，主动暴露 figure/layout-heavy 文档的 citation 与 evidence 边界。
- source_query_or_ids:
  - D-020: `Segment Anything`
  - D-020 fallback: `2304.02643`
  - D-070: `LayoutParser`
  - D-070 fallback: `2103.15348`
- sample_registry_refs:
  - `D-020`
  - `D-070`
- expected_import_mode:
  - D-020: `fulltext-ready` expected, but figure evidence may drift
  - D-070: `fulltext-ready` expected, but layout/citation jump is a known boundary
- expected_workflow_steps:
  - Search one figure-heavy paper
  - Import into the same or a fresh demo KB
  - Open Read
  - Ask Chat for a figure-grounded answer
  - Trigger Review or Compare only if the first paper import is complete
- expected_evidence:
  - Verify whether a figure-related answer can jump to the cited region.
  - Record any unsupported or weakly grounded claim as a limitation, not a pass.
- known_degraded_cases:
  - figure/caption grounding may be weak
  - citation jump may drift on layout-heavy pages
  - review honesty may surface partial sections
- fallback:
  - If D-070 fails search/import, retain only D-020 and classify the run as degraded coverage.
  - If figure citation cannot be verified, stop before public-facing summary and file feedback.
- reset_requirements:
  - Reuse the same run namespace only if prior import jobs completed cleanly.
  - Any stale KB with the same prefix invalidates fresh-state claims.

## 5. 推荐顺序

1. 默认使用 `beta-mainline-001` 完成主链。
2. 只有主链记录完成后，再追加 `beta-degraded-001` 作为 limitation probe。
3. 如果第一组样本 search 不稳定，不得换成未登记样本；必须使用 fallback ID 或把 run 标记为 `blocked`。

## 6. 证据探针

每次 controlled beta walkthrough 至少记录以下 3 个 evidence probe：

1. Search 结果页是否返回目标论文并提供真实 import CTA。
2. Chat 或 Review 的至少 1 次 citation jump 是否能落回论文内容。
3. Compare 或 Review 是否把 `partial / insufficient_evidence` 诚实暴露为限制，而不是写成成功。